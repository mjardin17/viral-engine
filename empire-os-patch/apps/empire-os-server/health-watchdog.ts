/**
 * HealthWatchdog — Automatic Health Monitoring
 *
 * Background daemon that checks every service every 60 seconds.
 * Logs failures with timestamps. Writes persisted status to disk.
 * Exposes status via EmpireModule HTTP endpoints.
 *
 * Routes:
 *   GET /watchdog/status    → current health snapshot
 *   GET /watchdog/history   → last 100 check results
 *   GET /watchdog/failures  → all current failures
 *   POST /watchdog/check    → trigger immediate re-check
 *   GET /watchdog/health    → module health
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { readFileSync, writeFileSync, mkdirSync, existsSync, cpSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { execSync } from 'node:child_process'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ServiceCheck {
  id:            string
  name:          string
  url:           string
  critical:      boolean
  timeout:       number
  /** Windows command to attempt restart if offline (optional) */
  restartCmd?:   string
}

export interface CheckResult {
  serviceId:      string
  serviceName:    string
  status:         'ok' | 'offline' | 'degraded'
  latencyMs:      number
  statusCode?:    number
  error?:         string
  checkedAt:      string
  restartAttempted?: boolean
  restartResult?:    string
}

export interface WatchdogSnapshot {
  allOk:       boolean
  failureCount:number
  services:    CheckResult[]
  checkedAt:   string
  nextCheckIn: number
}

// ── Service registry ──────────────────────────────────────────────────────────

const EMPIRE_DIR = process.env.EMPIRE_DIR ?? 'C:\\Users\\jjard\\claude\\video-bot-pipeline\\empire-os-patch\\apps\\empire-os-server'

const SERVICES: ServiceCheck[] = [
  {
    id: 'empire-os', name: 'Empire OS Server',
    url: 'http://localhost:3001/health', critical: true, timeout: 5000,
    // Can't restart self from within self — just log
  },
  {
    id: 'ollama', name: 'Ollama Local AI',
    url: 'http://localhost:11434/api/tags', critical: true, timeout: 5000,
    restartCmd: 'start "" "ollama" serve',
  },
  {
    id: 'open-webui', name: 'Open WebUI',
    url: 'http://127.0.0.1:42004/', critical: false, timeout: 4000,
    // Managed by Pinokio — no restart command
  },
  // Empire OS modules — checked via their health endpoints
  {
    id: 'empire-assistant', name: 'Empire Assistant',
    url: 'http://localhost:3001/empire-assistant/health', critical: true, timeout: 5000,
  },
  {
    id: 'health-monitor', name: 'Health Monitor',
    url: 'http://localhost:3001/health-monitor/health', critical: false, timeout: 5000,
  },
  {
    id: 'knowledge-base', name: 'Knowledge Base',
    url: 'http://localhost:3001/knowledge-base/health', critical: false, timeout: 5000,
  },
  {
    id: 'video-factory', name: 'Video Factory',
    url: 'http://localhost:3001/video-factory/health', critical: true, timeout: 5000,
  },
  {
    id: 'executive', name: 'Autonomous Executive',
    url: 'http://localhost:3001/executive/health', critical: true, timeout: 5000,
  },
  {
    id: 'discovery-engine', name: 'Discovery Engine',
    url: 'http://localhost:3001/discovery-engine/health', critical: false, timeout: 5000,
  },
  {
    id: 'media-engine', name: 'Media Engine',
    url: 'http://localhost:3001/media-engine/health', critical: false, timeout: 5000,
  },
]

const CHECK_INTERVAL_MS  = 60_000
const BACKUP_INTERVAL_MS = 60 * 60 * 1000   // 1 hour
const BACKUP_KEEP        = 24                // keep 24 rolling backups
const DATA_DIR           = '.empire-data'
const STATUS_FILE        = join(DATA_DIR, 'watchdog-status.json')
const BACKUP_DIR         = join(DATA_DIR, 'backups')
const HISTORY_MAX        = 100

// Track which services have had a restart attempted to avoid restart-loops
const restartAttemptedAt: Map<string, number> = new Map()
const RESTART_COOLDOWN_MS = 5 * 60 * 1000   // only retry restart every 5 min

// ── Module ────────────────────────────────────────────────────────────────────

export class HealthWatchdogModule implements EmpireModule {
  readonly moduleId = 'watchdog'

  private intervalHandle:  ReturnType<typeof setInterval> | null = null
  private backupHandle:    ReturnType<typeof setInterval> | null = null
  private latestSnapshot:  WatchdogSnapshot | null = null
  private history:         WatchdogSnapshot[] = []
  private startTime =      Date.now()
  private backupCount =    0

