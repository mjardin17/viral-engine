/**
 * EmpireLogger — Centralized Structured Logging
 *
 * Singleton logger used by every module and the server itself.
 * All logs are tagged with timestamp, level, module, and optional
 * structured data payload. Stored in a ring buffer AND appended to
 * daily rotating log files in .empire-data/logs/.
 *
 * Import the singleton:
 *   import { empireLog } from './logger.module.js'
 *   empireLog('INFO', 'my-module', 'Something happened', { key: 'value' })
 *
 * Routes:
 *   GET  /logger/recent        → last N entries (default 100, max 1000)
 *   GET  /logger/search        → search by ?q=&level=&module=&limit=
 *   GET  /logger/stats         → counts by level + module
 *   GET  /logger/export        → full NDJSON export
 *   POST /logger/clear         → clear in-memory buffer (not log files)
 *   GET  /logger/files         → list log files on disk
 *   GET  /logger/health        → module health
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { appendFileSync, mkdirSync, existsSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

// ── Types ─────────────────────────────────────────────────────────────────────

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'

export interface LogEntry {
  id:        string
  timestamp: string
  level:     LogLevel
  module:    string
  message:   string
  data?:     unknown
  ms?:       number   // optional duration tag
}

// ── Singleton logger state ────────────────────────────────────────────────────

const RING_MAX   = 5_000
const LOG_DIR    = '.empire-data/logs'
const LEVEL_RANK: Record<LogLevel, number> = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 }

let   ring:     LogEntry[] = []
let   ringHead  = 0           // next write position (circular)
let   entrySeq  = 0           // monotonically increasing ID
let   logDirOk  = false

function ensureLogDir(): void {
  if (logDirOk) return
  if (!existsSync(LOG_DIR)) mkdirSync(LOG_DIR, { recursive: true })
  logDirOk = true
}

function todayFilePath(): string {
  const d = new Date()
  const ymd = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
  return join(LOG_DIR, `empire-${ymd}.log`)
}

function writeToFile(entry: LogEntry): void {
  try {
    ensureLogDir()
    appendFileSync(todayFilePath(), JSON.stringify(entry) + '\n', 'utf8')
  } catch { /* file I/O failure must never crash the server */ }
}

/**
 * Primary logging function — import and call from anywhere in the codebase.
 */
export function empireLog(
  level: LogLevel,
  module: string,
  message: string,
  data?: unknown,
  ms?: number,
): LogEntry {
  const entry: LogEntry = {
    id:        (++entrySeq).toString(36),
    timestamp: new Date().toISOString(),
    level,
    module,
    message,
    ...(data !== undefined ? { data } : {}),
    ...(ms   !== undefined ? { ms }   : {}),
  }

  // Write to ring buffer (circular)
  if (ring.length < RING_MAX) {
    ring.push(entry)
  } else {
    ring[ringHead] = entry
    ringHead = (ringHead + 1) % RING_MAX
  }

  // Write to daily file
  writeToFile(entry)

  // Mirror critical levels to stderr
  if (level === 'ERROR') {
    process.stderr.write(`[${entry.timestamp}] [ERROR] [${module}] ${message}\n`)
  } else if (level === 'WARN') {
    process.stderr.write(`[${entry.timestamp}] [WARN]  [${module}] ${message}\n`)
  }

  return entry
}

/** Convenience aliases */
export const logDebug = (m: string, msg: string, d?: unknown) => empireLog('DEBUG', m, msg, d)
export const logInfo  = (m: string, msg: string, d?: unknown) => empireLog('INFO',  m, msg, d)
export const logWarn  = (m: string, msg: string, d?: unknown) => empireLog('WARN',  m, msg, d)
export const logError = (m: string, msg: string, d?: unknown) => empireLog('ERROR', m, msg, d)

// ── Query helpers ─────────────────────────────────────────────────────────────

/**
 * Returns entries in chronological order (oldest first).
 * The ring may be partially filled or wrapped — this reconstructs order.
 */
function getRingOrdered(): LogEntry[] {
  if (ring.length < RING_MAX) {
    return [...ring]
  }
  // Wrapped: ringHead points to oldest slot
  return [...ring.slice(ringHead), ...ring.slice(0, ringHead)]
}

function searchEntries(opts: {
  q?:      string
  level?:  LogLevel
  module?: string
  limit?:  number
  since?:  string
}): LogEntry[] {
  const minRank = opts.level ? LEVEL_RANK[opts.level] : 0
  const since   = opts.since ? new Date(opts.since).getTime() : 0
  const limit   = Math.min(opts.limit ?? 100, 1_000)
  const q       = opts.q?.toLowerCase()

  const all = getRingOrdered().reverse()  // newest first

  const filtered = all.filter(e => {
    if (LEVEL_RANK[e.level] < minRank) return false
    if (opts.module && e.module !== opts.module) return false
    if (since && new Date(e.timestamp).getTime() < since) return false
    if (q && !e.message.toLowerCase().includes(q) && !JSON.stringify(e.data ?? '').toLowerCase().includes(q)) return false
    return true
  })

  return filtered.slice(0, limit)
}

