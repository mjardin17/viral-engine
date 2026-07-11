/**
 * ServiceRegistry — Automatic Service Discovery & Dependency Graph
 *
 * Maintains a live registry of all Empire OS modules and external services.
 * Computes dependency ordering for safe startup/shutdown sequences.
 * Provides a health matrix showing each service's current state.
 *
 * Routes:
 *   GET /service-registry/            → summary + service count
 *   GET /service-registry/services    → all registered services
 *   GET /service-registry/graph       → full dependency graph (adjacency list)
 *   GET /service-registry/dependencies/:id → what service :id depends on
 *   GET /service-registry/dependents/:id   → what depends on :id
 *   GET /service-registry/health-matrix    → all services with current status
 *   GET /service-registry/startup-order    → topological sort (safe boot order)
 *   GET /service-registry/shutdown-order   → reverse of startup (safe teardown)
 *   POST /service-registry/register   → register a new service at runtime
 *   POST /service-registry/probe/:id  → force probe a service's health
 *   GET /service-registry/health      → module health
 */

import type { EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth } from '@empire-os/core'
import { empireLog } from './logger.module.js'

// ── Types ─────────────────────────────────────────────────────────────────────

export type ServiceKind   = 'empire-module' | 'external' | 'adapter' | 'background'
export type ServiceStatus = 'unknown' | 'online' | 'offline' | 'degraded' | 'starting'

export interface ServiceDefinition {
  id:           string
  name:         string
  kind:         ServiceKind
  description:  string
  healthUrl?:   string         // optional HTTP probe URL
  dependencies: string[]       // IDs of services this one requires
  port?:        number
  critical:     boolean        // if offline, empire OS is degraded
}

export interface ServiceState extends ServiceDefinition {
  status:       ServiceStatus
  latencyMs:    number | null
  lastCheckedAt:string | null
  lastSeenAt:   string | null
  errorMessage: string | null
  checkCount:   number
}

// ── Registry ──────────────────────────────────────────────────────────────────

const registry = new Map<string, ServiceState>()

function addService(def: ServiceDefinition): void {
  registry.set(def.id, {
    ...def,
    status:        'unknown',
    latencyMs:     null,
    lastCheckedAt: null,
    lastSeenAt:    null,
    errorMessage:  null,
    checkCount:    0,
  })
}

// ── Built-in service definitions ──────────────────────────────────────────────