  async init(_services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    ensureDataDir()
    ensureBackupDir()
    loadPersisted(this)

    // Immediate first check
    await this.runCheck()

    // Schedule recurring health checks
    this.intervalHandle = setInterval(() => {
      this.runCheck().catch(e => {
        console.error(`[Watchdog] Check failed: ${e instanceof Error ? e.message : String(e)}`)
      })
    }, CHECK_INTERVAL_MS)

    // Schedule rolling backups every hour
    this.backupHandle = setInterval(() => {
      this.runBackup()
    }, BACKUP_INTERVAL_MS)

    console.log('[Watchdog] Health monitoring active — checking every 60 seconds')
    console.log(`[Watchdog] Monitoring ${SERVICES.length} services`)
    console.log('[Watchdog] Rolling backups enabled — every 1 hour, keeping 24 copies')
  }

  async shutdown(): Promise<void> {
    if (this.intervalHandle) {
      clearInterval(this.intervalHandle)
      this.intervalHandle = null
    }
    if (this.backupHandle) {
      clearInterval(this.backupHandle)
      this.backupHandle = null
    }
    console.log('[Watchdog] Stopped')
  }

  private runBackup(): void {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const dest = join(BACKUP_DIR, `backup-${timestamp}`)
      cpSync(DATA_DIR, dest, { recursive: true, filter: (src) => !src.includes('backups') })
      this.backupCount++
      console.log(`[Watchdog] Backup ${this.backupCount}: ${dest}`)
      pruneBackups()
    } catch (e) {
      console.error(`[Watchdog] Backup failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  async health(): Promise<ModuleHealth> {
    const snap = this.latestSnapshot
    return {
      status: snap ? (snap.allOk ? 'healthy' : 'degraded') : 'healthy',
      details: {
        lastCheck: snap?.checkedAt ?? 'never',
        failures:  snap?.failureCount ?? 0,
        services:  SERVICES.length,
        uptimeMs:  Date.now() - this.startTime,
      },
    }
  }

  async handleEvent(): Promise<void> {}

  // ── Core check logic ────────────────────────────────────────────────────────

  async runCheck(): Promise<WatchdogSnapshot> {
    const results = await Promise.all(SERVICES.map(svc => checkService(svc)))

    // Auto-restart critical services that are offline
    for (const result of results) {
      if (result.status === 'offline') {
        const svc = SERVICES.find(s => s.id === result.serviceId)
        if (svc?.critical && svc.restartCmd) {
          const lastAttempt = restartAttemptedAt.get(svc.id) ?? 0
          if (Date.now() - lastAttempt > RESTART_COOLDOWN_MS) {
            restartAttemptedAt.set(svc.id, Date.now())
            const restartResult = attemptRestart(svc)
            result.restartAttempted = true
            result.restartResult    = restartResult
          }
        }
      }
    }

    const failures = results.filter(r => r.status !== 'ok')

    logResults(results)

    const snapshot: WatchdogSnapshot = {
      allOk:        failures.length === 0,
      failureCount: failures.length,
      services:     results,
      checkedAt:    new Date().toISOString(),
      nextCheckIn:  CHECK_INTERVAL_MS / 1000,
    }

    this.latestSnapshot = snapshot
    this.history.unshift(snapshot)
    if (this.history.length > HISTORY_MAX) this.history.length = HISTORY_MAX

    persistSnapshot(snapshot)
    return snapshot
  }

  // ── HTTP handler ─────────────────────────────────────────────────────────────

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start  = Date.now()
    const path   = req.path === '' ? '/' : req.path
    const method = req.method

    try {
      // GET /watchdog/status
      if ((path === '/' || path === '/status') && method === 'GET') {
        const snap = this.latestSnapshot ?? await this.runCheck()
        return this.ok(start, snap)
      }

      // GET /watchdog/history
      if (path === '/history' && method === 'GET') {
        return this.ok(start, { history: this.history.slice(0, 50), total: this.history.length })
      }

      // GET /watchdog/failures
      if (path === '/failures' && method === 'GET') {
        const failures = this.latestSnapshot?.services.filter(s => s.status !== 'ok') ?? []
        return this.ok(start, { failures, count: failures.length, allOk: failures.length === 0 })
      }

      // POST /watchdog/check
      if (path === '/check' && method === 'POST') {
        const snap = await this.runCheck()
        return this.ok(start, snap)
      }

      // GET /watchdog/health
      if (path === '/health' && method === 'GET') {
        const h = await this.health()
        return this.ok(start, h)
      }

      // POST /watchdog/backup — trigger manual backup now
      if (path === '/backup' && method === 'POST') {
        this.runBackup()
        return this.ok(start, { message: 'Backup triggered', backupCount: this.backupCount, timestamp: new Date().toISOString() })
      }

      // GET /watchdog/backups — list available backups
      if (path === '/backups' && method === 'GET') {
        try {
          const entries = readdirSync(BACKUP_DIR)
            .filter(e => e.startsWith('backup-'))
            .sort()
            .reverse()
          return this.ok(start, { backups: entries, count: entries.length, backupDir: BACKUP_DIR })
        } catch {
          return this.ok(start, { backups: [], count: 0, note: 'No backups yet' })
        }
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[Watchdog] Error on ${method} ${path}: ${msg}`)
      return this.serverError(start, msg)
    }
  }

  // ── Response helpers ────────────────────────────────────────────────────────

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

