/**
 * Video Factory — Provider Adapters
 *
 * Adapters for all external media generation services:
 *   Image: Imagen 3 (Google), Flux Pro (Black Forest Labs), DALL-E 3 (OpenAI)
 *   Video: Veo 2/3 (Google), Runway Gen-3 (Runway), Kling (Kuaishou), Luma Dream Machine
 *   Audio: ElevenLabs (TTS), Suno (music AI)
 *
 * All adapters return a ProviderResult with: success, assetUrl, cost, provider, metadata.
 * Adapters read keys from environment variables — never hardcoded.
 * All calls are non-blocking; generation is queued and polled.
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ProviderResult {
  success: boolean
  provider: string
  assetType: 'image' | 'video' | 'audio'
  assetUrl: string | null
  assetPath: string | null
  costUsd: number
  durationMs: number
  qualityScore: number | null
  metadata: Record<string, unknown>
  error: string | null
}

export interface ImageGenerationParams {
  prompt: string
  negativePrompt?: string
  width: number
  height: number
  style?: 'photorealistic' | 'painterly' | 'cinematic' | 'illustrated' | 'watercolor'
  numImages?: number
  seed?: number
  model?: string
}

export interface VideoGenerationParams {
  prompt: string
  imageUrl?: string     // Starting frame (image-to-video)
  duration: number      // seconds (3-8 recommended)
  fps?: 24 | 30 | 60
  width: number
  height: number
  motion?: 'low' | 'medium' | 'high'
  cameraMovement?: string
  model?: string
}

export interface TTSParams {
  text: string
  voiceId: string
  stability?: number
  similarityBoost?: number
  style?: number
  useSpeakerBoost?: boolean
  outputFormat?: 'mp3_44100_128' | 'pcm_44100' | 'wav_44100'
}

export interface MusicParams {
  prompt: string
  duration: number      // seconds
  genre?: string
  tempo?: string
  mood?: string
}

// ── Helper ────────────────────────────────────────────────────────────────────

function resultError(provider: string, assetType: ProviderResult['assetType'], error: string, durationMs: number): ProviderResult {
  return { success: false, provider, assetType, assetUrl: null, assetPath: null, costUsd: 0, durationMs, qualityScore: null, metadata: {}, error }
}

function resultOk(provider: string, assetType: ProviderResult['assetType'], assetUrl: string, costUsd: number, durationMs: number, metadata: Record<string, unknown> = {}): ProviderResult {
  return { success: true, provider, assetType, assetUrl, assetPath: null, costUsd, durationMs, qualityScore: null, metadata, error: null }
}

// ── Imagen 3 (Google AI Studio / Vertex AI) ──────────────────────────────────

export const ImagenProvider = {
  name: 'imagen-3',
  available(): boolean {
    return !!(process.env.GOOGLE_API_KEY || process.env.GOOGLE_VERTEX_PROJECT)
  },

  async generateImage(params: ImageGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.GOOGLE_API_KEY

    if (!apiKey) {
      return resultError('imagen-3', 'image', 'GOOGLE_API_KEY not configured', Date.now() - start)
    }

    try {
      const model = params.model ?? 'imagen-3.0-generate-001'
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateImages?key=${apiKey}`

      const body = {
        prompt: { text: params.prompt },
        imageGenerationConfig: {
          numberOfImages: params.numImages ?? 1,
          width: params.width,
          height: params.height,
          seed: params.seed,
        },
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('imagen-3', 'image', `API error ${res.status}: ${err}`, Date.now() - start)
      }

      const data = await res.json() as { generatedImages?: Array<{ bytesBase64Encoded?: string }> }
      const imageData = data.generatedImages?.[0]?.bytesBase64Encoded
      if (!imageData) {
        return resultError('imagen-3', 'image', 'No image data returned', Date.now() - start)
      }

      // Return as data URI (caller handles saving to disk)
      const dataUri = `data:image/png;base64,${imageData}`
      const cost = 0.0035  // ~$0.0035 per image for Imagen 3
      return resultOk('imagen-3', 'image', dataUri, cost, Date.now() - start, { model })
    } catch (e) {
      return resultError('imagen-3', 'image', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(params: ImageGenerationParams): number {
    return 0.0035 * (params.numImages ?? 1)
  },
}

// ── Flux Pro (Black Forest Labs / Replicate) ──────────────────────────────────

export const FluxProvider = {
  name: 'flux-pro',
  available(): boolean {
    return !!(process.env.REPLICATE_API_KEY || process.env.FAL_API_KEY || process.env.BFL_API_KEY)
  },

  async generateImage(params: ImageGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.REPLICATE_API_KEY

    if (!apiKey) {
      return resultError('flux-pro', 'image', 'REPLICATE_API_KEY not configured', Date.now() - start)
    }

    try {
      // Use Replicate API for Flux Pro
      const createRes = await fetch('https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
          'Prefer': 'wait',
        },
        body: JSON.stringify({
          input: {
            prompt: params.prompt,
            negative_prompt: params.negativePrompt ?? '',
            width: params.width,
            height: params.height,
            num_outputs: params.numImages ?? 1,
            seed: params.seed,
            output_format: 'png',
          },
        }),
      })

      if (!createRes.ok) {
        const err = await createRes.text()
        return resultError('flux-pro', 'image', `API error ${createRes.status}: ${err}`, Date.now() - start)
      }

      const prediction = await createRes.json() as { output?: string | string[]; error?: string; status?: string }

      if (prediction.error) {
        return resultError('flux-pro', 'image', prediction.error, Date.now() - start)
      }

      const output = Array.isArray(prediction.output) ? prediction.output[0] : prediction.output
      if (!output) {
        return resultError('flux-pro', 'image', 'No output from Flux Pro', Date.now() - start)
      }

      const cost = 0.055  // Flux 1.1 Pro pricing
      return resultOk('flux-pro', 'image', output, cost, Date.now() - start, { model: 'flux-1.1-pro' })
    } catch (e) {
      return resultError('flux-pro', 'image', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(_params: ImageGenerationParams): number {
    return 0.055
  },
}

// ── DALL-E 3 (OpenAI) — Fallback image provider ──────────────────────────────

export const DalleProvider = {
  name: 'dall-e-3',
  available(): boolean {
    return !!process.env.OPENAI_API_KEY
  },

  async generateImage(params: ImageGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.OPENAI_API_KEY

    if (!apiKey) {
      return resultError('dall-e-3', 'image', 'OPENAI_API_KEY not configured', Date.now() - start)
    }

    try {
      const size = `${params.width}x${params.height}` as '1024x1024' | '1792x1024' | '1024x1792'

      const res = await fetch('https://api.openai.com/v1/images/generations', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'dall-e-3',
          prompt: params.prompt,
          n: 1,
          size: ['1024x1024', '1792x1024', '1024x1792'].includes(size) ? size : '1024x1024',
          quality: 'hd',
          style: 'vivid',
        }),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('dall-e-3', 'image', `API error ${res.status}: ${err}`, Date.now() - start)
      }

      const data = await res.json() as { data?: Array<{ url?: string }> }
      const url = data.data?.[0]?.url
      if (!url) return resultError('dall-e-3', 'image', 'No URL returned', Date.now() - start)

      const cost = 0.08  // DALL-E 3 HD
      return resultOk('dall-e-3', 'image', url, cost, Date.now() - start, { model: 'dall-e-3', quality: 'hd' })
    } catch (e) {
      return resultError('dall-e-3', 'image', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(_params: ImageGenerationParams): number {
    return 0.08
  },
}

// ── Veo (Google Vertex AI / AI Studio) ───────────────────────────────────────

export const VeoProvider = {
  name: 'veo-2',
  available(): boolean {
    return !!(process.env.GOOGLE_API_KEY || process.env.GOOGLE_VERTEX_PROJECT)
  },

  async generateVideo(params: VideoGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.GOOGLE_API_KEY

    if (!apiKey) {
      return resultError('veo-2', 'video', 'GOOGLE_API_KEY not configured — add to .env', Date.now() - start)
    }

    try {
      // Veo via AI Studio API (preview)
      const url = `https://generativelanguage.googleapis.com/v1beta/models/veo-2.0-generate-001:generateVideos?key=${apiKey}`

      const input: Record<string, unknown> = {
        prompt: params.prompt,
        generationConfig: {
          durationSeconds: params.duration,
          aspectRatio: params.width > params.height ? '16:9' : params.width < params.height ? '9:16' : '1:1',
          resolution: '1080p',
        },
      }

      if (params.imageUrl) {
        input.image = { imageUrl: params.imageUrl }
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('veo-2', 'video', `Veo API error ${res.status}: ${err}`, Date.now() - start)
      }

      const data = await res.json() as { name?: string; done?: boolean; response?: { generatedVideos?: Array<{ video?: { uri?: string } }> } }

      // Veo returns an operation — poll for completion
      if (data.name && !data.done) {
        // Return the operation name — caller should poll
        return resultOk('veo-2', 'video', '', 0.15 * params.duration, Date.now() - start, {
          operationName: data.name,
          status: 'pending',
          pollUrl: `https://generativelanguage.googleapis.com/v1beta/${data.name}?key=${apiKey}`,
        })
      }

      const videoUri = data.response?.generatedVideos?.[0]?.video?.uri ?? ''
      const cost = 0.15 * params.duration  // Estimated
      return resultOk('veo-2', 'video', videoUri, cost, Date.now() - start)
    } catch (e) {
      return resultError('veo-2', 'video', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(params: VideoGenerationParams): number {
    return 0.15 * params.duration
  },
}

// ── Runway Gen-3 Alpha ────────────────────────────────────────────────────────

export const RunwayProvider = {
  name: 'runway-gen3',
  available(): boolean {
    return !!process.env.RUNWAY_API_KEY
  },

  async generateVideo(params: VideoGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.RUNWAY_API_KEY

    if (!apiKey) {
      return resultError('runway-gen3', 'video', 'RUNWAY_API_KEY not configured', Date.now() - start)
    }

    try {
      const body: Record<string, unknown> = {
        model: 'gen3a_turbo',
        promptText: params.prompt,
        duration: params.duration > 5 ? 10 : 5,  // Runway supports 5s or 10s
        ratio: params.width > params.height ? '1280:768' : '768:1280',
        watermark: false,
      }

      if (params.imageUrl) {
        body.promptImage = params.imageUrl
      }

      const res = await fetch('https://api.dev.runwayml.com/v1/image_to_video', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
          'X-Runway-Version': '2024-11-06',
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('runway-gen3', 'video', `Runway API error ${res.status}: ${err}`, Date.now() - start)
      }

      const data = await res.json() as { id?: string; status?: string; output?: string[] }
      const taskId = data.id

      if (!taskId) {
        return resultError('runway-gen3', 'video', 'No task ID returned', Date.now() - start)
      }

      // Return task ID for polling
      const cost = 0.25 * params.duration
      return resultOk('runway-gen3', 'video', '', cost, Date.now() - start, {
        taskId,
        status: 'pending',
        pollPath: `/v1/tasks/${taskId}`,
      })
    } catch (e) {
      return resultError('runway-gen3', 'video', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(params: VideoGenerationParams): number {
    const seconds = params.duration > 5 ? 10 : 5
    return seconds * 0.25  // Rough Runway pricing
  },
}

// ── Kling (Kuaishou) ──────────────────────────────────────────────────────────

export const KlingProvider = {
  name: 'kling',
  available(): boolean {
    return !!process.env.KLING_API_KEY
  },

  async generateVideo(params: VideoGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.KLING_API_KEY

    if (!apiKey) {
      return resultError('kling', 'video', 'KLING_API_KEY not configured', Date.now() - start)
    }

    try {
      const body: Record<string, unknown> = {
        model: 'kling-v1-5',
        prompt: params.prompt,
        negative_prompt: '',
        cfg_scale: 0.5,
        mode: params.motion === 'low' ? 'std' : 'pro',
        duration: params.duration <= 5 ? '5' : '10',
        aspect_ratio: params.width > params.height ? '16:9' : '9:16',
      }

      if (params.imageUrl) {
        body.image = params.imageUrl
        delete body.aspect_ratio  // Not used for image-to-video
      }

      const res = await fetch('https://api.klingai.com/v1/videos/image2video', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('kling', 'video', `Kling API error ${res.status}: ${err}`, Date.now() - start)
      }

      const data = await res.json() as { data?: { task_id?: string; task_status?: string } }
      const taskId = data.data?.task_id

      if (!taskId) {
        return resultError('kling', 'video', 'No task ID', Date.now() - start)
      }

      const cost = 0.18 * (params.duration <= 5 ? 5 : 10)
      return resultOk('kling', 'video', '', cost, Date.now() - start, { taskId, status: 'pending' })
    } catch (e) {
      return resultError('kling', 'video', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(params: VideoGenerationParams): number {
    return 0.18 * (params.duration <= 5 ? 5 : 10)
  },
}

// ── Luma Dream Machine ────────────────────────────────────────────────────────

export const LumaProvider = {
  name: 'luma-dream-machine',
  available(): boolean {
    return !!process.env.LUMA_API_KEY
  },

  async generateVideo(params: VideoGenerationParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.LUMA_API_KEY

    if (!apiKey) {
      return resultError('luma-dream-machine', 'video', 'LUMA_API_KEY not configured', Date.now() - start)
    }

    try {
      const body: Record<string, unknown> = {
        prompt: params.prompt,
        aspect_ratio: params.width > params.height ? '16:9' : '9:16',
        loop: false,
      }

      if (params.imageUrl) {
        body.keyframes = {
          frame0: { type: 'image', url: params.imageUrl },
        }
      }

      const res = await fetch('https://api.lumalabs.ai/dream-machine/v1/generations', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('luma-dream-machine', 'video', `Luma API error ${res.status}: ${err}`, Date.now() - start)
      }

      const data = await res.json() as { id?: string; state?: string; video?: { url?: string } }
      const genId = data.id

      if (!genId) {
        return resultError('luma-dream-machine', 'video', 'No generation ID', Date.now() - start)
      }

      if (data.state === 'completed' && data.video?.url) {
        return resultOk('luma-dream-machine', 'video', data.video.url, 0.10, Date.now() - start)
      }

      return resultOk('luma-dream-machine', 'video', '', 0.10, Date.now() - start, {
        generationId: genId,
        status: 'pending',
      })
    } catch (e) {
      return resultError('luma-dream-machine', 'video', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(_params: VideoGenerationParams): number {
    return 0.10
  },
}

// ── ElevenLabs TTS ────────────────────────────────────────────────────────────

export const ElevenLabsProvider = {
  name: 'elevenlabs',
  available(): boolean {
    return !!process.env.ELEVENLABS_API_KEY
  },

  /** Default voice IDs per channel */
  VOICE_IDS: {
    'gods-glory': process.env.ELEVENLABS_VOICE_GG ?? 'pNInz6obpgDQGcFmaJgB',        // "Adam" (placeholder)
    'machine-learning': process.env.ELEVENLABS_VOICE_ML ?? 'ErXwobaYiN019PkySvjV',  // "Antoni" (placeholder)
    'little-olympus': process.env.ELEVENLABS_VOICE_LO ?? 'EXAVITQu4vr4xnSDxMaL',   // "Bella" (placeholder)
  } as Record<string, string>,

  async generateSpeech(params: TTSParams): Promise<ProviderResult> {
    const start = Date.now()
    const apiKey = process.env.ELEVENLABS_API_KEY

    if (!apiKey) {
      return resultError('elevenlabs', 'audio', 'ELEVENLABS_API_KEY not configured', Date.now() - start)
    }

    try {
      const url = `https://api.elevenlabs.io/v1/text-to-speech/${params.voiceId}`

      const body = {
        text: params.text,
        model_id: 'eleven_turbo_v2_5',
        voice_settings: {
          stability: params.stability ?? 0.65,
          similarity_boost: params.similarityBoost ?? 0.85,
          style: params.style ?? 0.4,
          use_speaker_boost: params.useSpeakerBoost ?? true,
        },
        output_format: params.outputFormat ?? 'mp3_44100_128',
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'xi-api-key': apiKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.text()
        return resultError('elevenlabs', 'audio', `ElevenLabs error ${res.status}: ${err}`, Date.now() - start)
      }

      // Audio data as ArrayBuffer — caller saves to disk
      const audioBuffer = await res.arrayBuffer()
      const base64Audio = Buffer.from(audioBuffer).toString('base64')
      const dataUri = `data:audio/mpeg;base64,${base64Audio}`

      // Cost: ~$0.30 per 1000 chars with Turbo v2
      const cost = (params.text.length / 1000) * 0.30

      return resultOk('elevenlabs', 'audio', dataUri, cost, Date.now() - start, {
        voiceId: params.voiceId,
        charCount: params.text.length,
        model: 'eleven_turbo_v2_5',
      })
    } catch (e) {
      return resultError('elevenlabs', 'audio', String(e), Date.now() - start)
    }
  },

  estimatedCostUsd(params: TTSParams): number {
    return (params.text.length / 1000) * 0.30
  },
}

