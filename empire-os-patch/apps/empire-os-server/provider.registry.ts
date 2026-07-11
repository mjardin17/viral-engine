/**
 * ProviderRegistryModule — Unified AI Provider Layer
 *
 * Every AI provider accessible through one interface.
 * Each provider exposes: complete(), models(), health()
 *
 * Routes:
 *   GET  /provider-registry/               → all providers + live status
 *   GET  /provider-registry/health         → full health check of every provider
 *   GET  /provider-registry/:id            → single provider info
 *   GET  /provider-registry/:id/models     → models from that provider
 *   POST /provider-registry/complete       → auto-routed completion (uses AIRouter)
 *   POST /provider-registry/:id/complete   → completion via specific provider
 *   GET  /provider-registry/summary        → machine-readable capability matrix
 */

import type {
  EmpireModule, CoreServices, GatewayRequest, GatewayResponse, ModuleHealth,
} from '@empire-os/core'
import type { AIProviderAdapter } from '@empire-os/core'
import { OllamaAdapter } from './adapters/ollama.adapter.js'
import { AnthropicAdapter } from './adapters/anthropic.adapter.js'
import { GeminiAdapter } from './adapters/gemini.adapter.js'
import { OpenAIAdapter } from './adapters/openai.adapter.js'
import { GooseExecutor } from './goose.executor.js'

// ── Unified types ─────────────────────────────────────────────────────────────

export type ProviderId = 'ollama' | 'anthropic' | 'gemini' | 'openai' | 'goose'
export type ProviderType = 'local' | 'cloud' | 'agent'

export interface ProviderHealth {
  status:     'ok' | 'offline'
  latencyMs:  number
  modelCount: number
  error?:     string
  checkedAt:  string
}

export interface ProviderEntry {
  id:           ProviderId
  name:         string
  type:         ProviderType
  description:  string
  capabilities: string[]
  cost:         'free' | 'paid' | 'self-hosted'
}

// Registry of known providers (static metadata)
const PROVIDER_CATALOG: Record<ProviderId, ProviderEntry> = {
  ollama: {
    id: 'ollama', name: 'Ollama', type: 'local',
    description: 'Local LLM runtime — free, private, no API key needed',
    capabilities: ['chat', 'complete', 'code', 'embeddings'],
    cost: 'free',
  },
  anthropic: {
    id: 'anthropic', name: 'Anthropic Claude', type: 'cloud',
    description: 'Claude Opus 4, Sonnet 4, Haiku 4 — best for code and architecture',
    capabilities: ['chat', 'complete', 'code', 'reasoning', 'long-context', 'function-calling'],
    cost: 'paid',
  },
  gemini: {
    id: 'gemini', name: 'Google Gemini', type: 'cloud',
    description: 'Gemini 1.5 Pro/Flash — best for research and million-token context',
    capabilities: ['chat', 'complete', 'research', 'long-context', 'vision'],
    cost: 'paid',
  },
  openai: {
    id: 'openai', name: 'OpenAI GPT', type: 'cloud',
    description: 'GPT-4o / GPT-4o-mini — general purpose + tool-use',
    capabilities: ['chat', 'complete', 'code', 'function-calling', 'vision'],
    cost: 'paid',
  },
  goose: {
    id: 'goose', name: 'Goose AI Agent', type: 'agent',
    description: 'Local AI agent — runs shell commands, edits files, executes code',
    capabilities: ['agent', 'shell', 'file-ops', 'code-exec'],
    cost: 'free',
  },
}

// ── Module ────────────────────────────────────────────────────────────────────

export class ProviderRegistryModule implements EmpireModule {
  readonly moduleId = 'provider-registry'

  private services!: CoreServices
  private ollama:    OllamaAdapter     | null = null
  private anthropic: AnthropicAdapter  | null = null
  private gemini:    GeminiAdapter     | null = null
  private openai:    OpenAIAdapter     | null = null
  private goose:     GooseExecutor     | null = null

  // Health cache — refreshed on each /health call, max 30s old
  private healthCache: Map<ProviderId, ProviderHealth> = new Map()
  private healthCachedAt = 0

  // ── Lifecycle ───────────────────────────────────────────────────────────────

