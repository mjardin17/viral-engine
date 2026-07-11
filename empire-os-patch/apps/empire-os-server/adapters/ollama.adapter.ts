/**
 * Ollama — AIProviderAdapter
 *
 * Auto-discovers every locally-installed model via GET /api/tags at startup.
 * No API key required — local inference only.
 *
 * Exposes full unified interface:
 *   complete()    — full chat completion (messages array)
 *   chat()        — single-prompt convenience wrapper → string
 *   stream()      — NDJSON streaming with onChunk callback
 *   vision()      — image + text for llava/moondream/bakllava models
 *   embeddings()  — dense vector embeddings via POST /api/embeddings
 *   health()      — liveness check against /api/tags
 *   models()      — list of discovered models
 *
 * Use OllamaAdapter.create() (async factory) so model discovery happens
 * before the adapter is registered with the AIRouter.
 */

import type { AIProviderAdapter } from '@empire-os/core'
import type { AIModel, AIMessage } from '@empire-os/core'

// ── Ollama API shapes ─────────────────────────────────────────────────────────

interface OllamaTagEntry {
  name:     string
  model:    string
  size:     number
  details?: {
    parameter_size?: string   // e.g. "8.0B", "70B"
    family?:         string
    families?:       string[]
  }
}

interface OllamaTagsResponse { models: OllamaTagEntry[] }

interface OllamaChatResponse {
  model:               string
  message:             { role: string; content: string }
  done:                boolean
  prompt_eval_count?:  number
  eval_count?:         number
  total_duration?:     number   // nanoseconds
}

interface OllamaChatStreamChunk {
  model:    string
  message:  { role: string; content: string }
  done:     boolean
  eval_count?: number
  prompt_eval_count?: number
}

interface OllamaEmbedResponse {
  embedding: number[]
}

// ── Capability inference ──────────────────────────────────────────────────────

function inferCapabilities(entry: OllamaTagEntry): AIModel['capabilities'] {
  const name = (entry.name + ' ' + (entry.details?.family ?? '')).toLowerCase()
  const caps = new Set<string>(['chat'])

  if (/code|starcoder|deepcoder|codegemma|codellama|qwen.*coder|granite.*code/.test(name)) {
    caps.add('code')
  }
  if (/llava|vision|minicpm.v|bakllava|moondream|cogvlm/.test(name)) {
    caps.add('vision')
  }
  if (/embed/.test(name)) {
    caps.add('embeddings')
  }

  const billions = parseParamBillions(entry.details?.parameter_size)
  if (billions >= 30) {
    caps.add('reasoning')
    caps.add('research')
    caps.add('long-context')
  } else if (billions >= 13) {
    caps.add('research')
  }

  return [...caps] as AIModel['capabilities']
}

function parseParamBillions(paramSize: string | undefined): number {
  if (!paramSize) return 0
  const match = paramSize.match(/(\d+(?:\.\d+)?)\s*[Bb]/)
  return match ? parseFloat(match[1]) : 0
}