function registerBuiltins(): void {
  const services: ServiceDefinition[] = [
    // External services
    { id: 'ollama',         name: 'Ollama',            kind: 'external',        description: 'Local LLM runtime',                    healthUrl: 'http://localhost:11434/api/tags',       dependencies: [],                         port: 11434, critical: false },
    { id: 'open-webui',     name: 'Open WebUI',        kind: 'external',        description: 'Pinokio-hosted Ollama web interface',  healthUrl: 'http://localhost:42004/',               dependencies: ['ollama'],                 port: 42004, critical: false },

    // Adapters (depend on external services or env vars)
    { id: 'adapter-ollama',    name: 'Ollama Adapter',    kind: 'adapter', description: 'Ollama AI provider adapter',      dependencies: ['ollama'],         critical: false },
    { id: 'adapter-anthropic', name: 'Anthropic Adapter', kind: 'adapter', description: 'Claude AI provider adapter',      dependencies: [],                  critical: false },
    { id: 'adapter-gemini',    name: 'Gemini Adapter',    kind: 'adapter', description: 'Google Gemini provider adapter',  dependencies: [],                  critical: false },
    { id: 'adapter-openai',    name: 'OpenAI Adapter',    kind: 'adapter', description: 'OpenAI provider adapter',         dependencies: [],                  critical: false },

    // Core empire-modules (order matters for dependency graph)
    { id: 'logger',             name: 'Empire Logger',         kind: 'empire-module', description: 'Centralized structured logger',          healthUrl: 'http://localhost:3001/logger/health',                dependencies: [],                          critical: true  },
    { id: 'metrics-engine',     name: 'Metrics Engine',        kind: 'empire-module', description: 'Live API performance metrics',            healthUrl: 'http://localhost:3001/metrics-engine/health',        dependencies: ['logger'],                  critical: false },
    { id: 'job-scheduler',      name: 'Job Scheduler',         kind: 'empire-module', description: 'Background job runner',                   healthUrl: 'http://localhost:3001/job-scheduler/health',         dependencies: ['logger'],                  critical: false },
    { id: 'watchdog',           name: 'Health Watchdog',       kind: 'background',    description: '60s background health polling + backups', healthUrl: 'http://localhost:3001/watchdog/health',              dependencies: ['logger'],                  critical: false },
    { id: 'empire-assistant',   name: 'Empire Assistant',      kind: 'empire-module', description: 'AI orchestration + agent chat',           healthUrl: 'http://localhost:3001/empire-assistant/health',      dependencies: ['adapter-ollama'],          critical: true  },
    { id: 'provider-registry',  name: 'Provider Registry',     kind: 'empire-module', description: 'Unified AI provider API',                 healthUrl: 'http://localhost:3001/provider-registry/health',     dependencies: ['adapter-ollama'],          critical: false },
    { id: 'model-manager',      name: 'Model Manager',         kind: 'empire-module', description: 'Ollama model browser + installer',        healthUrl: 'http://localhost:3001/model-manager/health',         dependencies: ['ollama'],                  critical: false },
    { id: 'knowledge-base',     name: 'Knowledge Base',        kind: 'empire-module', description: 'Persistent file-backed memory store',     healthUrl: 'http://localhost:3001/knowledge-base/health',        dependencies: [],                          critical: false },
    { id: 'health-monitor',     name: 'Health Monitor',        kind: 'empire-module', description: 'System resource monitor (RAM/CPU/disk)',   healthUrl: 'http://localhost:3001/health-monitor/health',        dependencies: [],                          critical: false },
    { id: 'media-engine',       name: 'Media Engine',          kind: 'empire-module', description: 'Image/video/audio generation router',     healthUrl: 'http://localhost:3001/media-engine/health',          dependencies: [],                          critical: false },
    { id: 'discovery',          name: 'Discovery',             kind: 'empire-module', description: 'Curated AI model catalog',                healthUrl: 'http://localhost:3001/discovery/health',             dependencies: [],                          critical: false },
    { id: 'discovery-engine',   name: 'Discovery Engine',      kind: 'empire-module', description: 'Live multi-source model discovery',       healthUrl: 'http://localhost:3001/discovery-engine/health',      dependencies: [],                          critical: false },
    { id: 'benchmark-engine',   name: 'Benchmark Engine',      kind: 'empire-module', description: 'Model performance benchmarking',          healthUrl: 'http://localhost:3001/benchmark-engine/health',      dependencies: ['ollama'],                  critical: false },
    { id: 'self-improvement',   name: 'Self Improvement',      kind: 'empire-module', description: 'Model upgrade recommendation engine',     healthUrl: 'http://localhost:3001/self-improvement/health',      dependencies: ['benchmark-engine'],        critical: false },
    { id: 'store',              name: 'Empire Store',          kind: 'empire-module', description: 'One-click AI software catalog',           healthUrl: 'http://localhost:3001/store/health',                 dependencies: [],                          critical: false },
    { id: 'installer',          name: 'Installer',             kind: 'empire-module', description: 'AI tool download + configuration',        healthUrl: 'http://localhost:3001/installer/health',             dependencies: [],                          critical: false },
    { id: 'video-factory',      name: 'Video Factory',         kind: 'empire-module', description: '19-department AI film production',        healthUrl: 'http://localhost:3001/video-factory/health',         dependencies: ['empire-assistant'],        critical: false },
    { id: 'executive',          name: 'Executive',             kind: 'empire-module', description: '10-worker autonomous AI company OS',      healthUrl: 'http://localhost:3001/executive/health',             dependencies: ['empire-assistant'],        critical: false },
    { id: 'notification',       name: 'Notification',          kind: 'empire-module', description: 'Event-driven notification system',        healthUrl: 'http://localhost:3001/notification/health',          dependencies: ['logger'],                  critical: false },
    { id: 'empire-dashboard',   name: 'Empire Dashboard',      kind: 'empire-module', description: 'Gemini glassmorphism SPA frontend',       healthUrl: 'http://localhost:3001/empire-dashboard/health',      dependencies: [],                          critical: false },
  ]

  for (const s of services) addService(s)
}

// ── Dependency graph utilities ─────────────────────────────────────────────────

function buildGraph(): Map<string, string[]> {
  const graph = new Map<string, string[]>()
  for (const [id, svc] of registry) {
    graph.set(id, [...svc.dependencies])
  }
  return graph
}

function topologicalSort(graph: Map<string, string[]>): string[] {
  const visited   = new Set<string>()
  const result:   string[] = []
  const inStack   = new Set<string>()

  function visit(node: string): void {
    if (inStack.has(node)) return  // cycle — skip
    if (visited.has(node)) return
    inStack.add(node)
    for (const dep of (graph.get(node) ?? [])) {
      visit(dep)
    }
    inStack.delete(node)
    visited.add(node)
    result.push(node)
  }

  for (const id of graph.keys()) visit(id)
  return result
}