  async init(services: CoreServices, _config: Record<string, unknown>): Promise<void> {
    this.services = services
    console.log('[ProviderRegistry] Unified provider layer initializing...')

    // Discover all available providers
    await this.discoverProviders()

    console.log(`[ProviderRegistry] Ready — ${this.availableCount()} of 5 providers active`)
  }

  /**
   * Called by server.ts after adapters are created, so the registry
   * can reference the same instances already registered with AIRouter.
   */
  registerAdapters(opts: {
    ollama?:    OllamaAdapter
    anthropic?: AnthropicAdapter
    gemini?:    GeminiAdapter
    openai?:    OpenAIAdapter
    goose?:     GooseExecutor
  }): void {
    if (opts.ollama)    this.ollama    = opts.ollama
    if (opts.anthropic) this.anthropic = opts.anthropic
    if (opts.gemini)    this.gemini    = opts.gemini
    if (opts.openai)    this.openai    = opts.openai
    if (opts.goose)     this.goose     = opts.goose
  }

  private async discoverProviders(): Promise<void> {
    // Ollama: always attempt
    try {
      if (!this.ollama) {
        const base = process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434'
        this.ollama = await OllamaAdapter.create(base)
      }
    } catch { /* not available */ }

    // Cloud providers: key-gated
    if (process.env.ANTHROPIC_API_KEY && !this.anthropic) {
      this.anthropic = new AnthropicAdapter(process.env.ANTHROPIC_API_KEY)
    }
    if (process.env.GOOGLE_API_KEY && !this.gemini) {
      this.gemini = new GeminiAdapter(process.env.GOOGLE_API_KEY)
    }
    if (process.env.OPENAI_API_KEY && !this.openai) {
      this.openai = new OpenAIAdapter(process.env.OPENAI_API_KEY)
    }

    // Goose: auto-detect
    if (!this.goose) {
      this.goose = await GooseExecutor.create()
    }
  }

  private availableCount(): number {
    return [this.ollama, this.anthropic, this.gemini, this.openai, this.goose]
      .filter(Boolean).length
  }

  async health(): Promise<ModuleHealth> {
    return {
      status: 'healthy',
      details: {
        totalProviders: 5,
        activeProviders: this.availableCount(),
        providers: ['ollama', 'anthropic', 'gemini', 'openai', 'goose'],
      },
    }
  }

  async handleEvent(): Promise<void> {}
  async shutdown(): Promise<void> {}

  // ── Request router ──────────────────────────────────────────────────────────

  async handleRequest(req: GatewayRequest): Promise<GatewayResponse> {
    const start = Date.now()
    const path   = req.path === '' ? '/' : req.path
    const method = req.method

    try {
      // GET /provider-registry/
      if ((path === '/' || path === '') && method === 'GET') {
        return this.ok(start, await this.getAllProviders())
      }

      // GET /provider-registry/health
      if (path === '/health' && method === 'GET') {
        const h = await this.checkAllHealth(true)
        return this.ok(start, h)
      }

      // GET /provider-registry/summary
      if (path === '/summary' && method === 'GET') {
        return this.ok(start, this.buildCapabilityMatrix())
      }

      // POST /provider-registry/complete
      if (path === '/complete' && method === 'POST') {
        const { prompt, strategy } = (req.body as Record<string, string>) ?? {}
        if (!prompt) return this.badRequest(start, 'prompt is required')
        const result = await this.routedComplete(prompt, strategy)
        return this.ok(start, result)
      }

      // Provider-specific routes: /provider-registry/:id/...
      const providerMatch = path.match(/^\/([a-z]+)(\/.*)?$/)
      if (providerMatch) {
        const pid = providerMatch[1] as ProviderId
        const sub = providerMatch[2] ?? '/'

        if (!(pid in PROVIDER_CATALOG)) return this.notFound(start, `Unknown provider: ${pid}`)

        // GET /provider-registry/:id
        if (sub === '/' && method === 'GET') {
          return this.ok(start, await this.getProvider(pid))
        }

        // GET /provider-registry/:id/models
        if (sub === '/models' && method === 'GET') {
          return this.ok(start, { provider: pid, models: await this.getModels(pid) })
        }

        // GET /provider-registry/:id/health
        if (sub === '/health' && method === 'GET') {
          return this.ok(start, { provider: pid, health: await this.checkProviderHealth(pid) })
        }

        // POST /provider-registry/:id/complete
        if (sub === '/complete' && method === 'POST') {
          const { prompt, model } = (req.body as Record<string, string>) ?? {}
          if (!prompt) return this.badRequest(start, 'prompt is required')
          const result = await this.directComplete(pid, prompt, model)
          return this.ok(start, result)
        }

        // POST /provider-registry/:id/stream
        // Collects all stream chunks synchronously and returns joined content
        if (sub === '/stream' && method === 'POST') {
          const { prompt, model } = (req.body as Record<string, string>) ?? {}
          if (!prompt) return this.badRequest(start, 'prompt is required')
          const result = await this.directStream(pid, prompt, model)
          return this.ok(start, result)
        }

        // POST /provider-registry/:id/vision
        if (sub === '/vision' && method === 'POST') {
          const body = req.body as Record<string, string> | undefined
          if (!body?.imageBase64 || !body?.prompt) {
            return this.badRequest(start, 'imageBase64 and prompt are required')
          }
          const result = await this.directVision(pid, body.imageBase64, body.prompt, body.model, body.mediaType)
          return this.ok(start, result)
        }

        // POST /provider-registry/:id/embeddings
        if (sub === '/embeddings' && method === 'POST') {
          const { text, model } = (req.body as Record<string, string>) ?? {}
          if (!text) return this.badRequest(start, 'text is required')
          const result = await this.directEmbeddings(pid, text, model)
          return this.ok(start, result)
        }
      }

      return this.notFound(start, `No route: ${method} ${path}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[ProviderRegistry] Error on ${method} ${path}: ${msg}`)
      return this.serverError(start, msg)
    }
  }

