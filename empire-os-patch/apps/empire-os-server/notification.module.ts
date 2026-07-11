/**
 * NotificationModule — Event-Driven Notification Queue
 *
 * Captures critical system events and surfaces them as a dismissible
 * notification feed. Modules and the watchdog emit events via
 * the exported `emitNotification()` function. The notification
 * queue is in-memory (500 max). Notifications survive server restarts
 * only if JSON persistence is added later.
 *
 * Severity levels:
 *   info     — informational, auto-dismiss after 24h
 *   warning  — something needs attention
 *   error    — something broke; actionable
 *   critical — empire OS degraded; needs immediate action
 *
 * Routes:
 *   GET  /notification/                → summary
 *   GET  /notification/all             → all notifications (newest first)
 *   GET  /notification/unread          → unread notifications only
 *   GET  /notification/dismiss/:id     → dismiss a single notification
 *   POST /notification/dismiss-all     → dismiss all (mark as read)
 *   GET  /notification/settings        → get notification settings
 *   POST /notification/settings        → update notification settings
 *   POST /notification/emit            → emit a notification (internal API)
 *   GET  /notification/health          → module health
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { empireLog } from './logger.module.js'

// ── Types ─────────────────────────────────────────────────────────────────────

export type NotificationSeverity = 'info' | 'warning' | 'error' | 'critical'
export type NotificationCategory = 'system' | 'ai' | 'job' | 'backup' | 'update' | 'custom'

export interface Notification {
  id:         string
  severity:   NotificationSeverity
  category:   NotificationCategory
  title:      string
  message:    string
  source:     string      // which module emitted it
  timestamp:  string      // ISO
  dismissed:  boolean
  dismissedAt:string | null
  actionUrl?: string      // optional deep-link to relevant module endpoint
  data?:      unknown     // optional structured payload
}

export interface NotificationSettings {
  maxQueue:         number    // max notifications to keep (default 500)
  autoExpireHours:  number    // auto-expire INFO notifications after N hours (0 = never)
  criticalRetain:   boolean   // never auto-expire critical notifications
}

// ── Singleton store ───────────────────────────────────────────────────────────

const queue: Notification[] = []
const MAX_QUEUE = 500
let   notifSeq  = 0

let settings: NotificationSettings = {
  maxQueue:        500,
  autoExpireHours: 24,
  criticalRetain:  true,
}

// ── Public emit API — importable from any module ──────────────────────────────

export function emitNotification(
  severity:   NotificationSeverity,
  category:   NotificationCategory,
  title:      string,
  message:    string,
  source:     string,
  options?: {
    actionUrl?: string
    data?:      unknown
  },
): Notification {
  const n: Notification = {
    id:          (++notifSeq).toString(36),
    severity,
    category,
    title,
    message,
    source,
    timestamp:   new Date().toISOString(),
    dismissed:   false,
    dismissedAt: null,
    actionUrl:   options?.actionUrl,
    data:        options?.data,
  }

  queue.unshift(n)   // newest first
  if (queue.length > settings.maxQueue) queue.length = settings.maxQueue

  // Mirror to logger
  const logLevel = severity === 'info' ? 'INFO' : severity === 'warning' ? 'WARN' : 'ERROR'
  empireLog(logLevel, `notification[${source}]`, `${title}: ${message}`)

  return n
}

// ── Auto-expire helper ────────────────────────────────────────────────────────

function sweepExpired(): void {
  if (settings.autoExpireHours <= 0) return
  const cutoffMs = Date.now() - settings.autoExpireHours * 3_600_000
  for (const n of queue) {
    if (n.dismissed) continue
    if (settings.criticalRetain && n.severity === 'critical') continue
    if (n.severity === 'info' && new Date(n.timestamp).getTime() < cutoffMs) {
      n.dismissed   = true
      n.dismissedAt = new Date().toISOString()
    }
  }
}

// ── Module ────────────────────────────────────────────────────────────────────

export class NotificationModule implements EmpireModule {
  readonly moduleId = 'notification'
  private sweepInterval?: ReturnType<typeof setInterval>

  async init(_services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    // Emit a startup notification
    emitNotification('info', 'system', 'Empire OS Started', 'All modules online and accepting requests', 'notification')

    // Auto-sweep every 10 minutes
    this.sweepInterval = setInterval(() => sweepExpired(), 10 * 60 * 1_000)

    empireLog('INFO', 'notification', 'Notification module initialized')
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start  = Date.now()
    const path   = (req.path === '' ? '/' : req.path).split('?')[0]
    const method = req.method

    try {
      // GET / — summary
      if ((path === '/' || path === '') && method === 'GET') {
        sweepExpired()
        const unread   = queue.filter(n => !n.dismissed)
        const critical = unread.filter(n => n.severity === 'critical')
        return this.ok(start, {
          module:         'Notification',
          total:          queue.length,
          unread:         unread.length,
          critical:       critical.length,
          byCritical:     critical.slice(0, 5).map(n => ({ id: n.id, title: n.title, timestamp: n.timestamp })),
          endpoints: {
            all:        'GET /notification/all',
            unread:     'GET /notification/unread',
            dismiss:    'GET /notification/dismiss/:id',
            dismissAll: 'POST /notification/dismiss-all',
            settings:   'GET /notification/settings',
            emit:       'POST /notification/emit',
          },
        })
      }

      // GET /all — all notifications
      if (path === '/all' && method === 'GET') {
        sweepExpired()
        return this.ok(start, { notifications: queue, total: queue.length })
      }

      // GET /unread — unread only
      if (path === '/unread' && method === 'GET') {
        sweepExpired()
        const unread = queue.filter(n => !n.dismissed)
        return this.ok(start, { notifications: unread, count: unread.length })
      }

      // GET /dismiss/:id
      const dismissMatch = path.match(/^\/dismiss\/(.+)$/)
      if (dismissMatch && method === 'GET') {
        const id = dismissMatch[1]
        const n  = queue.find(n => n.id === id)
        if (!n) return this.notFound(start, `Notification not found: ${id}`)
        n.dismissed   = true
        n.dismissedAt = new Date().toISOString()
        return this.ok(start, { message: `Dismissed: ${id}`, notification: n })
      }

      // POST /dismiss-all
      if (path === '/dismiss-all' && method === 'POST') {
        const now = new Date().toISOString()
        let count = 0
        for (const n of queue) {
          if (!n.dismissed) {
            n.dismissed   = true
            n.dismissedAt = now
            count++
          }
        }
        return this.ok(start, { message: `Dismissed ${count} notifications` })
      }

      // GET /settings
      if (path === '/settings' && method === 'GET') {
        return this.ok(start, settings)
      }

      // POST /settings
      if (path === '/settings' && method === 'POST') {
        const body = (req.body ?? {}) as Partial<NotificationSettings>
        if (body.maxQueue !== undefined)        settings.maxQueue        = body.maxQueue
        if (body.autoExpireHours !== undefined) settings.autoExpireHours = body.autoExpireHours
        if (body.criticalRetain !== undefined)  settings.criticalRetain  = body.criticalRetain
        empireLog('INFO', 'notification', 'Settings updated', settings)
        return this.ok(start, { message: 'Settings updated', settings })
      }

      // POST /emit — internal API for other modules
      if (path === '/emit' && method === 'POST') {
        const body = (req.body ?? {}) as {
          severity?: NotificationSeverity
          category?: NotificationCategory
          title?:    string
          message?:  string
          source?:   string
          actionUrl?:string
          data?:     unknown
        }
        if (!body.severity || !body.title || !body.message || !body.source) {
          return this.badRequest(start, 'Required fields: severity, title, message, source')
        }
        const n = emitNotification(
          body.severity,
          body.category ?? 'custom',
          body.title,
          body.message,
          body.source,
          { actionUrl: body.actionUrl, data: body.data },
        )
        return this.ok(start, { message: 'Notification emitted', notification: n })
      }

      // GET /health
      if (path === '/health' && method === 'GET') {
        return this.ok(start, await this.health())
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      empireLog('ERROR', 'notification', `Error on ${method} ${path}`, msg)
      return this.serverError(start, msg)
    }
  }

  async health(): Promise<ModuleHealth> {
    const unread   = queue.filter(n => !n.dismissed)
    const critical = unread.filter(n => n.severity === 'critical')
    return {
      status: critical.length > 0 ? 'degraded' : 'healthy',
      details: {
        total:    queue.length,
        unread:   unread.length,
        critical: critical.length,
        maxQueue: settings.maxQueue,
      },
    }
  }

  async handleEvent(): Promise<void> {}

  async shutdown(): Promise<void> {
    if (this.sweepInterval) clearInterval(this.sweepInterval)
    empireLog('INFO', 'notification', 'Notification module shutting down', { total: queue.length })
  }

  private ok(start: number, body: unknown): GatewayResponse {
    return { status: 200, body, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private notFound(start: number, msg: string): GatewayResponse {
    return { status: 404, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private badRequest(start: number, msg: string): GatewayResponse {
    return { status: 400, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private serverError(start: number, msg: string): GatewayResponse {
    return { status: 500, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
}