// ── Helpers ───────────────────────────────────────────────────────────────────

async function checkService(svc: ServiceCheck): Promise<CheckResult> {
  const t0 = Date.now()
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), svc.timeout)

    const res = await fetch(svc.url, { signal: ctrl.signal })
    clearTimeout(timer)

    return {
      serviceId:   svc.id,
      serviceName: svc.name,
      status:      res.ok ? 'ok' : 'degraded',
      latencyMs:   Date.now() - t0,
      statusCode:  res.status,
      checkedAt:   new Date().toISOString(),
    }
  } catch (e) {
    const isTimeout = e instanceof Error && e.name === 'AbortError'
    return {
      serviceId:   svc.id,
      serviceName: svc.name,
      status:      'offline',
      latencyMs:   Date.now() - t0,
      error:       isTimeout ? 'timeout' : (e instanceof Error ? e.message : String(e)),
      checkedAt:   new Date().toISOString(),
    }
  }
}

function logResults(results: CheckResult[]): void {
  const ts      = new Date().toISOString()
  const ok      = results.filter(r => r.status === 'ok').length
  const offline = results.filter(r => r.status === 'offline')
  const degraded = results.filter(r => r.status === 'degraded')

  console.log(`[Watchdog] ${ts} — ${ok}/${results.length} OK`)

  for (const f of offline) {
    console.error(`[Watchdog] ❌ OFFLINE  ${f.serviceName} — ${f.error ?? 'no response'}`)
  }
  for (const d of degraded) {
    console.warn(`[Watchdog] ⚠️  DEGRADED ${d.serviceName} — HTTP ${d.statusCode}`)
  }
}

function ensureDataDir(): void {
  if (!existsSync(DATA_DIR)) {
    mkdirSync(DATA_DIR, { recursive: true })
  }
}

function ensureBackupDir(): void {
  if (!existsSync(BACKUP_DIR)) {
    mkdirSync(BACKUP_DIR, { recursive: true })
  }
}

function pruneBackups(): void {
  try {
    const entries = readdirSync(BACKUP_DIR)
      .filter(e => e.startsWith('backup-'))
      .sort()                         // oldest first (ISO timestamps sort lexicographically)
    const excess = entries.length - BACKUP_KEEP
    if (excess > 0) {
      for (const old of entries.slice(0, excess)) {
        try {
          execSync(`rmdir /s /q "${join(BACKUP_DIR, old)}"`, { stdio: 'ignore' })
        } catch { /* ignore individual prune failures */ }
      }
      console.log(`[Watchdog] Pruned ${excess} old backup(s). Keeping ${BACKUP_KEEP}.`)
    }
  } catch { /* non-fatal */ }
}

function attemptRestart(svc: ServiceCheck): string {
  if (!svc.restartCmd) return 'no restart command configured'
  try {
    console.warn(`[Watchdog] 🔄 Attempting restart of ${svc.name}: ${svc.restartCmd}`)
    execSync(svc.restartCmd, { shell: true, stdio: 'ignore', timeout: 10_000 })
    return `restart command issued at ${new Date().toISOString()}`
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    console.error(`[Watchdog] ❌ Restart failed for ${svc.name}: ${msg}`)
    return `restart failed: ${msg}`
  }
}

function persistSnapshot(snap: WatchdogSnapshot): void {
  try {
    writeFileSync(STATUS_FILE, JSON.stringify(snap, null, 2), 'utf8')
  } catch {
    // Non-fatal — log but continue
  }
}

function loadPersisted(mod: HealthWatchdogModule): void {
  try {
    if (existsSync(STATUS_FILE)) {
      const raw  = readFileSync(STATUS_FILE, 'utf8')
      const snap = JSON.parse(raw) as WatchdogSnapshot
      // Only use if less than 5 minutes old
      if (Date.now() - new Date(snap.checkedAt).getTime() < 300_000) {
        ;(mod as unknown as { latestSnapshot: WatchdogSnapshot }).latestSnapshot = snap
      }
    }
  } catch {
    // ignore stale/corrupt file
  }
}
