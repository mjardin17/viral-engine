/**
 * MetricsEngine — Live API Performance Profiling
 *
 * Collects per-module request timing, error rates, and throughput.
 * Uses a fixed-size rolling window for accurate P50/P95/P99 percentiles.
 * System-wide req/min computed from a sliding 60-second bucket.
 *
 * Called by server.ts after every module.handleRequest():
 *   metricsEngine.record(moduleId, durationMs, statusCode, method, path)
 *
 * Routes:
 *   GET /metrics-engine/          → system summary
 *   GET /metrics-engine/summary   → full metrics for all modules
 *   GET /metrics-engine/module/:id → per-module detail + recent requests
 *   GET /metrics-engine/realtime  → live snapshot (call every few seconds)
 *   GET /metrics-engine/slowest   → top 20 slowest recent requests
 *   GET /metrics-engine/errors    → recent error requests
 *   GET /metrics-engine/export    → full JSON export
 *   POST /metrics-engine/reset    → reset all counters
 *   GET /metrics-engine/health    → module health
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { empireLog } from './logger.module.js'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RequestRecord {
  moduleId:   string
  method:     string
  path:       string
  statusCode: number
  durationMs: number
  timestamp:  string
  isError:    boolean
}

export interface ModuleMetrics {
  moduleId:      string
  requestCount:  number
  errorCount:    number
  errorRate:     number   // 0–1
  avgDurationMs: number
  p50:           number
  p95:           number
  p99:           number
  minDuration:   number
  maxDuration:   number
  lastSeenAt:    string | null
  recentRequests:RequestRecord[]
}

export interface SystemMetrics {
  totalRequests:  number
  totalErrors:    number
  systemErrorRate:number
  reqPerMin:      number
  avgDurationMs:  number
  p95:            number
  activeModules:  number
  uptimeMs:       number
  sampledAt:      string
}

// ── Constants ─────────────────────────────────────────────────────────────────

const WINDOW_SIZE    = 1_000   // rolling window per module
const RECENT_MAX     = 50      // recent requests kept per module
const GLOBAL_MAX     = 500     // global recent request log
const REQ_MIN_WINDOW = 60_000  // 60s window for req/min calculation

// ── Metrics store ─────────────────────────────────────────────────────────────

/** Rolling window of durations per module — sorted on insertion for O(1) percentile */
const durationWindows  = new Map<string, number[]>()
const requestCounts    = new Map<string, number>()
const errorCounts      = new Map<string, number>()
const lastSeen         = new Map<string, string>()
const recentByModule   = new Map<string, RequestRecord[]>()
const globalRecent:    RequestRecord[] = []
const globalTimestamps: number[] = []  // epoch ms, for req/min

let totalRequests  = 0
let totalErrors    = 0
let startTime      = Date.now()

// ── Percentile calculation ────────────────────────────────────────────────────

function insertSorted(arr: number[], val: number): void {
  let lo = 0, hi = arr.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (arr[mid] < val) lo = mid + 1
    else hi = mid
  }
  arr.splice(lo, 0, val)
  if (arr.length > WINDOW_SIZE) arr.shift()
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0
  const idx = Math.floor((p / 100) * (sorted.length - 1))
  return sorted[Math.max(0, Math.min(idx, sorted.length - 1))]
}

// ── Public record API ─────────────────────────────────────────────────────────

export function recordMetric(
  moduleId:   string,
  durationMs: number,
  statusCode: number,
  method:     string,
  path:       string,
): void {
  const now     = new Date().toISOString()
  const isError = statusCode >= 400

  totalRequests++
  if (isError) totalErrors++

  // Timestamp bucket for req/min
  const nowMs = Date.now()
  globalTimestamps.push(nowMs)
  // Prune entries older than the window
  const cutoff = nowMs - REQ_MIN_WINDOW
  let i = 0
  while (i < globalTimestamps.length && globalTimestamps[i] < cutoff) i++
  if (i > 0) globalTimestamps.splice(0, i)

  // Per-module counters
  requestCounts.set(moduleId, (requestCounts.get(moduleId) ?? 0) + 1)
  if (isError) errorCounts.set(moduleId, (errorCounts.get(moduleId) ?? 0) + 1)
  lastSeen.set(moduleId, now)

  // Duration window
  let window = durationWindows.get(moduleId)
  if (!window) {
    window = []
    durationWindows.set(moduleId, window)
  }
  insertSorted(window, durationMs)

  // Recent requests per module
  const record: RequestRecord = { moduleId, method, path, statusCode, durationMs, timestamp: now, isError }
  let recent = recentByModule.get(moduleId)
  if (!recent) {
    recent = []
    recentByModule.set(moduleId, recent)
  }
  recent.unshift(record)
  if (recent.length > RECENT_MAX) recent.length = RECENT_MAX

  // Global recent log
  globalRecent.unshift(record)
  if (globalRecent.length > GLOBAL_MAX) globalRecent.length = GLOBAL_MAX
}

// ── Aggregation helpers ───────────────────────────────────────────────────────