function getDependents(targetId: string): string[] {
  const result: string[] = []
  for (const [id, svc] of registry) {
    if (svc.dependencies.includes(targetId)) result.push(id)
  }
  return result
}

// ── Health probe ──────────────────────────────────────────────────────────────

async function probeService(svc: ServiceState): Promise<void> {
  svc.checkCount++
  svc.lastCheckedAt = new Date().toISOString()

  if (!svc.healthUrl) {
    // No probe URL — assume online if it's an empire-module (server is running)
    if (svc.kind === 'empire-module' || svc.kind === 'background') {
      svc.status    = 'online'
      svc.latencyMs = 0
    }
    return
  }

  const start = Date.now()
  try {
    const res = await fetch(svc.healthUrl, {
      method: 'GET',
      signal: AbortSignal.timeout(5_000),
    })
    svc.latencyMs   = Date.now() - start
    svc.status      = res.ok ? 'online' : 'degraded'
    svc.errorMessage = res.ok ? null : `HTTP ${res.status}`
    if (res.ok) svc.lastSeenAt = svc.lastCheckedAt
  } catch (e) {
    svc.latencyMs    = Date.now() - start
    svc.status       = 'offline'
    svc.errorMessage = e instanceof Error ? e.message : String(e)
  }
}

// ── Module ────────────────────────────────────────────────────────────────────

export class ServiceRegistryModule implements EmpireModule {
  readonly moduleId = 'service-registry'

  async init(_services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    registerBuiltins()
    empireLog('INFO', 'service-registry', `Service registry initialized`, {
      serviceCount: registry.size,
    })

    // Run an initial lightweight probe pass (no await — don't block startup)
    setTimeout(() => this.runProbePass(), 2_000)

    // Re-probe every 5 minutes to keep health matrix fresh
    setInterval(() => this.runProbePass(), 5 * 60 * 1_000)
  }

  private async runProbePass(): Promise<void> {
    const probes = [...registry.values()].map(svc => probeService(svc))
    await Promise.allSettled(probes)
    const online  = [...registry.values()].filter(s => s.status === 'online').length
    const offline = [...registry.values()].filter(s => s.status === 'offline').length
    empireLog('INFO', 'service-registry', `Probe pass complete`, { online, offline, total: registry.size })
  }

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start  = Date.now()
    const path   = (req.path === '' ? '/' : req.path).split('?')[0]
    const method = req.method