function getStats(): Record<string, unknown> {
  const all      = getRingOrdered()
  const byLevel  = { DEBUG: 0, INFO: 0, WARN: 0, ERROR: 0 }
  const byModule: Record<string, number> = {}

  for (const e of all) {
    byLevel[e.level]++
    byModule[e.module] = (byModule[e.module] ?? 0) + 1
  }

  return {
    total:    all.length,
    capacity: RING_MAX,
    byLevel,
    byModule,
    oldestEntry: all[0]?.timestamp ?? null,
    newestEntry: all[all.length - 1]?.timestamp ?? null,
  }
}

// ── Module ────────────────────────────────────────────────────────────────────

export class EmpireLoggerModule implements EmpireModule {
  readonly moduleId = 'logger'

  private startTime = Date.now()

  async init(_services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    ensureLogDir()
    empireLog('INFO', 'logger', 'Empire Logger initialized', {
      ringCapacity: RING_MAX,
      logDir: LOG_DIR,
    })
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start  = Date.now()
    const path   = req.path === '' ? '/' : req.path
    const method = req.method

    try {
      // GET /logger/recent?limit=100
      if (path === '/recent' && method === 'GET') {
        const limit  = Math.min(Number(this.qp(req, 'limit') ?? 100), 1_000)
        const entries = getRingOrdered().reverse().slice(0, limit)
        return this.ok(start, { entries, count: entries.length, total: ring.length })
      }

      // GET /logger/search?q=&level=&module=&limit=&since=
      if (path === '/search' && method === 'GET') {
        const entries = searchEntries({
          q:      this.qp(req, 'q'),
          level:  this.qp(req, 'level') as LogLevel | undefined,
          module: this.qp(req, 'module'),
          limit:  Number(this.qp(req, 'limit') ?? 100),
          since:  this.qp(req, 'since'),
        })
        return this.ok(start, { entries, count: entries.length })
      }

      // GET /logger/stats
      if (path === '/stats' && method === 'GET') {
        return this.ok(start, getStats())
      }

      // GET /logger/export  — full NDJSON
      if (path === '/export' && method === 'GET') {
        const ndjson = getRingOrdered().map(e => JSON.stringify(e)).join('\n')
        return {
          status: 200,
          body: ndjson,
          moduleId: this.moduleId,
          durationMs: Date.now() - start,
          headers: { 'Content-Type': 'application/x-ndjson' },
        }
      }

      // POST /logger/clear
      if (path === '/clear' && method === 'POST') {
        const count = ring.length
        ring    = []
        ringHead = 0
        empireLog('INFO', 'logger', `Ring buffer cleared (${count} entries removed)`)
        return this.ok(start, { message: 'Buffer cleared', removedEntries: count })
      }

      // GET /logger/files
      if (path === '/files' && method === 'GET') {
        try {
          const files = readdirSync(LOG_DIR)
            .filter(f => f.endsWith('.log'))
            .sort()
            .reverse()
            .map(f => ({
              name:    f,
              path:    join(LOG_DIR, f),
              sizeKB:  Math.round(statSync(join(LOG_DIR, f)).size / 1024),
              date:    f.replace('empire-', '').replace('.log', ''),
            }))
          return this.ok(start, { files, count: files.length, logDir: LOG_DIR })
        } catch {
          return this.ok(start, { files: [], count: 0, logDir: LOG_DIR })
        }
      }

      // GET /logger/health
      if (path === '/health' && method === 'GET') {
        const h = await this.health()
        return this.ok(start, h)
      }

      // GET /logger/ — summary
      if ((path === '/' || path === '') && method === 'GET') {
        return this.ok(start, {
          module:   'Empire Logger',
          status:   'active',
          entries:  ring.length,
          capacity: RING_MAX,
          logDir:   LOG_DIR,
          endpoints: {
            recent:  'GET /logger/recent?limit=100',
            search:  'GET /logger/search?q=&level=ERROR&module=executive&limit=50',
            stats:   'GET /logger/stats',
            export:  'GET /logger/export',
            files:   'GET /logger/files',
            clear:   'POST /logger/clear',
          },
        })
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      logError('logger', `Error on ${method} ${path}`, msg)
      return this.serverError(start, msg)
    }
  }

  async health(): Promise<ModuleHealth> {
    return {
      status: 'healthy',
      details: {
        entries:   ring.length,
        capacity:  RING_MAX,
        logDir:    LOG_DIR,
        uptimeMs:  Date.now() - this.startTime,
      },
    }
  }

  async handleEvent(): Promise<void> {}
  async shutdown(): Promise<void> {
    empireLog('INFO', 'logger', 'Logger shutting down')
  }

  // ── helpers ───────────────────────────────────────────────────────────────

  private qp(req: GatewayRequest, key: string): string | undefined {
    // Parse query params from the URL path (e.g. /recent?limit=100&level=ERROR)
    const rawPath = req.path ?? ''
    const qIdx = rawPath.indexOf('?')
    if (qIdx === -1) return undefined
    return new URLSearchParams(rawPath.slice(qIdx + 1)).get(key) ?? undefined
  }

  private ok(start: number, body: unknown): GatewayResponse {
    return { status: 200, body, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private notFound(start: number, msg: string): GatewayResponse {
    return { status: 404, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private serverError(start: number, msg: string): GatewayResponse {
    return { status: 500, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
}
