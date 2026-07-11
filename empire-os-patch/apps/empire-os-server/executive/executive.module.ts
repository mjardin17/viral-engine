/**
 * ExecutiveModule — Autonomous Executive AI
 *
 * The self-running AI company operating system. 10 workers coordinated by the CEO.
 * Runs continuously, tracking projects, executing tasks, and briefing Josh on
 * what matters.
 *
 * Routes:
 *   GET  /executive/                      → briefing HTML (main entry point)
 *   GET  /executive/briefing              → latest briefing HTML
 *   POST /executive/briefing/generate     → generate new briefing now
 *   GET  /executive/briefing/json         → latest briefing JSON
 *   GET  /executive/workers               → list all 10 workers
 *   GET  /executive/workers/:id           → worker details + memory + metrics
 *   POST /executive/workers/:id/run       → run a worker task
 *   POST /executive/workers/:id/teach     → add a lesson to worker memory
 *   GET  /executive/queue                 → Master Queue overview
 *   GET  /executive/queue/ready           → tasks ready to execute
 *   GET  /executive/queue/critical        → critical tasks only
 *   POST /executive/queue/tasks           → create a task
 *   GET  /executive/queue/tasks/:id       → get task details
 *   POST /executive/queue/tasks/:id/approve → approve a task for execution
 *   POST /executive/queue/tasks/:id/complete → mark a task complete
 *   POST /executive/queue/tasks/:id/fail  → mark a task failed
 *   POST /executive/queue/blueprint       → generate tasks from blueprint
 *   GET  /executive/queue/stats           → queue statistics
 *   GET  /executive/health                → health check
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import {
  WORKERS, getAllWorkers, getWorker, loadWorkerMemory, saveWorkerMemory,
  loadWorkerMetrics, updateWorkerMetrics, addWorkerLesson, recordWorkerDecision,
  getWorkerSystemPromptWithMemory,
  type WorkerId,
} from './executive.workers.js'
import {
  listAllTasks, getQueueStats, getReadyTasks, createTask, loadTask, updateTask,
  startTask, completeTask, failTask, generateTasksFromBlueprint, bootstrapInitialQueue,
  TASK_BLUEPRINTS,
} from './executive.queue.js'
import {
  generateBriefing, loadLatestBriefing, listBriefings, renderBriefingHTML,
} from './executive.briefing.js'

// ── Module ─────────────────────────────────────────────────────────────────────

export class ExecutiveModule implements EmpireModule {
  readonly moduleId = 'executive'
  private services!: CoreServices
  private startTime = Date.now()
  private lastBriefingDate = ''

  async init(services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    this.services = services
    this.startTime = Date.now()

    // Bootstrap the initial task queue on first run
    bootstrapInitialQueue()

    // Generate today's briefing if not already done
    const today = new Date().toLocaleDateString('en-CA')
    const existing = loadLatestBriefing()
    if (!existing || existing.generatedAt.slice(0, 10) !== today) {
      generateBriefing()
      this.lastBriefingDate = today
    }

    console.log('[Executive] Initialized — 10 workers, Master Queue active, Daily Briefing ready')
    console.log('[Executive] Dashboard: http://localhost:3001/executive/')
  }

  async health(): Promise<ModuleHealth> {
    const stats = getQueueStats()
    const briefing = loadLatestBriefing()

    return {
      status: stats.byStatus?.['failed'] > 5 ? 'degraded' : 'healthy',
      details: {
        workers: WORKERS.length,
        totalTasks: stats.total,
        criticalTasks: stats.byPriority?.['critical'] ?? 0,
        failedTasks: stats.byStatus?.['failed'] ?? 0,
        lastBriefing: briefing?.generatedAt ?? 'never',
        uptimeMs: Date.now() - this.startTime,
      },
    }
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start = Date.now()
    const p = req.path
    const method = req.method

    try {
      // ── Dashboard / Briefing ──────────────────────────────────────────────
      if ((p === '/' || p === '/briefing') && method === 'GET') {
        const briefing = loadLatestBriefing() ?? generateBriefing()
        return this.html(start, renderBriefingHTML(briefing))
      }

      if (p === '/briefing/generate' && method === 'POST') {
        const briefing = generateBriefing()
        return this.ok(start, { briefing, message: 'New briefing generated' })
      }

      if (p === '/briefing/json' && method === 'GET') {
        const briefing = loadLatestBriefing() ?? generateBriefing()
        return this.ok(start, briefing)
      }

      if (p === '/briefing/history' && method === 'GET') {
        return this.ok(start, { briefings: listBriefings().slice(0, 30) })
      }

      // ── Workers ───────────────────────────────────────────────────────────
      if (p === '/workers' && method === 'GET') {
        const workers = getAllWorkers().map(w => ({
          ...w,
          memory: loadWorkerMemory(w.id),
          metrics: loadWorkerMetrics(w.id),
        }))
        return this.ok(start, { workers })
      }

      const workerMatch = p.match(/^\/workers\/([^/]+)$/)
      if (workerMatch && method === 'GET') {
        const wId = workerMatch[1] as WorkerId
        const worker = getWorker(wId)
        if (!worker) return this.notFound(start, `Worker not found: ${wId}`)
        return this.ok(start, {
          worker,
          memory: loadWorkerMemory(wId),
          metrics: loadWorkerMetrics(wId),
          activeTasks: listAllTasks().filter(t => t.assignedTo === wId && t.status === 'running'),
          pendingTasks: listAllTasks().filter(t => t.assignedTo === wId && (t.status === 'pending' || t.status === 'queued')),
        })
      }

      // ── Run a worker ──────────────────────────────────────────────────────
      const workerRunMatch = p.match(/^\/workers\/([^/]+)\/run$/)
      if (workerRunMatch && method === 'POST') {
        const wId = workerRunMatch[1] as WorkerId
        const worker = getWorker(wId)
        if (!worker) return this.notFound(start, `Worker not found: ${wId}`)

        const body = req.body as { prompt?: string; taskId?: string; context?: string } | undefined
        if (!body?.prompt) return this.badRequest(start, 'prompt is required')

        const systemPrompt = getWorkerSystemPromptWithMemory(wId)

        const messages = [
          { role: 'system' as const, content: systemPrompt },
          { role: 'user' as const, content: body.prompt + (body.context ? `\n\nCONTEXT:\n${body.context}` : '') },
        ]

        const aiResult = await this.services.aiRouter.complete(messages, {
          strategy: worker.preferredStrategy,
          maxTokens: worker.maxTokens,
        })

        // Record the decision in worker memory
        recordWorkerDecision(wId, body.prompt, 'AI executed via /run')

        // If a task is associated, mark it running
        if (body.taskId) {
          startTask(body.taskId)
        }

        const result = {
          worker: worker.name,
          workerId: wId,
          taskId: body.taskId ?? null,
          response: aiResult.content,
          model: aiResult.model,
          provider: aiResult.provider,
          usage: aiResult.usage,
          durationMs: Date.now() - start,
        }

        return this.ok(start, result)
      }

      // ── Teach a worker ────────────────────────────────────────────────────
      const workerTeachMatch = p.match(/^\/workers\/([^/]+)\/teach$/)
      if (workerTeachMatch && method === 'POST') {
        const wId = workerTeachMatch[1] as WorkerId
        if (!getWorker(wId)) return this.notFound(start, `Worker not found: ${wId}`)

        const body = req.body as { lesson?: string; joshNote?: string } | undefined
        if (!body?.lesson && !body?.joshNote) return this.badRequest(start, 'lesson or joshNote required')

        if (body.lesson) addWorkerLesson(wId, body.lesson)

        if (body.joshNote) {
          const memory = loadWorkerMemory(wId)
          memory.joshNotes.push(body.joshNote)
          saveWorkerMemory(memory)
        }

        return this.ok(start, { message: `Lesson added to ${wId}`, memory: loadWorkerMemory(wId) })
      }

      // ── Queue — Overview ──────────────────────────────────────────────────
      if (p === '/queue' && method === 'GET') {
        const stats = getQueueStats()
        const ready = getReadyTasks(undefined, 10)
        const critical = listAllTasks().filter(t =>
          t.priority === 'critical' && t.status !== 'completed' && t.status !== 'cancelled'
        )
        return this.ok(start, { stats, readyTasks: ready, criticalTasks: critical })
      }

      if (p === '/queue/stats' && method === 'GET') {
        return this.ok(start, getQueueStats())
      }

      if (p === '/queue/ready' && method === 'GET') {
        const wIdParam = (req.headers as Record<string, string>)['x-worker-id'] as WorkerId | undefined
        return this.ok(start, { tasks: getReadyTasks(wIdParam, 20) })
      }

      if (p === '/queue/critical' && method === 'GET') {
        const critical = listAllTasks().filter(t =>
          t.priority === 'critical' && t.status !== 'completed' && t.status !== 'cancelled'
        )
        return this.ok(start, { tasks: critical })
      }

      // ── Queue — Tasks CRUD ────────────────────────────────────────────────
      if (p === '/queue/tasks' && method === 'GET') {
        const all = listAllTasks()
        const statusFilter = (req.headers as Record<string, string>)['x-status-filter']
        const filtered = statusFilter ? all.filter(t => t.status === statusFilter) : all
        return this.ok(start, { tasks: filtered.slice(0, 100), total: filtered.length })
      }

      if (p === '/queue/tasks' && method === 'POST') {
        const body = req.body as Partial<Parameters<typeof createTask>[0]> | undefined
        if (!body?.title) return this.badRequest(start, 'title is required')
        if (!body.category) return this.badRequest(start, 'category is required')
        if (!body.priority) return this.badRequest(start, 'priority is required')
        if (!body.assignedTo) return this.badRequest(start, 'assignedTo is required')

        const task = createTask({
          title: body.title,
          description: body.description ?? '',
          category: body.category,
          priority: body.priority,
          assignedTo: body.assignedTo,
          dependsOn: body.dependsOn ?? [],
          blocks: body.blocks ?? [],
          projectId: body.projectId ?? null,
          episodeId: body.episodeId ?? null,
          channel: body.channel ?? null,
          requiresApproval: body.requiresApproval ?? false,
          requiresReview: body.requiresReview ?? false,
          maxRetries: body.maxRetries ?? 2,
          dueDate: body.dueDate ?? null,
          estimatedMinutes: body.estimatedMinutes ?? 30,
          notes: body.notes ?? '',
          tags: body.tags ?? [],
          createdBy: body.createdBy ?? 'josh',
        })

        return this.ok(start, { task }, 201)
      }

      const taskMatch = p.match(/^\/queue\/tasks\/([^/]+)$/)
      if (taskMatch && method === 'GET') {
        const task = loadTask(taskMatch[1])
        if (!task) return this.notFound(start, `Task not found: ${taskMatch[1]}`)
        return this.ok(start, { task })
      }

      const taskApproveMatch = p.match(/^\/queue\/tasks\/([^/]+)\/approve$/)
      if (taskApproveMatch && method === 'POST') {
        const task = loadTask(taskApproveMatch[1])
        if (!task) return this.notFound(start, `Task not found: ${taskApproveMatch[1]}`)
        const updated = updateTask(task.id, { status: 'approved', requiresApproval: false })
        return this.ok(start, { task: updated, message: 'Task approved — now in ready queue' })
      }

      const taskCompleteMatch = p.match(/^\/queue\/tasks\/([^/]+)\/complete$/)
      if (taskCompleteMatch && method === 'POST') {
        const body = req.body as { result?: unknown; notes?: string } | undefined
        const updated = completeTask(taskCompleteMatch[1], body?.result ?? null, body?.notes ?? '')
        if (!updated) return this.notFound(start, `Task not found: ${taskCompleteMatch[1]}`)
        return this.ok(start, { task: updated })
      }

      const taskFailMatch = p.match(/^\/queue\/tasks\/([^/]+)\/fail$/)
      if (taskFailMatch && method === 'POST') {
        const body = req.body as { error?: string } | undefined
        const updated = failTask(taskFailMatch[1], body?.error ?? 'Unknown error')
        if (!updated) return this.notFound(start, `Task not found: ${taskFailMatch[1]}`)
        return this.ok(start, { task: updated })
      }

      // ── Blueprint execution ───────────────────────────────────────────────
      if (p === '/queue/blueprint' && method === 'POST') {
        const body = req.body as {
          blueprintId?: string
          projectId?: string
          episodeId?: string
          channel?: string
          dueDays?: number
        } | undefined

        if (!body?.blueprintId) {
          return this.ok(start, { blueprints: TASK_BLUEPRINTS.map(b => ({ id: b.id, name: b.name, description: b.description, taskCount: b.tasks.length })) })
        }

        const tasks = generateTasksFromBlueprint(body.blueprintId, {
          projectId: body.projectId,
          episodeId: body.episodeId,
          channel: body.channel,
          dueDays: body.dueDays,
          createdBy: 'josh',
        })

        if (tasks.length === 0) return this.badRequest(start, `Blueprint not found: ${body.blueprintId}`)

        return this.ok(start, {
          tasks,
          message: `${tasks.length} tasks created from blueprint "${body.blueprintId}"`,
        }, 201)
      }

      // ── Status (dashboard-compatible summary) ────────────────────────────
      if (p === '/status' && method === 'GET') {
        const stats    = getQueueStats()
        const briefing = loadLatestBriefing()
        return this.ok(start, {
          moduleId:       'executive',
          status:         'running',
          workers:        WORKERS.length,
          uptimeMs:       Date.now() - this.startTime,
          tasks:          stats.total ?? 0,
          criticalTasks:  stats.byCriticality?.critical ?? 0,
          failedTasks:    stats.byStatus?.['failed'] ?? 0,
          lastBriefing:   briefing?.generatedAt ?? null,
          timestamp:      new Date().toISOString(),
        })
      }

      // ── Health ────────────────────────────────────────────────────────────
      if (p === '/health') {
        return this.ok(start, await this.health())
      }

      return this.notFound(start, `No route: ${method} ${p}`)
    } catch (e) {
      return {
        moduleId: this.moduleId,
        status: 500,
        body: { error: e instanceof Error ? e.message : String(e), timestamp: new Date().toISOString() },
        headers: {},
        durationMs: Date.now() - start,
      }
    }
  }

  async shutdown(): Promise<void> {
    console.log('[Executive] Shutdown')
  }

  // ── Response helpers ───────────────────────────────────────────────────────

  private ok(start: number, body: unknown, status = 200): GatewayResponse {
    return { moduleId: this.moduleId, status, body, headers: {}, durationMs: Date.now() - start }
  }

  private notFound(start: number, message: string): GatewayResponse {
    return this.ok(start, { error: message }, 404)
  }

  private badRequest(start: number, message: string): GatewayResponse {
    return this.ok(start, { error: message }, 400)
  }

  private html(start: number, htmlContent: string): GatewayResponse {
    return {
      moduleId: this.moduleId,
      status: 200,
      body: htmlContent,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
      durationMs: Date.now() - start,
    }
  }
}