function buildModuleMetrics(moduleId: string): ModuleMetrics {
  const window   = durationWindows.get(moduleId) ?? []
  const reqCount = requestCounts.get(moduleId)   ?? 0
  const errCount = errorCounts.get(moduleId)     ?? 0
  const recent   = recentByModule.get(moduleId)  ?? []

  return {
    moduleId,
    requestCount:   reqCount,
    errorCount:     errCount,
    errorRate:      reqCount > 0 ? errCount / reqCount : 0,
    avgDurationMs:  window.length > 0 ? Math.round(window.reduce((a, b) => a + b, 0) / window.length) : 0,
    p50:            percentile(window, 50),
    p95:            percentile(window, 95),
    p99:            percentile(window, 99),
    minDuration:    window.length > 0 ? window[0] : 0,
    maxDuration:    window.length > 0 ? window[window.length - 1] : 0,
    lastSeenAt:     lastSeen.get(moduleId) ?? null,
    recentRequests: recent.slice(0, 20),
  }
}

function buildSystemMetrics(): SystemMetrics {
  const allWindows  = [...durationWindows.values()]
  const allDurations = ([] as number[]).concat(...allWindows).sort((a, b) => a - b)
  const reqPerMin   = globalTimestamps.length  // entries in last 60s = req/min

  return {
    totalRequests,
    totalErrors,
    systemErrorRate:  totalRequests > 0 ? totalErrors / totalRequests : 0,
    reqPerMin,
    avgDurationMs:    allDurations.length > 0
      ? Math.round(allDurations.reduce((a, b) => a + b, 0) / allDurations.length)
      : 0,
    p95:              percentile(allDurations, 95),
    activeModules:    requestCounts.size,
    uptimeMs:         Date.now() - startTime,
    sampledAt:        new Date().toISOString(),
  }
}

// ── Module ────────────────────────────────────────────────────────────────────

export class MetricsEngineModule implements EmpireModule {
  readonly moduleId = 'metrics-engine'

  async init(_services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    startTime = Date.now()
    empireLog('INFO', 'metrics-engine', 'Metrics engine initialized', { windowSize: WINDOW_SIZE })
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start  = Date.now()
    const rawPath = req.path === '' ? '/' : req.path
    // Strip query string from path for routing
    const path   = rawPath.split('?')[0]
    const method = req.method

    try {
      // GET / or /summary — full system + per-module overview
      if ((path === '/' || path === '' || path === '/summary') && method === 'GET') {
        const system  = buildSystemMetrics()
        const modules = [...requestCounts.keys()].map(buildModuleMetrics)
        modules.sort((a, b) => b.requestCount - a.requestCount)
        return this.ok(start, { system, modules })
      }

      // GET /realtime — fast snapshot for dashboard polling
      if (path === '/realtime' && method === 'GET') {
        return this.ok(start, buildSystemMetrics())
      }

      // GET /module/:id
      const moduleMatch = path.match(/^\/module\/(.+)$/)
      if (moduleMatch && method === 'GET') {
        const id = moduleMatch[1]
        if (!requestCounts.has(id)) {
          return this.notFound(start, `No metrics for module: ${id}`)
        }
        return this.ok(start, buildModuleMetrics(id))
      }

      // GET /slowest — top 20 slowest recent requests system-wide
      if (path === '/slowest' && method === 'GET') {
        const slowest = [...globalRecent]
          .sort((a, b) => b.durationMs - a.durationMs)
          .slice(0, 20)
        return this.ok(start, { slowest, count: slowest.length })
      }

      // GET /errors — recent error requests
      if (path === '/errors' && method === 'GET') {
        const errors = globalRecent.filter(r => r.isError).slice(0, 50)
        return this.ok(start, { errors, count: errors.length, totalErrors })
      }

      // GET /export — full JSON export
      if (path === '/export' && method === 'GET') {
        const modules = [...requestCounts.keys()].map(buildModuleMetrics)
        return this.ok(start, {
          system:    buildSystemMetrics(),
          modules,
          allRecent: globalRecent,
          exportedAt: new Date().toISOString(),
        })
      }

      // POST /reset — reset all counters
      if (path === '/reset' && method === 'POST') {
        durationWindows.clear()
        requestCounts.clear()
        errorCounts.clear()
        lastSeen.clear()
        recentByModule.clear()
        globalRecent.length    = 0
        globalTimestamps.length = 0
        totalRequests = 0
        totalErrors   = 0
        startTime     = Date.now()
        empireLog('WARN', 'metrics-engine', 'All metrics reset')
        return this.ok(start, { message: 'All metrics reset', resetAt: new Date().toISOString() })
      }

      // GET /health
      if (path === '/health' && method === 'GET') {
        const h = await this.health()
        return this.ok(start, h)
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      empireLog('ERROR', 'metrics-engine', `Error on ${method} ${path}`, msg)
      return this.serverError(start, msg)
    }
  }

  async health(): Promise<ModuleHealth> {
    const sys = buildSystemMetrics()
    return {
      status: 'healthy',
      details: {
        totalRequests,
        totalErrors,
        reqPerMin:    sys.reqPerMin,
        activeModules: sys.activeModules,
        uptimeMs:     sys.uptimeMs,
      },
    }
  }

  async handleEvent(): Promise<void> {}
  async shutdown(): Promise<void> {
    empireLog('INFO', 'metrics-engine', 'Metrics engine shutting down', {
      totalRequests, totalErrors
    })
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