  // ── Provider operations ─────────────────────────────────────────────────────

  private async getAllProviders() {
    const health = await this.checkAllHealth(false)
    return {
      providers: Object.values(PROVIDER_CATALOG).map(p => ({
        ...p,
        available: this.isAvailable(p.id),
        health: health.providers[p.id] ?? null,
      })),
      activeCount: this.availableCount(),
      totalCount: 5,
      timestamp: new Date().toISOString(),
    }
  }

  private async getProvider(id: ProviderId) {
    const catalog = PROVIDER_CATALOG[id]
    const health  = await this.checkProviderHealth(id)
    const models  = await this.getModels(id)
    return { ...catalog, available: this.isAvailable(id), health, models }
  }

  private isAvailable(id: ProviderId): boolean {
    switch (id) {
      case 'ollama':    return this.ollama    != null
      case 'anthropic': return this.anthropic != null
      case 'gemini':    return this.gemini    != null
      case 'openai':    return this.openai    != null
      case 'goose':     return this.goose?.available ?? false
      default: return false
    }
  }

  private async getModels(id: ProviderId): Promise<{ id: string; available: boolean }[]> {
    try {
      switch (id) {
        case 'ollama':
          if (!this.ollama) return []
          return this.ollama.models.map(m => ({ id: m.id, available: true }))
        case 'anthropic':
          return this.anthropic ? [
            { id: 'claude-opus-4-8', available: true },
            { id: 'claude-sonnet-4-6', available: true },
            { id: 'claude-haiku-4-5-20251001', available: true },
          ] : []
        case 'gemini':
          return this.gemini ? [
            { id: 'gemini-1.5-pro', available: true },
            { id: 'gemini-1.5-flash', available: true },
          ] : []
        case 'openai':
          return this.openai ? [
            { id: 'gpt-4o', available: true },
            { id: 'gpt-4o-mini', available: true },
          ] : []
        case 'goose':
          return this.goose?.available ? [{ id: 'goose-agent', available: true }] : []
        default: return []
      }
    } catch {
      return []
    }
  }

  private async checkProviderHealth(id: ProviderId): Promise<ProviderHealth> {
    const t0 = Date.now()
    try {
      let ok = false
      switch (id) {
        case 'ollama':    ok = (await this.ollama?.isAvailable())    ?? false; break
        case 'anthropic': ok = (await this.anthropic?.isAvailable()) ?? false; break
        case 'gemini':    ok = (await this.gemini?.isAvailable())    ?? false; break
        case 'openai':    ok = (await this.openai?.isAvailable())    ?? false; break
        case 'goose':     ok = this.goose?.available ?? false;                 break
      }
      const models = await this.getModels(id)
      return { status: ok ? 'ok' : 'offline', latencyMs: Date.now() - t0, modelCount: models.length, checkedAt: new Date().toISOString() }
    } catch (e) {
      return { status: 'offline', latencyMs: Date.now() - t0, modelCount: 0, error: String(e), checkedAt: new Date().toISOString() }
    }
  }

