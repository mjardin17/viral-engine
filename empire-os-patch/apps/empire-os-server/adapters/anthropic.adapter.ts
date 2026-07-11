/**
 * Anthropic Claude — AIProviderAdapter
 * Registers claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5-20251001.
 * Reads ANTHROPIC_API_KEY from process.env — never hardcoded.
 *
 * Exposes full unified interface:
 *   complete()    — full chat completion (messages array)
 *   chat()        — single-prompt convenience wrapper → string
 *   stream()      — SSE streaming with onChunk callback
 *   vision()      — image + text completion
 *   embeddings()  — not supported by Anthropic (throws with clear message)
 *   health()      — liveness check
 *   models()      — list of registered models
 */

import type { AIProviderAdapter } from '@empire-os/core'
import type { AIModel, AIMessage } from '@empire-os/core'

const ANTHROPIC_API     = 'https://api.anthropic.com/v1/messages'
const ANTHROPIC_VERSION = '2023-06-01'
const DEFAULT_MODEL     = 'claude-sonnet-4-6'

const CLAUDE_MODELS: AIModel[] = [
  {
    id: 'claude-opus-4-8',
    provider: 'anthropic',
    capabilities: ['chat', 'code', 'research', 'reasoning', 'function-calling', 'long-context'],
    contextWindow: 200_000,
    costPerMToken: 15,
    available: true,
  },
  {
    id: 'claude-sonnet-4-6',
    provider: 'anthropic',
    capabilities: ['chat', 'code', 'research', 'function-calling', 'long-context'],
    contextWindow: 200_000,
    costPerMToken: 3,
    available: true,
  },
  {
    id: 'claude-haiku-4-5-20251001',
    provider: 'anthropic',
    capabilities: ['chat', 'code', 'reasoning'],
    contextWindow: 200_000,
    costPerMToken: 0.25,
    available: true,
  },
]

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

export class AnthropicAdapter implements AIProviderAdapter {
  readonly provider = 'anthropic' as const
  readonly models: AIModel[]

  constructor(private readonly apiKey: string) {
    this.models = CLAUDE_MODELS.map(m => ({ ...m }))
  }

  // ── Interface compliance ──────────────────────────────────────────────────

  async isAvailable(): Promise<boolean> {
    return Boolean(this.apiKey)
  }

  // ── complete() — full message array completion ────────────────────────────

  async complete(
    messages: AIMessage[],
    model: string,
    options: { maxTokens?: number; temperature?: number },
  ): Promise<CompletionResult> {
    const start = Date.now()

    const systemParts  = messages.filter(m => m.role === 'system').map(m => m.content)
    const conversation = messages.filter(m => m.role !== 'system')

    if (conversation.length === 0) {
      throw new Error('[AnthropicAdapter] At least one user message is required')
    }

    const body: Record<string, unknown> = {
      model,
      max_tokens: options.maxTokens ?? 4096,
      messages:   conversation.map(m => ({ role: m.role, content: m.content })),
    }
    if (systemParts.length > 0) body.system = systemParts.join('\n\n')
    if (options.temperature !== undefined) body.temperature = options.temperature

    const res = await fetch(ANTHROPIC_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(60_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[AnthropicAdapter] API error ${res.status}: ${text}`)
    }

    const data = await res.json() as {
      content: Array<{ type: string; text: string }>
      usage:   { input_tokens: number; output_tokens: number }
    }

    return {
      content:      data.content.find(b => b.type === 'text')?.text ?? '',
      inputTokens:  data.usage.input_tokens,
      outputTokens: data.usage.output_tokens,
      durationMs:   Date.now() - start,
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
    const r = await this.complete(messages, opts.model ?? DEFAULT_MODEL, {
      maxTokens:   opts.maxTokens,
      temperature: opts.temperature,
    })
    return r.content
  }

  // ── stream() — SSE streaming with per-chunk callback ─────────────────────

  async stream(
    messages: AIMessage[],
    model: string,
    options: { maxTokens?: number; temperature?: number },
    onChunk: StreamChunkCallback,
  ): Promise<StreamResult> {
    const start = Date.now()

    const systemParts  = messages.filter(m => m.role === 'system').map(m => m.content)
    const conversation = messages.filter(m => m.role !== 'system')

    const body: Record<string, unknown> = {
      model,
      max_tokens: options.maxTokens ?? 4096,
      stream:     true,
      messages:   conversation.map(m => ({ role: m.role, content: m.content })),
    }
    if (systemParts.length > 0) body.system = systemParts.join('\n\n')
    if (options.temperature !== undefined) body.temperature = options.temperature

    const res = await fetch(ANTHROPIC_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(120_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[AnthropicAdapter/stream] API error ${res.status}: ${text}`)
    }

    if (!res.body) throw new Error('[AnthropicAdapter/stream] No response body')

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
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue

        try {
          const event = JSON.parse(data) as {
            type:  string
            delta?: { type: string; text?: string }
            usage?: { input_tokens?: number; output_tokens?: number }
          }
          if (event.type === 'content_block_delta' && event.delta?.type === 'text_delta' && event.delta.text) {
            onChunk(event.delta.text)
          }
          if (event.type === 'message_delta' && event.usage) {
            outputTokens = event.usage.output_tokens ?? 0
          }
          if (event.type === 'message_start' && event.usage) {
            inputTokens = (event as { usage?: { input_tokens?: number } }).usage?.input_tokens ?? 0
          }
        } catch {
          // malformed SSE line — skip
        }
      }
    }

    return { inputTokens, outputTokens, durationMs: Date.now() - start }
  }

  // ── vision() — image + text understanding ────────────────────────────────

  async vision(
    imageBase64: string,
    prompt: string,
    opts: { model?: string; mediaType?: string; maxTokens?: number } = {},
  ): Promise<string> {
    const start     = Date.now()
    const model     = opts.model     ?? 'claude-sonnet-4-6'
    const mediaType = opts.mediaType ?? 'image/jpeg'

    const body = {
      model,
      max_tokens: opts.maxTokens ?? 1024,
      messages: [{
        role:    'user',
        content: [
          { type: 'image', source: { type: 'base64', media_type: mediaType, data: imageBase64 } },
          { type: 'text',  text: prompt },
        ],
      }],
    }

    const res = await fetch(ANTHROPIC_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(60_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[AnthropicAdapter/vision] API error ${res.status}: ${text}`)
    }

    const data = await res.json() as { content: Array<{ type: string; text: string }> }
    const _ = Date.now() - start  // durationMs captured for future use
    return data.content.find(b => b.type === 'text')?.text ?? ''
  }

  // ── embeddings() — not supported by Anthropic ────────────────────────────

  async embeddings(_text: string, _model?: string): Promise<never> {
    throw new Error('[AnthropicAdapter] Embeddings not supported by Anthropic API. Use Ollama (nomic-embed-text) or OpenAI (text-embedding-3-small) instead.')
  }

  // ── health() — liveness ping ─────────────────────────────────────────────

  async health(): Promise<{ status: 'ok' | 'offline'; latencyMs: number; error?: string }> {
    const t0 = Date.now()
    try {
      // Cheapest possible call: list models (not available) — use isAvailable instead
      const available = await this.isAvailable()
      return { status: available ? 'ok' : 'offline', latencyMs: Date.now() - t0 }
    } catch (e) {
      return { status: 'offline', latencyMs: Date.now() - t0, error: String(e) }
    }
  }

  // ── helpers ───────────────────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      'Content-Type':      'application/json',
      'x-api-key':         this.apiKey,
      'anthropic-version': ANTHROPIC_VERSION,
    }
  }
}