function inferContextWindow(entry: OllamaTagEntry): number {
  const billions = parseParamBillions(entry.details?.parameter_size)
  if (billions >= 70) return 32_768
  if (billions >= 30) return 16_384
  if (billions >= 13) return  8_192
  return 4_096
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type StreamChunkCallback = (chunk: string) => void

export interface CompletionResult {
  content:      string
  inputTokens:  number
  outputTokens: number
  durationMs:   number
}

export interface StreamResult {
  inputTokens:  number
  outputTokens: number
  durationMs:   number
}

// ── Adapter ───────────────────────────────────────────────────────────────────

export class OllamaAdapter implements AIProviderAdapter {
  readonly provider = 'ollama' as const
  readonly models:   AIModel[]

  private constructor(
    private readonly baseUrl: string,
    models: AIModel[],
  ) {
    this.models = models
  }

  /**
   * Async factory — discovers installed models before returning.
   * Throws if Ollama is unreachable.
   */
  static async create(baseUrl = 'http://localhost:11434'): Promise<OllamaAdapter> {
    const res = await fetch(`${baseUrl}/api/tags`, {
      signal: AbortSignal.timeout(5_000),
    })
    if (!res.ok) {
      throw new Error(`[OllamaAdapter] /api/tags returned ${res.status}`)
    }

    const data    = await res.json() as OllamaTagsResponse
    const entries = data.models ?? []

    const models: AIModel[] = entries.map(entry => ({
      id:            entry.name,
      provider:      'ollama' as const,
      capabilities:  inferCapabilities(entry),
      contextWindow: inferContextWindow(entry),
      costPerMToken: 0,   // free — local inference
      available:     true,
    }))

    return new OllamaAdapter(baseUrl, models)
  }

  // ── Interface compliance ──────────────────────────────────────────────────

  async isAvailable(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/tags`, {
        signal: AbortSignal.timeout(3_000),
      })
      return res.ok
    } catch {
      return false
    }
  }

  // ── complete() — full message array completion ────────────────────────────

  async complete(
    messages: AIMessage[],
    model: string,
    options: { maxTokens?: number; temperature?: number },
  ): Promise<CompletionResult> {
    const start = Date.now()

    const body = {
      model,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      stream:   false,
      options: {
        num_predict:  options.maxTokens  ?? 4_096,
        temperature:  options.temperature ?? 0.7,
      },
    }

    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(120_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[OllamaAdapter] /api/chat error ${res.status}: ${text}`)
    }

    const data = await res.json() as OllamaChatResponse

    return {
      content:      data.message?.content ?? '',
      inputTokens:  data.prompt_eval_count ?? 0,
      outputTokens: data.eval_count        ?? 0,
      durationMs:   data.total_duration
        ? Math.round(data.total_duration / 1_000_000)
        : Date.now() - start,
    }
  }

  // ── chat() — single-prompt convenience wrapper ────────────────────────────

  async chat(
    prompt: string,
    opts: { model?: string; maxTokens?: number; temperature?: number; system?: string } = {},
  ): Promise<string> {
    const messages: AIMessage[] = []
    if (opts.system) messages.push({ role: 'system', content: opts.system })
    messages.push({ role: 'user', content: prompt })
    const defaultModel = this.models[0]?.id ?? 'qwen2.5-coder:7b'
    const r = await this.complete(messages, opts.model ?? defaultModel, {
      maxTokens:   opts.maxTokens,
      temperature: opts.temperature,
    })
    return r.content
  }

  // ── stream() — NDJSON streaming with per-chunk callback ───────────────────

  async stream(
    messages: AIMessage[],
    model: string,
    options: { maxTokens?: number; temperature?: number },
    onChunk: StreamChunkCallback,
  ): Promise<StreamResult> {
    const start = Date.now()

    const body = {
      model,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      stream:   true,
      options: {
        num_predict: options.maxTokens  ?? 4_096,
        temperature: options.temperature ?? 0.7,
      },
    }

    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(120_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[OllamaAdapter/stream] /api/chat error ${res.status}: ${text}`)
    }

    if (!res.body) throw new Error('[OllamaAdapter/stream] No response body')

    let inputTokens  = 0
    let outputTokens = 0

    const reader  = res.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const chunk = JSON.parse(line) as OllamaChatStreamChunk
          if (chunk.message?.content) onChunk(chunk.message.content)
          if (chunk.done) {
            inputTokens  = chunk.prompt_eval_count ?? 0
            outputTokens = chunk.eval_count        ?? 0
          }
        } catch {
          // malformed NDJSON line — skip
        }
      }
    }

    return { inputTokens, outputTokens, durationMs: Date.now() - start }
  }

  // ── vision() — image + text for llava/moondream models ───────────────────

  async vision(
    imageBase64: string,
    prompt: string,
    opts: { model?: string; maxTokens?: number } = {},
  ): Promise<string> {
    // Default to first llava-capable model if available
    const visionModel = opts.model ?? this.models.find(m =>
      m.capabilities.includes('vision')
    )?.id ?? 'llava'

    const body = {
      model:   visionModel,
      messages: [{
        role:    'user',
        content: prompt,
        images:  [imageBase64],
      }],
      stream:  false,
      options: { num_predict: opts.maxTokens ?? 1024 },
    }

    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(120_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[OllamaAdapter/vision] /api/chat error ${res.status}: ${text}`)
    }

    const data = await res.json() as OllamaChatResponse
    return data.message?.content ?? ''
  }

  // ── embeddings() — dense vector embeddings ────────────────────────────────

  async embeddings(text: string, model?: string): Promise<number[]> {
    // Auto-select: prefer nomic-embed-text, fall back to first embed model, then main model
    const embedModel = model
      ?? this.models.find(m => m.id.includes('nomic') || m.id.includes('embed'))?.id
      ?? this.models[0]?.id
      ?? 'nomic-embed-text'

    const res = await fetch(`${this.baseUrl}/api/embeddings`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ model: embedModel, prompt: text }),
      signal:  AbortSignal.timeout(30_000),
    })

    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`[OllamaAdapter/embeddings] error ${res.status}: ${txt}`)
    }

    const data = await res.json() as OllamaEmbedResponse
    return data.embedding
  }

  // ── health() — liveness check ─────────────────────────────────────────────

  async health(): Promise<{ status: 'ok' | 'offline'; latencyMs: number; modelCount: number; error?: string }> {
    const t0 = Date.now()
    try {
      const ok = await this.isAvailable()
      return { status: ok ? 'ok' : 'offline', latencyMs: Date.now() - t0, modelCount: this.models.length }
    } catch (e) {
      return { status: 'offline', latencyMs: Date.now() - t0, modelCount: 0, error: String(e) }
    }
  }
}