    try {
      // GET / — summary
      if ((path === '/' || path === '') && method === 'GET') {
        const all = [...registry.values()]
        return this.ok(start, {
          module:       'Service Registry',
          serviceCount: all.length,
          online:       all.filter(s => s.status === 'online').length,
          offline:      all.filter(s => s.status === 'offline').length,
          unknown:      all.filter(s => s.status === 'unknown').length,
          critical:     all.filter(s => s.critical && s.status === 'offline').length,
          endpoints: {
            services:      'GET /service-registry/services',
            graph:         'GET /service-registry/graph',
            healthMatrix:  'GET /service-registry/health-matrix',
            startupOrder:  'GET /service-registry/startup-order',
            dependencies:  'GET /service-registry/dependencies/:id',
            probe:         'POST /service-registry/probe/:id',
          },
        })
      }

      // GET /services — full list
      if (path === '/services' && method === 'GET') {
        const services = [...registry.values()].map(s => this.serviceSummary(s))
        return this.ok(start, { services, total: services.length })
      }

      // GET /graph — adjacency list
      if (path === '/graph' && method === 'GET') {
        const graph: Record<string, string[]> = {}
        for (const [id, svc] of registry) {
          graph[id] = svc.dependencies
        }
        return this.ok(start, { graph, nodeCount: registry.size })
      }

      // GET /health-matrix
      if (path === '/health-matrix' && method === 'GET') {
        const matrix = [...registry.values()].map(s => ({
          id:           s.id,
          name:         s.name,
          kind:         s.kind,
          status:       s.status,
          latencyMs:    s.latencyMs,
          critical:     s.critical,
          lastCheckedAt:s.lastCheckedAt,
          errorMessage: s.errorMessage,
        }))
        const criticalDown = matrix.filter(m => m.critical && m.status === 'offline').map(m => m.id)
        return this.ok(start, {
          matrix,
          summary: {
            total:       matrix.length,
            online:      matrix.filter(m => m.status === 'online').length,
            offline:     matrix.filter(m => m.status === 'offline').length,
            degraded:    matrix.filter(m => m.status === 'degraded').length,
            unknown:     matrix.filter(m => m.status === 'unknown').length,
            criticalDown,
          },
        })
      }

      // GET /startup-order
      if (path === '/startup-order' && method === 'GET') {
        const order = topologicalSort(buildGraph())
        return this.ok(start, { order, count: order.length })
      }

      // GET /shutdown-order
      if (path === '/shutdown-order' && method === 'GET') {
        const order = topologicalSort(buildGraph()).reverse()
        return this.ok(start, { order, count: order.length })
      }

      // GET /dependencies/:id
      const depMatch = path.match(/^\/dependencies\/(.+)$/)
      if (depMatch && method === 'GET') {
        const id  = depMatch[1]
        const svc = registry.get(id)
        if (!svc) return this.notFound(start, `Service not found: ${id}`)
        const deps = svc.dependencies.map(d => registry.get(d)).filter(Boolean)
        return this.ok(start, { id, dependsOn: deps?.map(d => this.serviceSummary(d!)), count: deps?.length })
      }

      // GET /dependents/:id
      const depentsMatch = path.match(/^\/dependents\/(.+)$/)
      if (depentsMatch && method === 'GET') {
        const id      = depentsMatch[1]
        const svc     = registry.get(id)
        if (!svc) return this.notFound(start, `Service not found: ${id}`)
        const depIds  = getDependents(id)
        const depents = depIds.map(d => registry.get(d)).filter(Boolean)
        return this.ok(start, { id, dependents: depents.map(d => this.serviceSummary(d!)), count: depents.length })
      }

      // POST /register
      if (path === '/register' && method === 'POST') {
        const body = (req.body ?? {}) as Partial<ServiceDefinition>
        if (!body.id || !body.name || !body.kind) {
          return this.badRequest(start, 'Required fields: id, name, kind')
        }
        if (registry.has(body.id)) {
          return this.conflict(start, `Service already registered: ${body.id}`)
        }
        addService({
          id:           body.id,
          name:         body.name,
          kind:         body.kind,
          description:  body.description ?? '',
          healthUrl:    body.healthUrl,
          dependencies: body.dependencies ?? [],
          port:         body.port,
          critical:     body.critical ?? false,
        })
        empireLog('INFO', 'service-registry', `Service registered: ${body.id}`)
        return this.ok(start, { message: `Registered: ${body.id}`, service: this.serviceSummary(registry.get(body.id)!) })
      }

      // POST /probe/:id
      const probeMatch = path.match(/^\/probe\/(.+)$/)
      if (probeMatch && method === 'POST') {
        const id  = probeMatch[1]
        const svc = registry.get(id)
        if (!svc) return this.notFound(start, `Service not found: ${id}`)
        await probeService(svc)
        return this.ok(start, {
          message:  `Probed ${id}`,
          status:   svc.status,
          latencyMs:svc.latencyMs,
          error:    svc.errorMessage,
        })
      }

      // GET /health
      if (path === '/health' && method === 'GET') {
        return this.ok(start, await this.health())
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      empireLog('ERROR', 'service-registry', `Error on ${method} ${path}`, msg)
      return this.serverError(start, msg)
    }
  }

  async health(): Promise<ModuleHealth> {
    const all      = [...registry.values()]
    const critDown = all.filter(s => s.critical && s.status === 'offline').length
    return {
      status:  critDown === 0 ? 'healthy' : 'degraded',
      details: {
        total:        all.length,
        online:       all.filter(s => s.status === 'online').length,
        offline:      all.filter(s => s.status === 'offline').length,
        criticalDown: critDown,
      },
    }
  }

  async handleEvent(): Promise<void> {}
  async shutdown(): Promise<void> {
    empireLog('INFO', 'service-registry', 'Service registry shutting down')
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  private serviceSummary(s: ServiceState) {
    return {
      id:           s.id,
      name:         s.name,
      kind:         s.kind,
      description:  s.description,
      status:       s.status,
      latencyMs:    s.latencyMs,
      critical:     s.critical,
      port:         s.port,
      dependencies: s.dependencies,
      lastCheckedAt:s.lastCheckedAt,
      errorMessage: s.errorMessage,
    }
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
  private conflict(start: number, msg: string): GatewayResponse {
    return { status: 409, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
  private serverError(start: number, msg: string): GatewayResponse {
    return { status: 500, body: { error: msg, timestamp: new Date().toISOString() }, moduleId: this.moduleId, durationMs: Date.now() - start }
  }
}
