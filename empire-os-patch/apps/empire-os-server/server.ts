/**
 * Empire OS Server — Entry Point
 *
 * Boots all CoreServices, registers AI adapters, initialises EmpireModules,
 * and serves HTTP on PORT (default 3001).
 *
 * URL scheme:  http://localhost:PORT/:moduleId/path
 *   empire-assistant  → all AI + agent endpoints
 *   video-pipeline    → proxy to empire_server.py (port 8002)
 *
 * Start:  npm start   (or: npx tsx server.ts)
 * Keys:   copy .env.example → .env  then add your API keys
 */

import 'dotenv/config'
import http from 'node:http'
import path from 'node:path'
import { bootstrap } from '@empire-os/core/bootstrap'
import type { ConfigurableAIRouter } from '@empire-os/core'
import { EmpireAssistantModule } from '../empire-assistant/empire-assistant.module.js'
import { AnthropicAdapter } from './adapters/anthropic.adapter.js'
import { GeminiAdapter } from './adapters/gemini.adapter.js'
import { OpenAIAdapter } from './adapters/openai.adapter.js'
import { OllamaAdapter } from './adapters/ollama.adapter.js'
import { GooseExecutor } from './goose.executor.js'
import { ModelManagerModule } from './model-manager.module.js'
import { DiscoveryModule } from './discovery.module.js'
import { HealthMonitorModule } from './health-monitor.module.js'
import { MediaEngineModule } from './media-engine.module.js'
import { KnowledgeBaseModule } from './knowledge-base.module.js'
import { EmpireDashboardModule } from './empire-dashboard.module.js'
import { EmpireStoreModule } from './store.module.js'
import { EmpireInstallerModule } from './installer.module.js'
// Phase 3 — Discovery Engine, Benchmark Engine, Self-Improvement
import { DiscoveryEngineModule } from './discovery-engine.module.js'
import { BenchmarkEngineModule } from './benchmark-engine.module.js'
import { SelfImprovementModule } from './self-improvement.module.js'
// Phase 4 — Video Factory (19 departments, 20-stage pipeline)
import { VideoFactoryModule } from './video-factory/video-factory.module.js'
// Phase 4 — Autonomous Executive (10 workers, Master Queue, Daily Briefing)
import { ExecutiveModule } from './executive/executive.module.js'
// Phase 5 — Unified Provider Registry + Health Watchdog
import { ProviderRegistryModule } from './provider.registry.js'
import { HealthWatchdogModule } from './health-watchdog.js'
// Video Bot Pipeline — render bridge (empire_server.py at port 8002)
import { VideoPipelineModule }   from '../video-pipeline/empire-module/video-pipeline.module.js'
// Operation Blacksmith — observability + automation
import { EmpireLoggerModule }    from './logger.module.js'
import { MetricsEngineModule, recordMetric } from './metrics-engine.module.js'
import { JobSchedulerModule }    from './job-scheduler.module.js'
import { ServiceRegistryModule } from './service-registry.module.js'
import { NotificationModule }    from './notification.module.js'
import type { EmpireModule } from '@empire-os/core'
import type { GatewayRequest, HttpMethod } from '@empire-os/core'

const PORT      = Number(process.env.PORT ?? 3001)
const HOST      = process.env.HOST ?? 'localhost'
const BASE_URL  = `http://${HOST}:${PORT}`
const DATA_DIR  = process.env.DATA_DIR ?? path.resolve('.empire-data')
const API_KEY   = process.env.EMPIRE_API_KEY  // undefined = auth disabled (dev mode)

// Paths that don't require authentication
const PUBLIC_PATHS = new Set(['/', '/health'])

// ── helpers ────────────────────────────────────────────────────────────────

function log(msg: string): void {
  process.stdout.write(`[Empire OS] ${msg}\n`)
}

function jsonResponse(res: http.ServerResponse, status: number, body: unknown, extra?: Record<string, string>): void {
  const headers = { 'Content-Type': 'application/json', ...extra }
  res.writeHead(status, headers)
  // If the module returned a raw string (e.g. text/html), send it as-is.
  // JSON.stringify on an HTML string escapes all " to \" and breaks the page.
  if (typeof body === 'string') {
    res.end(body)
  } else {
    res.end(JSON.stringify(body))
  }
}

