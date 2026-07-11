/**
 * VideoFactoryModule — Empire OS Module
 *
 * The full 19-department AI film production engine, registered as an Empire OS module.
 * Plugs into the AI Router, Knowledge Base, and all provider adapters.
 *
 * Routes:
 *   GET  /video-factory/                    → dashboard HTML
 *   GET  /video-factory/status              → status JSON
 *   GET  /video-factory/providers           → provider availability
 *   GET  /video-factory/departments         → all 19 departments
 *   GET  /video-factory/projects            → list all projects
 *   POST /video-factory/projects            → create new project
 *   GET  /video-factory/projects/:id        → get project details
 *   POST /video-factory/projects/:id/advance → advance to next stage
 *   GET  /video-factory/memory/characters   → list all characters
 *   GET  /video-factory/memory/environments → list all environments
 *   POST /video-factory/memory/characters   → save character
 *   POST /video-factory/memory/environments → save environment
 *   GET  /video-factory/pipeline/stages     → pipeline stage definitions
 *   POST /video-factory/ai/run              → run a department AI task
 *   GET  /video-factory/health              → health check
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { DEPARTMENTS, getDepartment, getAllDepartmentIds, PRODUCTION_MODE_DEFAULTS } from './video-factory.departments.js'
import {
  STAGE_ORDER, STAGE_DEFINITIONS, getStagesSummary,
  createProject, loadProject, listProjects, updateStage,
  startStage, completeStage, failStage, getNextStages, getProjectProgress
} from './video-factory.pipeline.js'
import {
  CharacterEngine, EnvironmentEngine, TimelineEngine, getMemoryStats
} from './video-factory.memory.js'
import {
  getProviderStatus, routeImageGeneration, routeVideoGeneration, routeTTS,
  type ProviderRouterConfig
} from './video-factory.providers.js'
import type { ProductionMode } from './video-factory.departments.js'

// ── Module ─────────────────────────────────────────────────────────────────────

export class VideoFactoryModule implements EmpireModule {
  readonly moduleId = 'video-factory'
  private services!: CoreServices
  private startTime = Date.now()

  async init(services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    this.services = services
    this.startTime = Date.now()
    console.log('[VideoFactory] Initialized — 19 departments, 20-stage pipeline ready')
  }

  async health(): Promise<ModuleHealth> {
    const memStats = getMemoryStats()
    const providerStatus = getProviderStatus()
    const availableProviders = Object.values(providerStatus).filter(p => p.available).length
    const projects = listProjects()

    return {
      status: 'healthy',
      details: {
        departments: DEPARTMENTS.length,
        pipelineStages: STAGE_ORDER.length,
        projects: projects.length,
        characters: memStats.characters.total,
        environments: memStats.environments.total,
        timelines: memStats.timelines,
        availableProviders,
        uptimeMs: Date.now() - this.startTime,
      },
    }
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start = Date.now()
    const path = req.path
    const method = req.method

    try {
      // ── Dashboard ─────────────────────────────────────────────────────────
      if (path === '/' && method === 'GET') {
        return this.htmlResponse(start, this.buildDashboardHTML())
      }

      // ── Status ────────────────────────────────────────────────────────────
      if (path === '/status' && method === 'GET') {
        const projects = listProjects()
        const memStats = getMemoryStats()
        const providers = getProviderStatus()
        return this.ok(start, {
          module: 'video-factory',
          departments: DEPARTMENTS.length,
          pipelineStages: STAGE_ORDER.length,
          projects: {
            total: projects.length,
            byStatus: projects.reduce((acc: Record<string, number>, p) => {
              acc[p.status] = (acc[p.status] ?? 0) + 1
              return acc
            }, {}),
          },
          memory: memStats,
          providers: Object.fromEntries(
            Object.entries(providers).map(([k, v]) => [k, { available: v.available, name: v.name }])
          ),
        })
      }

      // ── Providers ─────────────────────────────────────────────────────────
      if (path === '/providers' && method === 'GET') {
        return this.ok(start, getProviderStatus())
      }

      // ── Departments ───────────────────────────────────────────────────────
      if (path === '/departments' && method === 'GET') {
        return this.ok(start, { departments: DEPARTMENTS })
      }

      if (path.startsWith('/departments/') && method === 'GET') {
        const deptId = path.split('/')[2]
        const dept = getDepartment(deptId)
        if (!dept) return this.notFound(start, `Department not found: ${deptId}`)
        return this.ok(start, dept)
      }

      // ── Pipeline Stages ───────────────────────────────────────────────────
      if (path === '/pipeline/stages' && method === 'GET') {
        return this.ok(start, { stages: getStagesSummary(), order: STAGE_ORDER })
      }

      // ── Projects — List / Create ──────────────────────────────────────────
      if (path === '/projects' && method === 'GET') {
        return this.ok(start, { projects: listProjects() })
      }

      if (path === '/projects' && method === 'POST') {
        const body = req.body as {
          title?: string
          channel?: string
          mode?: ProductionMode
          episodeNumber?: string
          season?: number
          logline?: string
          targetPublishDate?: string
        } | undefined

        if (!body?.title) return this.badRequest(start, 'title is required')
        if (!body.channel) return this.badRequest(start, 'channel is required')
        if (!body.mode) return this.badRequest(start, 'mode is required (see /video-factory/departments for modes)')
        if (!body.episodeNumber) return this.badRequest(start, 'episodeNumber is required')

        const project = createProject({
          title: body.title,
          channel: body.channel,
          mode: body.mode,
          episodeNumber: body.episodeNumber,
          season: body.season ?? 1,
          logline: body.logline,
          targetPublishDate: body.targetPublishDate,
        })

        return this.ok(start, { project, message: `Project "${project.title}" created. ID: ${project.id}` }, 201)
      }

      // ── Project — Get / Advance ───────────────────────────────────────────
      const projectMatch = path.match(/^\/projects\/([^/]+)$/)
      if (projectMatch && method === 'GET') {
        const project = loadProject(projectMatch[1])
        if (!project) return this.notFound(start, `Project not found: ${projectMatch[1]}`)
        const progress = getProjectProgress(project)
        const nextStages = getNextStages(project)
        return this.ok(start, { project, progress, nextStages })
      }

      const advanceMatch = path.match(/^\/projects\/([^/]+)\/advance$/)
      if (advanceMatch && method === 'POST') {
        const project = loadProject(advanceMatch[1])
        if (!project) return this.notFound(start, `Project not found: ${advanceMatch[1]}`)

        const nextStages = getNextStages(project)
        if (nextStages.length === 0) {
          const progress = getProjectProgress(project)
          return this.ok(start, {
            message: progress.percentComplete === 100 ? 'Project is complete!' : 'No stages ready to advance. Check for blocked dependencies.',
            progress,
          })
        }

        // Advance the first available stage
        const stage = nextStages[0]
        const updated = startStage(project.id, stage)
        return this.ok(start, {
          message: `Stage "${stage}" started`,
          stage,
          project: updated,
          nextStages: nextStages.slice(1),
        })
      }

      // ── AI — Run a department task ────────────────────────────────────────
      if (path === '/ai/run' && method === 'POST') {
        const body = req.body as {
          departmentId?: string
          projectId?: string
          stage?: string
          input?: string
          context?: Record<string, unknown>
        } | undefined

        if (!body?.departmentId) return this.badRequest(start, 'departmentId is required')
        if (!body.input) return this.badRequest(start, 'input is required')

        const dept = getDepartment(body.departmentId)
        if (!dept) return this.badRequest(start, `Unknown department: ${body.departmentId}`)

        // Route through Empire OS AI Router
        const messages = [
          { role: 'system' as const, content: dept.systemPrompt },
          { role: 'user'   as const, content: body.input },
        ]

        const aiResult = await this.services.aiRouter.complete(messages, {
          strategy: dept.preferredStrategy,
          maxTokens: dept.maxTokens,
        })

        const result = {
          department: dept.name,
          stage: body.stage ?? 'manual',
          projectId: body.projectId ?? null,
          output: aiResult.content,
          model: aiResult.model,
          provider: aiResult.provider,
          usage: aiResult.usage,
          durationMs: Date.now() - start,
        }

        // If a project + stage is provided, save the result
        if (body.projectId && body.stage) {
          const stageId = body.stage as Parameters<typeof completeStage>[1]
          completeStage(body.projectId, stageId, result.output)
        }

        return this.ok(start, result)
      }

      // ── Image Generation ──────────────────────────────────────────────────
      if (path === '/generate/image' && method === 'POST') {
        const body = req.body as {
          prompt?: string
          negativePrompt?: string
          width?: number
          height?: number
          style?: 'photorealistic' | 'painterly' | 'cinematic' | 'illustrated' | 'watercolor'
          provider?: ProviderRouterConfig['imageProvider']
        } | undefined

        if (!body?.prompt) return this.badRequest(start, 'prompt is required')

        const result = await routeImageGeneration(
          {
            prompt: body.prompt,
            negativePrompt: body.negativePrompt,
            width: body.width ?? 1792,
            height: body.height ?? 1024,
            style: body.style ?? 'cinematic',
          },
          { imageProvider: body.provider ?? 'auto', videoProvider: 'auto', audioProvider: 'auto' }
        )

        return this.ok(start, result)
      }

      // ── Video Generation ──────────────────────────────────────────────────
      if (path === '/generate/video' && method === 'POST') {
        const body = req.body as {
          prompt?: string
          imageUrl?: string
          duration?: number
          width?: number
          height?: number
          provider?: ProviderRouterConfig['videoProvider']
        } | undefined

        if (!body?.prompt) return this.badRequest(start, 'prompt is required')

        const result = await routeVideoGeneration(
          {
            prompt: body.prompt,
            imageUrl: body.imageUrl,
            duration: body.duration ?? 5,
            width: body.width ?? 1920,
            height: body.height ?? 1080,
          },
          { imageProvider: 'auto', videoProvider: body.provider ?? 'auto', audioProvider: 'auto' }
        )

        return this.ok(start, result)
      }

      // ── TTS Generation ────────────────────────────────────────────────────
      if (path === '/generate/voice' && method === 'POST') {
        const body = req.body as {
          text?: string
          voiceId?: string
          channel?: string
          stability?: number
          similarityBoost?: number
        } | undefined

        if (!body?.text) return this.badRequest(start, 'text is required')

        const voiceId = body.voiceId
          ?? ElevenLabsVoiceIds[body.channel ?? 'gods-glory']
          ?? ElevenLabsVoiceIds['gods-glory']

        const result = await routeTTS({
          text: body.text,
          voiceId,
          stability: body.stability,
          similarityBoost: body.similarityBoost,
        })

        return this.ok(start, result)
      }

      // ── Memory — Characters ───────────────────────────────────────────────
      if (path === '/memory/characters' && method === 'GET') {
        return this.ok(start, { characters: CharacterEngine.listAll(), stats: CharacterEngine.getStats() })
      }

      if (path === '/memory/characters' && method === 'POST') {
        const body = req.body as Parameters<typeof CharacterEngine.create>[0] | undefined
        if (!body?.name) return this.badRequest(start, 'name is required')
        const char = CharacterEngine.create(body)
        return this.ok(start, char, 201)
      }

      const charMatch = path.match(/^\/memory\/characters\/([^/]+)$/)
      if (charMatch && method === 'GET') {
        const char = CharacterEngine.load(charMatch[1])
          ?? CharacterEngine.findByName(charMatch[1])
        if (!char) return this.notFound(start, `Character not found: ${charMatch[1]}`)
        return this.ok(start, char)
      }

      // ── Memory — Environments ─────────────────────────────────────────────
      if (path === '/memory/environments' && method === 'GET') {
        return this.ok(start, { environments: EnvironmentEngine.listAll(), stats: EnvironmentEngine.getStats() })
      }

      if (path === '/memory/environments' && method === 'POST') {
        const body = req.body as Parameters<typeof EnvironmentEngine.create>[0] | undefined
        if (!body?.name) return this.badRequest(start, 'name is required')
        const env = EnvironmentEngine.create(body)
        return this.ok(start, env, 201)
      }

      const envMatch = path.match(/^\/memory\/environments\/([^/]+)$/)
      if (envMatch && method === 'GET') {
        const env = EnvironmentEngine.load(envMatch[1])
          ?? EnvironmentEngine.findByName(envMatch[1])
        if (!env) return this.notFound(start, `Environment not found: ${envMatch[1]}`)
        return this.ok(start, env)
      }

      // ── Memory — Stats ────────────────────────────────────────────────────
      if (path === '/memory' && method === 'GET') {
        return this.ok(start, getMemoryStats())
      }

      // ── Health ────────────────────────────────────────────────────────────
      if (path === '/health') {
        return this.ok(start, await this.health())
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (e) {
      return {
        moduleId: this.moduleId,
        status: 500,
        body: { error: e instanceof Error ? e.message : String(e) },
        headers: {},
        durationMs: Date.now() - start,
      }
    }
  }

  async shutdown(): Promise<void> {
    console.log('[VideoFactory] Shutdown')
  }

  // ── Response helpers ───────────────────────────────────────────────────────

  private ok(start: number, body: unknown, status = 200): GatewayResponse {
    return { moduleId: this.moduleId, status, body, headers: {}, durationMs: Date.now() - start }
  }

  private notFound(start: number, message: string): GatewayResponse {
    return this.ok(start, { error: message, available: getAllDepartmentIds() }, 404)
  }

  private badRequest(start: number, message: string): GatewayResponse {
    return this.ok(start, { error: message }, 400)
  }

  private htmlResponse(start: number, html: string): GatewayResponse {
    return {
      moduleId: this.moduleId,
      status: 200,
      body: html,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
      durationMs: Date.now() - start,
    }
  }

  // ── Dashboard HTML ─────────────────────────────────────────────────────────

  private buildDashboardHTML(): string {
    const projects = listProjects()
    const memStats = getMemoryStats()
    const providers = getProviderStatus()
    const availableProviders = Object.values(providers).filter(p => p.available)
    const missingProviders  = Object.values(providers).filter(p => !p.available)

    const projectRows = projects.slice(0, 10).map(p => {
      const progress = getProjectProgress(p)
      return `
        <tr>
          <td>${p.title}</td>
          <td>${p.channel}</td>
          <td>${p.mode}</td>
          <td>${p.status}</td>
          <td>
            <div class="progress-bar" style="width:100%;background:#1a1a2e;border-radius:4px;height:12px;">
              <div style="width:${progress.percentComplete}%;background:#7c3aed;height:12px;border-radius:4px;"></div>
            </div>
            <small>${progress.percentComplete}% (${progress.completed}/${progress.total} stages)</small>
          </td>
          <td><small>${p.updatedAt.slice(0, 10)}</small></td>
        </tr>`
    }).join('')

    const deptCards = DEPARTMENTS.map(d => `
      <div class="dept-card">
        <div class="dept-name">${d.name}</div>
        <div class="dept-role">${d.role}</div>
        <div class="dept-stages">${d.ownedStages.join(', ')}</div>
      </div>`).join('')

    const providerBadges = availableProviders.map(p =>
      `<span class="badge badge-green">✓ ${p.name}</span>`).join(' ')
    const missingBadges = missingProviders.map(p =>
      `<span class="badge badge-red">✗ ${p.name}</span>`).join(' ')

    return `<!DOCTYPE html>
<html>
<head>
<title>Video Factory — Viral Engine</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0a0a1a; color: #e0e0ff; padding: 24px; }
  h1 { font-size: 28px; color: #7c3aed; margin-bottom: 4px; }
  h2 { font-size: 18px; color: #a78bfa; margin: 24px 0 12px; }
  .subtitle { color: #6b7280; margin-bottom: 24px; }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  .stat { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 16px 24px; min-width: 120px; }
  .stat-num { font-size: 32px; font-weight: 700; color: #7c3aed; }
  .stat-label { font-size: 12px; color: #6b7280; }
  table { width: 100%; border-collapse: collapse; background: #111827; border-radius: 8px; overflow: hidden; margin-bottom: 24px; }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #1f2937; font-size: 13px; }
  th { background: #1a1a2e; color: #a78bfa; font-weight: 600; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin: 2px; }
  .badge-green { background: #052e16; color: #4ade80; border: 1px solid #166534; }
  .badge-red   { background: #2d0a0a; color: #f87171; border: 1px solid #7f1d1d; }
  .dept-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .dept-card { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 12px; }
  .dept-name { font-size: 13px; font-weight: 600; color: #c4b5fd; }
  .dept-role { font-size: 11px; color: #6b7280; margin: 4px 0; }
  .dept-stages { font-size: 10px; color: #4b5563; font-family: monospace; }
  .api-box { background: #111827; border: 1px solid #7c3aed; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 12px; line-height: 2; }
</style>
</head>
<body>
<h1>🎬 Video Factory</h1>
<p class="subtitle">19-Department AI Film Production Engine — Viral Engine</p>

<div class="stats">
  <div class="stat"><div class="stat-num">${projects.length}</div><div class="stat-label">Projects</div></div>
  <div class="stat"><div class="stat-num">${DEPARTMENTS.length}</div><div class="stat-label">Departments</div></div>
  <div class="stat"><div class="stat-num">${STAGE_ORDER.length}</div><div class="stat-label">Pipeline Stages</div></div>
  <div class="stat"><div class="stat-num">${memStats.characters.total}</div><div class="stat-label">Characters</div></div>
  <div class="stat"><div class="stat-num">${memStats.environments.total}</div><div class="stat-label">Environments</div></div>
  <div class="stat"><div class="stat-num">${availableProviders.length}/${Object.keys(providers).length}</div><div class="stat-label">Providers Live</div></div>
</div>

<h2>Provider Status</h2>
<div style="margin-bottom:24px;">${providerBadges} ${missingBadges}</div>

<h2>Active Projects</h2>
${projects.length === 0
  ? '<p style="color:#4b5563;font-size:13px;">No projects yet. POST /video-factory/projects to create one.</p>'
  : `<table><tr><th>Title</th><th>Channel</th><th>Mode</th><th>Status</th><th>Progress</th><th>Updated</th></tr>${projectRows}</table>`
}

<h2>19 Departments</h2>
<div class="dept-cards">${deptCards}</div>

<h2>API Reference</h2>
<div class="api-box">
  POST /video-factory/projects           → Create project<br>
  GET  /video-factory/projects           → List all projects<br>
  GET  /video-factory/projects/:id       → Project details + progress<br>
  POST /video-factory/projects/:id/advance → Advance pipeline<br>
  POST /video-factory/ai/run             → Run AI department task<br>
  POST /video-factory/generate/image     → Generate image<br>
  POST /video-factory/generate/video     → Generate video clip<br>
  POST /video-factory/generate/voice     → Generate TTS audio<br>
  GET  /video-factory/memory/characters  → Character memory<br>
  GET  /video-factory/memory/environments → Environment memory<br>
  GET  /video-factory/departments        → All 19 departments<br>
  GET  /video-factory/pipeline/stages    → 20-stage pipeline<br>
</div>
</body>
</html>`
  }
}

// ── ElevenLabs voice ID lookup ─────────────────────────────────────────────────
const ElevenLabsVoiceIds: Record<string, string> = {
  'gods-glory':       process.env.ELEVENLABS_VOICE_GG ?? 'pNInz6obpgDQGcFmaJgB',
  'machine-learning': process.env.ELEVENLABS_VOICE_ML ?? 'ErXwobaYiN019PkySvjV',
  'little-olympus':   process.env.ELEVENLABS_VOICE_LO ?? 'EXAVITQu4vr4xnSDxMaL',
}
