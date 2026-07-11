/**
 * OpenAI — AIProviderAdapter
 * Registers GPT-4o and GPT-4o-mini.
 * Reads OPENAI_API_KEY from process.env — never hardcoded.
 *
 * Exposes full unified interface:
 *   complete()    — full chat completion (messages array)
 *   chat()        — single-prompt convenience wrapper → string
 *   stream()      — SSE streaming with onChunk callback
 *   vision()      — image + text via gpt-4o vision
 *   embeddings()  — dense vector embeddings via text-embedding-3-small
 *   health()      — liveness check
 *   models()      — list of registered models
 */

import type { AIProviderAdapter } from '@empire-os/core'
import type { AIModel, AIMessage } from '@empire-os/core'

const OPENAI_CHAT_API   = 'https://api.openai.com/v1/chat/completions'
const OPENAI_EMBED_API  = 'https://api.openai.com/v1/embeddings'
const DEFAULT_MODEL     = 'gpt-4o-mini'
const DEFAULT_EMBED_MDL = 'text-embedding-3-small'

const OPENAI_MODELS: AIModel[] = [
  {
    id:            'gpt-4o',
    provider:      'openai',
    capabilities:  ['chat', 'code', 'vision', 'function-calling', 'long-context', 'reasoning', 'embeddings'],
    contextWindow: 128_000,
    costPerMToken: 5,
    available:     true,
  },
  {
    id:            'gpt-4o-mini',
    provider:      'openai',
    capabilities:  ['chat', 'code', 'vision', 'function-calling', 'embeddings'],
    contextWindow: 128_000,
    costPerMToken: 0.15,
    available:     true,
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

export class OpenAIAdapter implements AIProviderAdapter {
  readonly provider = 'openai' as const
  readonly models:   AIModel[]

  constructor(private readonly apiKey: string) {
    this.models = OPENAI_MODELS.map(m => ({ ...m }))
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

    const body = {
      model,
      messages:    messages.map(m => ({ role: m.role, content: m.content })),
      max_tokens:  options.maxTokens  ?? 4_096,
      temperature: options.temperature ?? 0.7,
    }

    const res = await fetch(OPENAI_CHAT_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(60_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[OpenAIAdapter] API error ${res.status}: ${text}`)
    }

    const data = await res.json() as {
      choices: Array<{ message: { content: string } }>
      usage:   { prompt_tokens: number; completion_tokens: number }
    }

    return {
      content:      data.choices[0]?.message?.content ?? '',
      inputTokens:  data.usage.prompt_tokens,
      outputTokens: data.usage.completion_tokens,
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

    const body = {
      model,
      messages:           messages.map(m => ({ role: m.role, content: m.content })),
      max_tokens:         options.maxTokens  ?? 4_096,
      temperature:        options.temperature ?? 0.7,
      stream:             true,
      stream_options:     { include_usage: true },
    }

    const res = await fetch(OPENAI_CHAT_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(120_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[OpenAIAdapter/stream] API error ${res.status}: ${text}`)
    }

    if (!res.body) throw new Error('[OpenAIAdapter/stream] No response body')

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
          const chunk = JSON.parse(data) as {
            choices?: Array<{ delta?: { content?: string } }>
            usage?:   { prompt_tokens?: number; completion_tokens?: number }
          }
          const content = chunk.choices?.[0]?.delta?.content
          if (content) onChunk(content)
          if (chunk.usage) {
            inputTokens  = chunk.usage.prompt_tokens     ?? inputTokens
            outputTokens = chunk.usage.completion_tokens ?? outputTokens
          }
        } catch {
          // malformed SSE line — skip
        }
      }
    }

    return { inputTokens, outputTokens, durationMs: Date.now() - start }
  }

  // ── vision() — image + text via GPT-4o vision ────────────────────────────

  async vision(
    imageBase64: string,
    prompt: string,
    opts: { model?: string; mediaType?: string; maxTokens?: number } = {},
  ): Promise<string> {
    const model     = opts.model     ?? 'gpt-4o'
    const mediaType = opts.mediaType ?? 'image/jpeg'
    const dataUrl   = `data:${mediaType};base64,${imageBase64}`

    const body = {
      model,
      max_tokens: opts.maxTokens ?? 1024,
      messages: [{
        role:    'user',
        content: [
          { type: 'image_url', image_url: { url: dataUrl } },
          { type: 'text',      text: prompt },
        ],
      }],
    }

    const res = await fetch(OPENAI_CHAT_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(60_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[OpenAIAdapter/vision] API error ${res.status}: ${text}`)
    }

    const data = await res.json() as {
      choices: Array<{ message: { content: string } }>
    }
    return data.choices[0]?.message?.content ?? ''
  }

  // ── embeddings() — dense vector embeddings ────────────────────────────────

  async embeddings(text: string, model = DEFAULT_EMBED_MDL): Promise<number[]> {
    const body = { input: text, model }

    const res = await fetch(OPENAI_EMBED_API, {
      method:  'POST',
      headers: this.headers(),
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(30_000),
    })

    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`[OpenAIAdapter/embeddings] API error ${res.status}: ${txt}`)
    }

    const data = await res.json() as { data: Array<{ embedding: number[] }> }
    return data.data[0]?.embedding ?? []
  }

  // ── health() — liveness check ─────────────────────────────────────────────

  async health(): Promise<{ status: 'ok' | 'offline'; latencyMs: number; error?: string }> {
    const t0 = Date.now()
    try {
      const available = await this.isAvailable()
      return { status: available ? 'ok' : 'offline', latencyMs: Date.now() - t0 }
    } catch (e) {
      return { status: 'offline', latencyMs: Date.now() - t0, error: String(e) }
    }
  }

  // ── helpers ───────────────────────────────────────────────────────────────

  private headers(): Record<string, string> {
    return {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${this.apiKey}`,
    }
  }
}