// ── Suno (AI Music) — via unofficial API ─────────────────────────────────────

export const SunoProvider = {
  name: 'suno',
  available(): boolean {
    return !!process.env.SUNO_COOKIE || !!process.env.SUNO_API_KEY
  },

  async generateMusic(params: MusicParams): Promise<ProviderResult> {
    const start = Date.now()
    // Suno requires session cookie — not an official API yet
    // Returns a stub until official API is available
    return resultError('suno', 'audio', 'Suno official API pending — use Epidemic Sound or Artlist library for now', Date.now() - start)
  },

  estimatedCostUsd(_params: MusicParams): number {
    return 0
  },
}

// ── Provider Router ───────────────────────────────────────────────────────────

export interface ProviderRouterConfig {
  imageProvider: 'imagen-3' | 'flux-pro' | 'dall-e-3' | 'auto'
  videoProvider: 'veo-2' | 'runway-gen3' | 'kling' | 'luma-dream-machine' | 'auto'
  audioProvider: 'elevenlabs' | 'auto'
}

export async function routeImageGeneration(
  params: ImageGenerationParams,
  config: ProviderRouterConfig = { imageProvider: 'auto', videoProvider: 'auto', audioProvider: 'auto' }
): Promise<ProviderResult> {
  if (config.imageProvider === 'imagen-3' || (config.imageProvider === 'auto' && ImagenProvider.available())) {
    return ImagenProvider.generateImage(params)
  }
  if (config.imageProvider === 'flux-pro' || (config.imageProvider === 'auto' && FluxProvider.available())) {
    return FluxProvider.generateImage(params)
  }
  if (config.imageProvider === 'dall-e-3' || (config.imageProvider === 'auto' && DalleProvider.available())) {
    return DalleProvider.generateImage(params)
  }
  return resultError('none', 'image', 'No image provider configured. Add GOOGLE_API_KEY, REPLICATE_API_KEY, or OPENAI_API_KEY to .env', 0)
}

