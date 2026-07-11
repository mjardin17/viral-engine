/**
 * JobScheduler — Background Job Scheduling Engine
 *
 * Supports both cron expressions and fixed interval schedules.
 * Jobs can be enabled/disabled and triggered manually.
 * All job run history is kept in a rolling log (200 entries per job).
 *
 * Built-in production jobs:
 *   - hourly-backup      → triggers POST /watchdog/backup every hour
 *   - daily-discovery    → triggers POST /discovery-engine/scan every 24h
 *   - weekly-log-rotate  → cleans up old log files every 7 days
 *   - nightly-self-check → runs POST /self-improvement/analyze every night
 *
 * Routes:
 *   GET  /job-scheduler/           → status + job list
 *   GET  /job-scheduler/jobs       → all jobs with last run info
 *   GET  /job-scheduler/jobs/:id   → single job detail + history
 *   POST /job-scheduler/jobs/:id/run     → trigger manually
 *   POST /job-scheduler/jobs/:id/enable  → enable a disabled job
 *   POST /job-scheduler/jobs/:id/disable → disable a running job
 *   GET  /job-scheduler/history    → last 100 completed runs across all jobs
 *   GET  /job-scheduler/health     → module health
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { empireLog } from './logger.module.js'

// ── Types ─────────────────────────────────────────────────────────────────────

export type JobStatus = 'idle' | 'running' | 'disabled' | 'error'

export interface JobRun {
  runId:       string
  jobId:       string
  startedAt:   string
  completedAt: string | null
  success:     boolean
  durationMs:  number | null
  output:      string | null
  error:       string | null
}

export interface ScheduledJob {
  id:              string
  name:            string
  description:     string
  intervalMs:      number    // how often to run (ms); cron not supported without a library
  enabled:         boolean
  runCount:        number
  errorCount:      number
  lastRunAt:       string | null
  nextRunAt:       string | null
  status:          JobStatus
  history:         JobRun[]
  handler:         () => Promise<string>  // returns output string
}

// ── Singleton job registry ────────────────────────────────────────────────────

const jobs = new Map<string, ScheduledJob>()
const globalHistory: JobRun[] = []
const HISTORY_MAX_PER_JOB = 200
const GLOBAL_HISTORY_MAX  = 500
let   runSeq = 0

// ── Scheduler internals ───────────────────────────────────────────────────────

const timers = new Map<string, ReturnType<typeof setInterval>>()

function scheduleJob(job: ScheduledJob): void {
  clearJobTimer(job.id)
  if (!job.enabled) return

  // Compute initial delay: if we've never run, run soon (30s), otherwise wait out the interval
  const now       = Date.now()
  const lastMs    = job.lastRunAt ? new Date(job.lastRunAt).getTime() : 0
  const elapsed   = now - lastMs
  const remaining = Math.max(0, job.intervalMs - elapsed)
  const firstDelay = job.lastRunAt ? remaining : 30_000  // first run 30s after init

  const timer = setTimeout(async () => {
    await executeJob(job.id)
    // After first run, switch to regular interval
    if (job.enabled) {
      const interval = setInterval(() => executeJob(job.id), job.intervalMs)
      timers.set(job.id, interval)
    }
  }, firstDelay)

  job.nextRunAt = new Date(now + firstDelay).toISOString()
  timers.set(job.id, timer)
}

function clearJobTimer(id: string): void {
  const t = timers.get(id)
  if (t !== undefined) {
    clearTimeout(t as ReturnType<typeof setTimeout>)
    clearInterval(t as ReturnType<typeof setInterval>)
    timers.delete(id)
  }
}

async function executeJob(id: string): Promise<JobRun> {
  const job = jobs.get(id)
  if (!job || !job.enabled) {
    return { runId: '', jobId: id, startedAt: '', completedAt: '', success: false, durationMs: null, output: null, error: 'Job not found or disabled' }
  }

  job.status    = 'running'
  job.lastRunAt = new Date().toISOString()
  job.nextRunAt = new Date(Date.now() + job.intervalMs).toISOString()
  const startMs = Date.now()
  const runId   = `${id}-${(++runSeq).toString(36)}`

  const run: JobRun = {
    runId,
    jobId:       id,
    startedAt:   job.lastRunAt,
    completedAt: null,
    success:     false,
    durationMs:  null,
    output:      null,
    error:       null,
  }

  try {
    empireLog('INFO', 'job-scheduler', `Job starting: ${id}`)
    const output   = await job.handler()
    run.success    = true
    run.output     = output
    job.runCount++
    job.status     = 'idle'
    empireLog('INFO', 'job-scheduler', `Job complete: ${id}`, { output: output.slice(0, 200) })
  } catch (e) {
    const msg   = e instanceof Error ? e.message : String(e)
    run.error   = msg
    run.success = false
    job.errorCount++
    job.status  = 'error'
    empireLog('ERROR', 'job-scheduler', `Job failed: ${id}`, msg)
    // Reset to idle after error so it runs again next interval
    setTimeout(() => { if (jobs.get(id)?.status === 'error') { const j = jobs.get(id); if (j) j.status = 'idle' } }, 5_000)
  }

  run.completedAt = new Date().toISOString()
  run.durationMs  = Date.now() - startMs

  // Prepend to per-job history
  job.history.unshift(run)
  if (job.history.length > HISTORY_MAX_PER_JOB) job.history.length = HISTORY_MAX_PER_JOB

  // Prepend to global history
  globalHistory.unshift(run)
  if (globalHistory.length > GLOBAL_HISTORY_MAX) globalHistory.length = GLOBAL_HISTORY_MAX

  return run
}

// ── Built-in job definitions ──────────────────────────────────────────────────

function makeHttpJob(name: string, method: 'GET' | 'POST', url: string): () => Promise<string> {
  return async () => {
    const res = await fetch(url, {
      method,
      signal: AbortSignal.timeout(30_000),
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status} from ${url}`)
    const body = await res.text()
    return `${method} ${url} → ${res.status} (${body.length} bytes)`
  }
}

function registerBuiltinJobs(): void {
  const builtins: Omit<ScheduledJob, 'handler'>[] = [
    {
      id:          'hourly-backup',
      name:        'Hourly .empire-data Backup',
      description: 'Triggers the watchdog to snapshot .empire-data/ to .empire-data/backups/',
      intervalMs:  60 * 60 * 1_000,   // 1 hour
      enabled:     true,
      runCount:    0,
      errorCount:  0,
      lastRunAt:   null,
      nextRunAt:   null,
      status:      'idle',
      history:     [],
    },
    {
      id:          'daily-discovery',
      name:        'Daily Discovery Engine Scan',
      description: 'Rescans Ollama library, HuggingFace, and GitHub for new AI models',
      intervalMs:  24 * 60 * 60 * 1_000,  // 24 hours
      enabled:     true,
      runCount:    0,
      errorCount:  0,
      lastRunAt:   null,
      nextRunAt:   null,
      status:      'idle',
      history:     [],
    },
    {
      id:          'nightly-self-check',
      name:        'Nightly Self-Improvement Analysis',
      description: 'Analyzes benchmark history and queues model upgrade recommendations',
      intervalMs:  24 * 60 * 60 * 1_000,  // 24 hours
      enabled:     true,
      runCount:    0,
      errorCount:  0,
      lastRunAt:   null,
      nextRunAt:   null,
      status:      'idle',
      history:     [],
    },
    {
      id:          'weekly-log-rotate',
      name:        'Weekly Log File Rotation',
      description: 'Removes log files older than 14 days from .empire-data/logs/',
      intervalMs:  7 * 24 * 60 * 60 * 1_000,  // 7 days
      enabled:     true,
      runCount:    0,
      errorCount:  0,
      lastRunAt:   null,
      nextRunAt:   null,
      status:      'idle',
      history:     [],
    },
  ]

  const BASE = process.env.EMPIRE_BASE_URL ?? 'http://localhost:3001'
  const handlers: Record<string, () => Promise<string>> = {
    'hourly-backup':       makeHttpJob('hourly-backup',       'POST', `${BASE}/watchdog/backup`),
    'daily-discovery':     makeHttpJob('daily-discovery',     'POST', `${BASE}/discovery-engine/scan`),
    'nightly-self-check':  makeHttpJob('nightly-self-check',  'POST', `${BASE}/self-improvement/analyze`),
    'weekly-log-rotate':   logRotationHandler,
  }

  for (const def of builtins) {
    const job: ScheduledJob = { ...def, handler: handlers[def.id]! }
    jobs.set(def.id, job)
  }
}

async function logRotationHandler(): Promise<string> {
  const { readdirSync, statSync, unlinkSync } = await import('node:fs')
  const { join } = await import('node:path')
  const LOG_DIR   = '.empire-data/logs'
  const cutoffMs  = Date.now() - 14 * 24 * 60 * 60 * 1_000  // 14 days

  try {
    const files   = readdirSync(LOG_DIR).filter((f: string) => f.endsWith('.log'))
    let   removed = 0
    for (const f of files) {
      const fp   = join(LOG_DIR, f)
      const mtime = statSync(fp).mtimeMs
      if (mtime < cutoffMs) {
        unlinkSync(fp)
        removed++
      }
    }
    return `Rotated ${removed} of ${files.length} log files (older than 14 days)`
  } catch (e) {
    throw new Error(`Log rotation failed: ${e instanceof Error ? e.message : String(e)}`)
  }
}

// ── Module ────────────────────────────────────────────────────────────────────

export class JobSchedulerModule implements EmpireModule {
  readonly moduleId = 'job-scheduler'

  async init(_services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    registerBuiltinJobs()
    for (const job of jobs.values()) {
      scheduleJob(job)
    }
    empireLog('INFO', 'job-scheduler', `Job scheduler started`, { jobCount: jobs.size })
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start  = Date.now()
    const path   = (req.path === '' ? '/' : req.path).split('?')[0]
    const method = req.method

    try {
      // GET / — status overview
      if ((path === '/' || path === '') && method === 'GET') {
        return this.ok(start, {
          module:    'Job Scheduler',
          status:    'active',
          jobCount:  jobs.size,
          enabledCount: [...jobs.values()].filter(j => j.enabled).length,
          totalRuns: [...jobs.values()].reduce((s, j) => s + j.runCount, 0),
          endpoints: {
            jobs:    'GET /job-scheduler/jobs',
            job:     'GET /job-scheduler/jobs/:id',
            run:     'POST /job-scheduler/jobs/:id/run',
            enable:  'POST /job-scheduler/jobs/:id/enable',
            disable: 'POST /job-scheduler/jobs/:id/disable',
            history: 'GET /job-scheduler/history',
          },
        })
      }

      // GET /jobs — all jobs
      if (path === '/jobs' && method === 'GET') {
        const list = [...jobs.values()].map(j => this.jobSummary(j))
        return this.ok(start, { jobs: list, total: list.length })
      }

      // GET /jobs/:id
      const jobMatch = path.match(/^\/jobs\/([^/]+)$/)
      if (jobMatch && method === 'GET') {
        const job = jobs.get(jobMatch[1])
        if (!job) return this.notFound(start, `Job not found: ${jobMatch[1]}`)
        return this.ok(start, { ...this.jobSummary(job), history: job.history.slice(0, 50) })
      }

      // POST /jobs/:id/run
      const runMatch = path.match(/^\/jobs\/([^/]+)\/run$/)
      if (runMatch && method === 'POST') {
        const id  = runMatch[1]
        const job = jobs.get(id)
        if (!job) return this.notFound(start, `Job not found: ${id}`)
        if (job.status === 'running') {
          return this.conflict(start, `Job ${id} is already running`)
        }
        // Run in background — don't await the full result
        const runPromise = executeJob(id)
        const run        = await runPromise  // for manual triggers, we wait
        return this.ok(start, {
          message:    `Job ${id} triggered`,
          run:        { runId: run.runId, success: run.success, durationMs: run.durationMs, output: run.output, error: run.error },
          jobStatus:  jobs.get(id)?.status,
        })
      }

      // POST /jobs/:id/enable
      const enableMatch = path.match(/^\/jobs\/([^/]+)\/enable$/)
      if (enableMatch && method === 'POST') {
        const id  = enableMatch[1]
        const job = jobs.get(id)
        if (!job) return this.notFound(start, `Job not found: ${id}`)
        job.enabled = true
        job.status  = 'idle'
        scheduleJob(job)
        empireLog('INFO', 'job-scheduler', `Job enabled: ${id}`)
        return this.ok(start, { message: `Job ${id} enabled`, nextRunAt: job.nextRunAt })
      }

      // POST /jobs/:id/disable
      const disableMatch = path.match(/^\/jobs\/([^/]+)\/disable$/)
      if (disableMatch && method === 'POST') {
        const id  = disableMatch[1]
        const job = jobs.get(id)
        if (!job) return this.notFound(start, `Job not found: ${id}`)
        job.enabled  = false
        job.status   = 'disabled'
        job.nextRunAt = null
        clearJobTimer(id)
        empireLog('INFO', 'job-scheduler', `Job disabled: ${id}`)
        return this.ok(start, { message: `Job ${id} disabled` })
      }

      // GET /history — global run history
      if (path === '/history' && method === 'GET') {
        return this.ok(start, { history: globalHistory.slice(0, 100), total: globalHistory.length })
      }

      // GET /health
      if (path === '/health' && method === 'GET') {
        return this.ok(start, await this.health())
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      empireLog('ERROR', 'job-scheduler', `Error on ${method} ${path}`, msg)
      return this.serverError(start, msg)
    }
  }

  async health(): Promise<ModuleHealth> {
    const jobList   = [...jobs.values()]
    const errJobs   = jobList.filter(j => j.status === 'error').map(j => j.id)
    return {
      status:  errJobs.length === 0 ? 'healthy' : 'degraded',
      details: {
        jobCount:    jobs.size,
        enabled:     jobList.filter(j => j.enabled).length,
        errorJobs:   errJobs,
        totalRuns:   jobList.reduce((s, j) => s + j.runCount, 0),
        totalErrors: jobList.reduce((s, j) => s + j.errorCount, 0),
      },
    }
  }

  async handleEvent(): Promise<void> {}

  async shutdown(): Promise<void> {
    for (const id of timers.keys()) clearJobTimer(id)
    empireLog('INFO', 'job-scheduler', 'Job scheduler stopped', { jobCount: jobs.size })
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  private jobSummary(j: ScheduledJob) {
    return {
      id:          j.id,
      name:        j.name,
      description: j.description,
      enabled:     j.enabled,
      status:      j.status,
      intervalMs:  j.intervalMs,
      intervalHuman: this.humanInterval(j.intervalMs),
      runCount:    j.runCount,
      errorCount:  j.errorCount,
      lastRunAt:   j.lastRunAt,
      nextRunAt:   j.nextRunAt,
    }
  }

  private humanInterval(ms: number): string {
    const h = Math.round(ms / 3_600_000)
    if (h >= 24) return `${Math.round(h / 24)}d`
    if (h >= 1)  return `${h}h`
    return `${Math.round(ms / 60_000)}m`
  }

  private ok(start: number, body: unknown): GatewayResponse {
    return { status: 200, body, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private notFound(start: number, msg: string): GatewayResponse {
    return { status: 404, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private conflict(start: number, msg: string): GatewayResponse {
    return { status: 409, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private serverError(start: number, msg: string): GatewayResponse {
    return { status: 500, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
}