  private async checkAllHealth(fresh: boolean): Promise<{ providers: Record<string, ProviderHealth>; checkedAt: string }> {
    const now = Date.now()
    if (!fresh && this.healthCachedAt && now - this.healthCachedAt < 30_000) {
      return { providers: Object.fromEntries(this.healthCache), checkedAt: new Date(this.healthCachedAt).toISOString() }
    }

    const ids: ProviderId[] = ['ollama', 'anthropic', 'gemini', 'openai', 'goose']
    const results = await Promise.all(ids.map(id => this.checkProviderHealth(id).then(h => [id, h] as const)))
    this.healthCache = new Map(results)
    this.healthCachedAt = now
    return { providers: Object.fromEntries(results), checkedAt: new Date().toISOString() }
  }

  private buildCapabilityMatrix() {
    const matrix: Record<string, string[]> = {}
    for (const [id, p] of Object.entries(PROVIDER_CATALOG)) {
      matrix[id] = p.capabilities
    }
    return {
      matrix,
      recommended: {
        code:      'anthropic',
        research:  'gemini',
        local:     'ollama',
        agent:     'goose',
        copy:      'ollama',
        vision:    'gemini',
        longCtx:   'gemini',
      },
    }
  }

  private async routedComplete(prompt: string, strategy?: string): Promise<Record<string, unknown>> {
    const t0 = Date.now()
    try {
      const result = await this.services.aiRouter.complete({
        messages: [{ role: 'user', content: prompt }],
        strategy: (strategy as 'quality' | 'speed' | 'cost' | 'local-only') ?? 'cost',
      })
      return { content: result.content, model: result.model, provider: result.provider, durationMs: Date.now() - t0 }
    } catch (e) {
      throw new Error(`AI routing failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  // ── directStream — collect all chunks synchronously ───────────────────────

  private async directStream(id: ProviderId, prompt: string, model?: string): Promise<Record<string, unknown>> {
    const t0      = Date.now()
    const chunks: string[] = []
    const messages = [{ role: 'user' as const, content: prompt }]

    const defaultModels: Record<string, string> = {
      ollama:    this.ollama?.models[0]?.id ?? 'qwen2.5-coder:7b',
      anthropic: 'claude-sonnet-4-6',
      gemini:    'gemini-1.5-flash',
      openai:    'gpt-4o-mini',
    }
    const selectedModel = model ?? defaultModels[id] ?? ''
    const opts = { maxTokens: 1024, temperature: 0.7 }

    let inputTokens  = 0
    let outputTokens = 0

    switch (id) {
      case 'ollama':
        if (!this.ollama) throw new Error('Ollama not available')
        { const r = await this.ollama.stream(messages, selectedModel, opts, c => chunks.push(c))
          inputTokens = r.inputTokens; outputTokens = r.outputTokens }
        break
      case 'anthropic':
        if (!this.anthropic) throw new Error('Anthropic not available')
        { const r = await this.anthropic.stream(messages, selectedModel, opts, c => chunks.push(c))
          inputTokens = r.inputTokens; outputTokens = r.outputTokens }
        break
      case 'gemini':
        if (!this.gemini) throw new Error('Gemini not available')
        { const r = await this.gemini.stream(messages, selectedModel, opts, c => chunks.push(c))
          inputTokens = r.inputTokens; outputTokens = r.outputTokens }
        break
      case 'openai':
        if (!this.openai) throw new Error('OpenAI not available')
        { const r = await this.openai.stream(messages, selectedModel, opts, c => chunks.push(c))
          inputTokens = r.inputTokens; outputTokens = r.outputTokens }
        break
      case 'goose':
        // Goose doesn't stream — fall back to run()
        if (!this.goose?.available) throw new Error('Goose not available')
        { const r = await this.goose.run(prompt)
          chunks.push(r.output) }
        break
      default:
        throw new Error(`Unknown provider: ${id}`)
    }

    return {
      content:    chunks.join(''),
      chunks:     chunks.length,
      model:      selectedModel,
      provider:   id,
      tokensIn:   inputTokens,
      tokensOut:  outputTokens,
      durationMs: Date.now() - t0,
    }
  }

  // ── directVision ──────────────────────────────────────────────────────────

  private async directVision(
    id: ProviderId,
    imageBase64: string,
    prompt: string,
    model?: string,
    mediaType?: string,
  ): Promise<Record<string, unknown>> {
    const t0 = Date.now()
    let content = ''

    switch (id) {
      case 'ollama':
        if (!this.ollama) throw new Error('Ollama not available')
        content = await this.ollama.vision(imageBase64, prompt, { model, maxTokens: 1024 })
        break
      case 'anthropic':
        if (!this.anthropic) throw new Error('Anthropic not available')
        content = await this.anthropic.vision(imageBase64, prompt, { model, mediaType })
        break
      case 'gemini':
        if (!this.gemini) throw new Error('Gemini not available')
        content = await this.gemini.vision(imageBase64, prompt, { model, mediaType })
        break
      case 'openai':
        if (!this.openai) throw new Error('OpenAI not available')
        content = await this.openai.vision(imageBase64, prompt, { model, mediaType })
        break
      case 'goose':
        throw new Error('Goose does not support vision')
      default:
        throw new Error(`Unknown provider: ${id}`)
    }

    return { content, provider: id, durationMs: Date.now() - t0 }
  }

  // ── directEmbeddings ──────────────────────────────────────────────────────

  private async directEmbeddings(
    id: ProviderId,
    text: string,
    model?: string,
  ): Promise<Record<string, unknown>> {
    const t0 = Date.now()
    let embedding: number[] = []

    switch (id) {
      case 'ollama':
        if (!this.ollama) throw new Error('Ollama not available')
        embedding = await this.ollama.embeddings(text, model)
        break
      case 'anthropic':
        if (!this.anthropic) throw new Error('Anthropic not available')
        await this.anthropic.embeddings(text, model)  // always throws with clear message
        break
      case 'gemini':
        if (!this.gemini) throw new Error('Gemini not available')
        embedding = await this.gemini.embeddings(text, model)
        break
      case 'openai':
        if (!this.openai) throw new Error('OpenAI not available')
        embedding = await this.openai.embeddings(text, model)
        break
      case 'goose':
        throw new Error('Goose does not support embeddings')
      default:
        throw new Error(`Unknown provider: ${id}`)
    }

    return {
      embedding,
      dimensions: embedding.length,
      provider:   id,
      durationMs: Date.now() - t0,
    }
  }

  private async directComplete(id: ProviderId, prompt: string, model?: string): Promise<Record<string, unknown>> {
    const t0 = Date.now()
    const messages = [{ role: 'user' as const, content: prompt }]
    let adapter: AIProviderAdapter | null = null

    switch (id) {
      case 'ollama':    adapter = this.ollama as unknown as AIProviderAdapter | null; break
      case 'anthropic': adapter = this.anthropic as unknown as AIProviderAdapter | null; break
      case 'gemini':    adapter = this.gemini as unknown as AIProviderAdapter | null; break
      case 'openai':    adapter = this.openai as unknown as AIProviderAdapter | null; break
    }

    if (id === 'goose') {
      if (!this.goose?.available) throw new Error('Goose not available')
      const r = await this.goose.run(prompt)
      return { content: r.output, model: 'goose-agent', provider: 'goose', durationMs: r.durationMs }
    }

    if (!adapter) throw new Error(`Provider ${id} not configured or not available`)

    const defaultModels: Record<string, string> = {
      ollama:    'qwen2.5-coder:7b',
      anthropic: 'claude-sonnet-4-6',
      gemini:    'gemini-1.5-flash',
      openai:    'gpt-4o-mini',
    }
    const selectedModel = model ?? defaultModels[id] ?? ''

    const r = await adapter.complete(messages, selectedModel, { maxTokens: 1024, temperature: 0.7 })
    return {
      content:   r.content,
      model:     selectedModel,
      provider:  id,
      tokensIn:  r.inputTokens,
      tokensOut: r.outputTokens,
      durationMs: r.durationMs ?? Date.now() - t0,
    }
  }

  // ── Response helpers ────────────────────────────────────────────────────────

  private ok(start: number, body: unknown, status = 200): GatewayResponse {
    return { status, body, moduleId: this.moduleId, durationMs: Date.now() - start }
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