async function readBody(req: http.IncomingMessage): Promise<unknown> {
  if (req.method === 'GET' || req.method === 'HEAD') return undefined
  const chunks: Buffer[] = []
  for await (const chunk of req) chunks.push(chunk as Buffer)
  const raw = Buffer.concat(chunks).toString()
  if (!raw) return undefined
  try { return JSON.parse(raw) } catch { return raw }
}

// ── bootstrap ──────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  log('Booting...')

  log(`Data directory: ${DATA_DIR}`)
  if (API_KEY) {
    log('Auth: ENABLED — X-Empire-Api-Key required on all non-public endpoints')
  } else {
    log('Auth: DISABLED — set EMPIRE_API_KEY in .env to enable')
  }

  // 1. Core services — file-backed persistence (survives restarts)
  const services = await bootstrap({ dataDir: DATA_DIR })
  log('Core services ready (file-backed persistence active).')

  // 2. Register AI adapters
  //    Provider priority (cost strategy = default):
  //      Ollama  → local, free, handles routine/copy/summary/classification
  //      Claude  → code, architecture, complex reasoning
  //      Gemini  → research, long-context, planning
  //      OpenAI  → GPT-specific features
  //
  //    Routing: 'cost' strategy wins Ollama (costPerMToken=0).
  //             'quality' strategy wins Claude/Gemini (larger context window).
  //             'local-only' strategy forces Ollama exclusively.

  const aiRouter = services.aiRouter as ConfigurableAIRouter

  // ── 1. Ollama (local — no key needed) ─────────────────────────────────────
  const OLLAMA_BASE = process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434'
  try {
    const ollama = await OllamaAdapter.create(OLLAMA_BASE)
    if (ollama.models.length === 0) {
      log('⚠  Ollama is running but has no models installed. Run: ollama pull llama3')
    } else {
      aiRouter.registerAdapter(ollama)
      // Set cost as default so Ollama wins routine tasks automatically
      await aiRouter.setDefaultStrategy('cost')
      log(`Ollama adapter registered — ${ollama.models.length} model(s): ${ollama.models.map(m => m.id).join(', ')}`)
      log('   Default strategy: cost (Ollama handles routine tasks; cloud AI on fallback)')
    }
  } catch (err) {
    log(`⚠  Ollama not reachable at ${OLLAMA_BASE} — ${err instanceof Error ? err.message : String(err)}`)
    log('   Start Ollama: run  ollama serve  in a terminal, then restart Empire OS')
  }

  // ── 2. Anthropic Claude (complex code, architecture, reasoning) ────────────
  if (process.env.ANTHROPIC_API_KEY) {
    aiRouter.registerAdapter(new AnthropicAdapter(process.env.ANTHROPIC_API_KEY))
    log('Anthropic adapter registered (claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5-20251001)')
    log('   Role: code, architecture, complex reasoning')
  } else {
    log('⚠  ANTHROPIC_API_KEY not set — Claude models unavailable')
  }

  // ── 3. Google Gemini (research, long-context, planning) ───────────────────
  if (process.env.GOOGLE_API_KEY) {
    aiRouter.registerAdapter(new GeminiAdapter(process.env.GOOGLE_API_KEY))
    log('Gemini adapter registered (gemini-1.5-pro, gemini-1.5-flash)')
    log('   Role: research, long-context planning, scripts')
  } else {
    log('   GOOGLE_API_KEY not set — Gemini models skipped (optional)')
  }

  // ── 4. OpenAI (GPT-specific features) ────────────────────────────────────
  if (process.env.OPENAI_API_KEY) {
    aiRouter.registerAdapter(new OpenAIAdapter(process.env.OPENAI_API_KEY))
    log('OpenAI adapter registered (gpt-4o, gpt-4o-mini)')
    log('   Role: GPT-specific tasks, copy, function-calling features')
  } else {
    log('   OPENAI_API_KEY not set — OpenAI models skipped (optional)')
  }

  // ── 5. Goose (local dev agent — file ops, shell, coding execution) ────────
  const goose = await GooseExecutor.create()
  if (goose.available) {
    const gooseVersion = await goose.version()
    log(`Goose agent detected (${gooseVersion ?? 'version unknown'})`)
    log('   Role: local coding tasks, file operations, terminal commands')
    log(`   Send tasks to: POST ${BASE_URL}/goose/run`)
  } else {
    log('   Goose not found on PATH — local dev agent disabled')
    log('   Install: https://github.com/block/goose')
  }

  const hasAnyAI = process.env.ANTHROPIC_API_KEY || process.env.GOOGLE_API_KEY || process.env.OPENAI_API_KEY
  if (!hasAnyAI) {
    log('⚠  No cloud AI keys configured. Ollama will handle all requests (or add keys to .env).')
  }

  // 3. Instantiate and init modules
  const modules = new Map<string, EmpireModule>()

  const ea = new EmpireAssistantModule()
  await ea.init(services, {
    port: PORT,
    baseUrl: `${BASE_URL}/empire-assistant`,
  })
  modules.set(ea.moduleId, ea)
  log(`Module ready: ${ea.moduleId}`)

  const modelManager = new ModelManagerModule()
  await modelManager.init(services, {})
  modules.set(modelManager.moduleId, modelManager)
  log(`Module ready: ${modelManager.moduleId} — http://${HOST}:${PORT}/model-manager/`)

  const discovery = new DiscoveryModule()
  await discovery.init(services, {})
  modules.set(discovery.moduleId, discovery)
  log(`Module ready: ${discovery.moduleId} — http://${HOST}:${PORT}/discovery/`)

  const healthMonitor = new HealthMonitorModule()
  await healthMonitor.init(services, {})
  modules.set(healthMonitor.moduleId, healthMonitor)
  log(`Module ready: ${healthMonitor.moduleId} — http://${HOST}:${PORT}/health-monitor/`)

  const mediaEngine = new MediaEngineModule()
  await mediaEngine.init(services, {})
  modules.set(mediaEngine.moduleId, mediaEngine)
  log(`Module ready: ${mediaEngine.moduleId} — http://${HOST}:${PORT}/media-engine/`)

  const knowledgeBase = new KnowledgeBaseModule()
  await knowledgeBase.init(services, {})
  modules.set(knowledgeBase.moduleId, knowledgeBase)
  log(`Module ready: ${knowledgeBase.moduleId} — http://${HOST}:${PORT}/knowledge-base/`)

  const store = new EmpireStoreModule()
  await store.init(services, {})
  modules.set(store.moduleId, store)
  log(`Module ready: ${store.moduleId} — http://${HOST}:${PORT}/store/`)

  const installer = new EmpireInstallerModule()
  await installer.init(services, {})
  modules.set(installer.moduleId, installer)
  log(`Module ready: ${installer.moduleId} — http://${HOST}:${PORT}/installer/`)

  const dashboard = new EmpireDashboardModule()
  await dashboard.init(services, {})
  modules.set(dashboard.moduleId, dashboard)
  log(`Module ready: ${dashboard.moduleId} — http://${HOST}:${PORT}/empire-dashboard/`)

  // Phase 3 — Discovery Engine
  const discoveryEngine = new DiscoveryEngineModule()
  await discoveryEngine.init(services, {})
  modules.set(discoveryEngine.moduleId, discoveryEngine)
  log(`Module ready: ${discoveryEngine.moduleId} — http://${HOST}:${PORT}/discovery-engine/`)

  // Phase 3 — Benchmark Engine
  const benchmarkEngine = new BenchmarkEngineModule()
  await benchmarkEngine.init(services, {})
  modules.set(benchmarkEngine.moduleId, benchmarkEngine)
  log(`Module ready: ${benchmarkEngine.moduleId} — http://${HOST}:${PORT}/benchmark-engine/`)

  // Phase 3 — Self Improvement Engine
  const selfImprovement = new SelfImprovementModule()
  await selfImprovement.init(services, {})
  modules.set(selfImprovement.moduleId, selfImprovement)
  log(`Module ready: ${selfImprovement.moduleId} — http://${HOST}:${PORT}/self-improvement/`)

  // Phase 4 — Video Factory
  const videoFactory = new VideoFactoryModule()
  await videoFactory.init(services, {})
  modules.set(videoFactory.moduleId, videoFactory)
  log(`Module ready: ${videoFactory.moduleId} — http://${HOST}:${PORT}/video-factory/`)

  // Phase 4 — Autonomous Executive
  const executive = new ExecutiveModule()
  await executive.init(services, {})
  modules.set(executive.moduleId, executive)
  log(`Module ready: ${executive.moduleId} — http://${HOST}:${PORT}/executive/   ← DAILY BRIEFING`)

  // Phase 5 — Unified Provider Registry (auto-discovers adapters via env vars)
  const providerRegistry = new ProviderRegistryModule()
  await providerRegistry.init(services, {})
  // Ollama auto-discovered by registry during init(); just wire Goose here
  providerRegistry.registerAdapters({
    goose: goose.available ? goose : undefined,
  })
  modules.set(providerRegistry.moduleId, providerRegistry)
  log(`Module ready: ${providerRegistry.moduleId} — http://${HOST}:${PORT}/provider-registry/`)

  // Phase 5 — Health Watchdog (background 60s monitor)
  const watchdog = new HealthWatchdogModule()
  await watchdog.init(services, {})
  modules.set(watchdog.moduleId, watchdog)
  log(`Module ready: ${watchdog.moduleId} — http://${HOST}:${PORT}/watchdog/status`)

  // Operation Blacksmith — Centralized Logger
  const empireLogger = new EmpireLoggerModule()
  await empireLogger.init(services, {})
  modules.set(empireLogger.moduleId, empireLogger)
  log(`Module ready: ${empireLogger.moduleId} — http://${HOST}:${PORT}/logger/`)

  // Operation Blacksmith — Live Metrics Engine
  const metricsEngine = new MetricsEngineModule()
  await metricsEngine.init(services, {})
  modules.set(metricsEngine.moduleId, metricsEngine)
  log(`Module ready: ${metricsEngine.moduleId} — http://${HOST}:${PORT}/metrics-engine/`)

  // Operation Blacksmith — Background Job Scheduler
  const jobScheduler = new JobSchedulerModule()
  await jobScheduler.init(services, {})
  modules.set(jobScheduler.moduleId, jobScheduler)
  log(`Module ready: ${jobScheduler.moduleId} — http://${HOST}:${PORT}/job-scheduler/`)

  // Operation Blacksmith — Service Registry + Dependency Graph
  const serviceRegistry = new ServiceRegistryModule()
  await serviceRegistry.init(services, {})
  modules.set(serviceRegistry.moduleId, serviceRegistry)
  log(`Module ready: ${serviceRegistry.moduleId} — http://${HOST}:${PORT}/service-registry/`)

  // Operation Blacksmith — Notification System
  const notification = new NotificationModule()
  await notification.init(services, {})
  modules.set(notification.moduleId, notification)
  log(`Module ready: ${notification.moduleId} — http://${HOST}:${PORT}/notification/`)

  // Video Bot Pipeline — proxy to empire_server.py at port 8002
  const videoPipeline = new VideoPipelineModule()
  await videoPipeline.init(services, {})
  modules.set(videoPipeline.moduleId, videoPipeline)
  log(`Module ready: ${videoPipeline.moduleId} — http://${HOST}:${PORT}/video-pipeline/  → :8002`)
  log(`   (empire_server.py must be running: python empire_server.py)`)

  // 4. HTTP server
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', `http://${HOST}:${PORT}`)
    const correlationId = (req.headers['x-correlation-id'] as string) ?? crypto.randomUUID()
    const reqStart = Date.now()

    // ── Request logger ──────────────────────────────────────────────────────────
    // Intercept writeHead to capture status code for the finish log
    let capturedStatus = 200
    const origWriteHead = res.writeHead.bind(res) as typeof res.writeHead
    res.writeHead = ((...args: Parameters<typeof res.writeHead>) => {
      capturedStatus = typeof args[0] === 'number' ? args[0] : 200
      return origWriteHead(...args as Parameters<typeof res.writeHead>)
    }) as typeof res.writeHead

    res.on('finish', () => {
      const ms    = Date.now() - reqStart
      const icon  = capturedStatus >= 500 ? '💥' : capturedStatus >= 400 ? '⚠' : '✓'
      const cid   = correlationId.slice(0, 8)
      log(`${icon} ${capturedStatus} ${req.method ?? 'GET'} ${url.pathname} ${ms}ms [${cid}]`)
    })

    try {
      // CORS — allow CrossPost Enterprise (port 3000) to call this server directly
      res.setHeader('Access-Control-Allow-Origin', '*')
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Empire-Api-Key, X-Correlation-Id')
      if (req.method === 'OPTIONS') {
        res.writeHead(204)
        res.end()
        return
      }

      // Auth check — skip for public paths
      if (API_KEY && !PUBLIC_PATHS.has(url.pathname)) {
        const provided = req.headers['x-empire-api-key']
        if (provided !== API_KEY) {
          jsonResponse(res, 401, {
            error: 'Unauthorized',
            hint: 'Include X-Empire-Api-Key header with your EMPIRE_API_KEY value',
          })
          return
        }
      }

      // Server root — redirect to the premium dashboard
      if (url.pathname === '/' || url.pathname === '') {
        res.writeHead(302, { Location: '/empire-dashboard/' })
        res.end()
        return
      }

      // Server-level health
      if (url.pathname === '/health') {
        const health: Record<string, unknown> = { status: 'online', modules: {} }
        for (const [id, mod] of modules) {
          const h = await mod.health().catch(e => ({ status: 'unhealthy', error: String(e) }))
          ;(health.modules as Record<string, unknown>)[id] = h
        }
        jsonResponse(res, 200, health)
        return
      }

      // Provider inventory — GET /providers
      if (url.pathname === '/providers' && req.method === 'GET') {
        const allModels = await services.aiRouter.models()
        jsonResponse(res, 200, {
          providers: allModels.reduce((acc: Record<string, unknown[]>, m) => {
            if (!acc[m.provider]) acc[m.provider] = []
            acc[m.provider].push({ id: m.id, capabilities: m.capabilities, contextWindow: m.contextWindow, costPerMToken: m.costPerMToken })
            return acc
          }, {}),
          goose: { available: goose.available, role: 'local dev agent — file ops, shell, coding' },
          defaultStrategy: 'cost',
          routingRules: {
            cost:       'Ollama wins (costPerMToken=0) — handles routine/copy/summary',
            quality:    'Claude or Gemini wins (largest context window)',
            'local-only': 'Ollama exclusively, no cloud fallback',
            speed:      'Cheapest available model',
          },
        })
        return
      }

      // Goose endpoint — POST /goose/run
      if (url.pathname === '/goose/run' && req.method === 'POST') {
        if (!goose.available) {
          jsonResponse(res, 503, { error: 'Goose not installed', hint: 'Install from https://github.com/block/goose' })
          return
        }
        const reqBody = await readBody(req) as { task?: string } | undefined
        const task = reqBody?.task
        if (!task) {
          jsonResponse(res, 400, { error: 'Missing required field: task' })
          return
        }
        const result = await goose.run(task)
        jsonResponse(res, 200, result)
        return
      }

      // Video pipeline shortcut — /api/* → video-pipeline module
      // Dashboard calls /api/episodes, /api/render etc. without module prefix
      if (url.pathname.startsWith('/api/')) {
        const vpMod = modules.get('video-pipeline')
        if (!vpMod) {
          jsonResponse(res, 503, { error: 'video-pipeline module not loaded' })
          return
        }
        const vpBody = (req.method !== 'GET' && req.method !== 'DELETE') ? await readBody(req) : undefined
        const vpReq = {
          path: url.pathname + (url.search ?? ''),
          method: req.method as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
          body: vpBody,
          headers: req.headers as Record<string, string>,
          correlationId,
          timeoutMs: 120_000,
        }
        const vpResult = await vpMod.handleRequest(vpReq)
        jsonResponse(res, vpResult.status, vpResult.body, vpResult.headers)
        return
      }

      // Module dispatch — /:moduleId[/path...]
      const segments = url.pathname.replace(/^\//, '').split('/')
      const moduleId = segments[0]
      const mod = modules.get(moduleId)
      if (!mod) {
        jsonResponse(res, 404, {
          error: `Unknown module: ${moduleId}`,
          hint: 'Check /health for available modules',
          availableModules: [...modules.keys()],
        })
        return
      }
      const modBody = (req.method !== 'GET' && req.method !== 'DELETE') ? await readBody(req) : undefined
      const modReq = {
        path: '/' + segments.slice(1).join('/') + (url.search ?? ''),
        method: req.method as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
        body: modBody,
        headers: req.headers as Record<string, string>,
        correlationId,
        timeoutMs: 120_000,
      }
      const modResult = await mod.handleRequest(modReq)
      jsonResponse(res, modResult.status, modResult.body, modResult.headers)

    } catch (err) {
      log(`💥 Unhandled error: ${err}`)
      jsonResponse(res, 500, { error: 'Internal server error', detail: String(err) })
    }
  })

  server.listen(PORT, HOST, () => {
    log(`\n✅ Empire OS server listening — http://${HOST}:${PORT}/`)
    log(`   Dashboard:   http://${HOST}:${PORT}/empire-dashboard/`)
    log(`   Health:      http://${HOST}:${PORT}/health`)
    log(`   Video API:   http://${HOST}:${PORT}/api/episodes`)
  })
}

main().catch(err => {
  console.error('💥 Fatal Empire OS startup error:', err)
  process.exit(1)
})