export async function routeVideoGeneration(
  params: VideoGenerationParams,
  config: ProviderRouterConfig = { imageProvider: 'auto', videoProvider: 'auto', audioProvider: 'auto' }
): Promise<ProviderResult> {
  if (config.videoProvider === 'veo-2' || (config.videoProvider === 'auto' && VeoProvider.available())) {
    return VeoProvider.generateVideo(params)
  }
  if (config.videoProvider === 'runway-gen3' || (config.videoProvider === 'auto' && RunwayProvider.available())) {
    return RunwayProvider.generateVideo(params)
  }
  if (config.videoProvider === 'kling' || (config.videoProvider === 'auto' && KlingProvider.available())) {
    return KlingProvider.generateVideo(params)
  }
  if (config.videoProvider === 'luma-dream-machine' || (config.videoProvider === 'auto' && LumaProvider.available())) {
    return LumaProvider.generateVideo(params)
  }
  return resultError('none', 'video', 'No video provider configured. Add GOOGLE_API_KEY, RUNWAY_API_KEY, KLING_API_KEY, or LUMA_API_KEY to .env', 0)
}

export async function routeTTS(
  params: TTSParams,
  _config: ProviderRouterConfig = { imageProvider: 'auto', videoProvider: 'auto', audioProvider: 'auto' }
): Promise<ProviderResult> {
  if (ElevenLabsProvider.available()) {
    return ElevenLabsProvider.generateSpeech(params)
  }
  return resultError('none', 'audio', 'ELEVENLABS_API_KEY not configured', 0)
}

