/**
 * Google Gemini — AIProviderAdapter
 * Registers gemini-1.5-pro and gemini-1.5-flash.
 * Reads GOOGLE_API_KEY from process.env — never hardcoded.
 *
 * Exposes full unified interface:
 *   complete()    — full chat completion (messages array)
 *   chat()        — single-prompt convenience wrapper → string
 *   stream()      — SSE streaming with onChunk callback
 *   vision()      — image + text completion (inline base64)
 *   embeddings()  — text embeddings via text-embedding-004
 *   health()      — liveness check
 *   models()      — list of registered models
 */

import type { AIProviderAdapter } from '@empire-os/core'
import type { AIModel, AIMessage } from '@empire-os/core'

const GEMINI_BASE      = 'https://generativelanguage.googleapis.com/v1beta/models'
const DEFAULT_MODEL    = 'gemini-1.5-flash'
const EMBED_MODEL      = 'text-embedding-004'

const GEMINI_MODELS: AIModel[] = [
  {
    id:            'gemini-1.5-pro',
    provider:      'google',
    capabilities:  ['chat', 'research', 'long-context', 'vision', 'embeddings'],
    contextWindow: 1_000_000,
    costPerMToken: 3.5,
    available:     true,
  },
  {
    id:            'gemini-1.5-flash',
    provider:      'google',
    capabilities:  ['chat', 'research', 'long-context', 'vision'],
    contextWindow: 1_000_000,
    costPerMToken: 0.075,
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

export class GeminiAdapter implements AIProviderAdapter {
  readonly provider = 'google' as const
  readonly models: AIModel[]

  constructor(private readonly apiKey: string) {
    this.models = GEMINI_MODELS.map(m => ({ ...m }))
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

    const contents = conversation.map(m => ({
      role:  m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }))

    const body: Record<string, unknown> = {
      contents,
      generationConfig: {
        maxOutputTokens: options.maxTokens ?? 4096,
        ...(options.temperature !== undefined ? { temperature: options.temperature } : {}),
      },
    }
    if (systemParts.length > 0) {
      body.systemInstruction = { parts: [{ text: systemParts.join('\n\n') }] }
    }

    const url = `${GEMINI_BASE}/${model}:generateContent?key=${this.apiKey}`
    const res = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(60_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[GeminiAdapter] API error ${res.status}: ${text}`)
    }

    const data = await res.json() as {
      candidates:    Array<{ content: { parts: Array<{ text: string }> } }>
      usageMetadata?: { promptTokenCount: number; candidatesTokenCount: number }
    }

    return {
      content:      data.candidates[0]?.content?.parts[0]?.text ?? '',
      inputTokens:  data.usageMetadata?.promptTokenCount   ?? 0,
      outputTokens: data.usageMetadata?.candidatesTokenCount ?? 0,
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

    const contents = conversation.map(m => ({
      role:  m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }))

    const body: Record<string, unknown> = {
      contents,
      generationConfig: {
        maxOutputTokens: options.maxTokens ?? 4096,
        ...(options.temperature !== undefined ? { temperature: options.temperature } : {}),
      },
    }
    if (systemParts.length > 0) {
      body.systemInstruction = { parts: [{ text: systemParts.join('\n\n') }] }
    }

    const url = `${GEMINI_BASE}/${model}:streamGenerateContent?key=${this.apiKey}&alt=sse`
    const res = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(120_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[GeminiAdapter/stream] API error ${res.status}: ${text}`)
    }

    if (!res.body) throw new Error('[GeminiAdapter/stream] No response body')

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
        if (!data) continue

        try {
          const event = JSON.parse(data) as {
            candidates?:    Array<{ content?: { parts: Array<{ text?: string }> } }>
            usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number }
          }
          const text = event.candidates?.[0]?.content?.parts?.[0]?.text
          if (text) onChunk(text)
          if (event.usageMetadata) {
            inputTokens  = event.usageMetadata.promptTokenCount     ?? inputTokens
            outputTokens = event.usageMetadata.candidatesTokenCount ?? outputTokens
          }
        } catch {
          // malformed SSE chunk — skip
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
    const model     = opts.model     ?? DEFAULT_MODEL
    const mediaType = opts.mediaType ?? 'image/jpeg'

    const body = {
      contents: [{
        parts: [
          { inline_data: { mime_type: mediaType, data: imageBase64 } },
          { text: prompt },
        ],
      }],
      generationConfig: { maxOutputTokens: opts.maxTokens ?? 1024 },
    }

    const url = `${GEMINI_BASE}/${model}:generateContent?key=${this.apiKey}`
    const res = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(60_000),
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(`[GeminiAdapter/vision] API error ${res.status}: ${text}`)
    }

    const data = await res.json() as {
      candidates: Array<{ content: { parts: Array<{ text: string }> } }>
    }
    return data.candidates[0]?.content?.parts[0]?.text ?? ''
  }

  // ── embeddings() — dense vector embeddings ────────────────────────────────

  async embeddings(text: string, model = EMBED_MODEL): Promise<number[]> {
    const url  = `${GEMINI_BASE}/${model}:embedContent?key=${this.apiKey}`
    const body = { content: { parts: [{ text }] } }

    const res = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(30_000),
    })

    if (!res.ok) {
      const txt = await res.text()
      throw new Error(`[GeminiAdapter/embeddings] API error ${res.status}: ${txt}`)
    }

    const data = await res.json() as { embedding: { values: number[] } }
    return data.embedding.values
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
}