export function getProviderStatus(): Record<string, { name: string; available: boolean; envVar: string }> {
  return {
    'imagen-3':          { name: 'Imagen 3 (Google)',         available: ImagenProvider.available(),       envVar: 'GOOGLE_API_KEY' },
    'flux-pro':          { name: 'Flux Pro (Replicate)',       available: FluxProvider.available(),         envVar: 'REPLICATE_API_KEY' },
    'dall-e-3':          { name: 'DALL-E 3 (OpenAI)',          available: DalleProvider.available(),        envVar: 'OPENAI_API_KEY' },
    'veo-2':             { name: 'Veo 2 (Google)',             available: VeoProvider.available(),          envVar: 'GOOGLE_API_KEY' },
    'runway-gen3':       { name: 'Runway Gen-3',               available: RunwayProvider.available(),       envVar: 'RUNWAY_API_KEY' },
    'kling':             { name: 'Kling (Kuaishou)',            available: KlingProvider.available(),        envVar: 'KLING_API_KEY' },
    'luma-dream-machine':{ name: 'Luma Dream Machine',         available: LumaProvider.available(),         envVar: 'LUMA_API_KEY' },
    'elevenlabs':        { name: 'ElevenLabs TTS',             available: ElevenLabsProvider.available(),   envVar: 'ELEVENLABS_API_KEY' },
    'suno':              { name: 'Suno AI Music',              available: SunoProvider.available(),         envVar: 'SUNO_API_KEY' },
  }
}
