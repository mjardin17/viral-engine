/**
 * Video Factory — Persistent Memory Engines
 *
 * Three memory engines that ensure visual consistency across all episodes:
 *
 *  1. CharacterEngine  — stores every character's appearance, costume, and
 *                        visual identifiers so AI re-generates them identically
 *
 *  2. EnvironmentEngine — stores every location's visual description, palette,
 *                         and atmosphere for consistent setting generation
 *
 *  3. TimelineEngine   — tracks continuity across scenes: costumes, time of day,
 *                        weather, props, and camera style per episode
 *
 * All data persists to .empire-data/video-factory/memory/ as JSON files.
 * Knowledge Base module is the source of truth.
 */

import fs from 'node:fs'
import path from 'node:path'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CharacterRecord {
  id: string
  name: string
  /** Canonical display name (used in prompts) */
  canonicalName: string
  /** All names/aliases this character appears under */
  aliases: string[]
  /** Physical description for AI prompts */
  physicalDescription: string
  /** Age range in the episode */
  ageRange: string
  /** Base appearance — never changes */
  baseAppearance: {
    build: string
    height: string
    skinTone: string
    hairColor: string
    hairStyle: string
    facialFeatures: string
    distinctiveFeatures: string
  }
  /** Costumes per time period / scene context */
  costumes: Array<{
    context: string        // "Battle of Waterloo scene", "Post-exile period", etc.
    description: string    // full costume description for AI
    colors: string[]       // hex or color names
  }>
  /** Emotional expression range */
  expressions: {
    neutral: string
    anger: string
    grief: string
    triumph: string
    fear: string
    determination: string
  }
  /** AI prompt seed — paste this into any image prompt for this character */
  promptSeed: string
  /** Negative prompt — what to avoid when generating this character */
  negativePromptSeed: string
  /** Episode IDs where this character appears */
  appearsIn: string[]
  /** Date first created */
  createdAt: string
  updatedAt: string
  /** Source: book, portrait, historical record, etc. */
  historicalReference: string
}

export interface EnvironmentRecord {
  id: string
  name: string
  /** Canonical location name */
  canonicalName: string
  /** Aliases for this location */
  aliases: string[]
  /** Geographic/physical description */
  geography: string
  /** Era/time period */
  timePeriod: string
  /** What existed here in this period */
  infrastructure: string
  /** Atmosphere description */
  atmosphere: {
    timeOfDay: string
    weather: string
    visibility: string
    temperature: string
    mood: string
  }
  /** Color palette */
  palette: {
    sky: string
    ground: string
    vegetation: string
    structures: string
    accent: string
    hexCodes: string[]
  }
  /** Scale and scope */
  scale: 'intimate' | 'local' | 'regional' | 'epic' | 'cosmic'
  /** AI prompt seed for this environment */
  promptSeed: string
  /** Negative prompt for this environment */
  negativePromptSeed: string
  /** Lighting conditions */
  lighting: string
  /** Episode IDs where this environment appears */
  appearsIn: string[]
  createdAt: string
  updatedAt: string
  historicalReference: string
}

export interface TimelineEntry {
  episodeId: string
  sceneId: string
  sceneNumber: number
  timestamp: string
  /** Characters present in this scene with their costume state */
  charactersPresent: Array<{
    characterId: string
    costumeContext: string
    emotionState: string
    position: string   // "foreground left", "background right", etc.
  }>
  /** Environment active in this scene */
  environmentId: string
  /** Specific conditions for this scene */
  conditions: {
    timeOfDay: string
    weather: string
    lighting: string
    camera: string    // camera style for consistency
  }
  /** Props present in this scene */
  props: string[]
  /** Continuity notes */
  continuityNotes: string
}

export interface TimelineRecord {
  episodeId: string
  episodeTitle: string
  channel: string
  entries: TimelineEntry[]
  globalNotes: string
  createdAt: string
  updatedAt: string
}

// ── Storage Paths ─────────────────────────────────────────────────────────────

const DATA_DIR      = process.env.DATA_DIR ?? path.resolve('.empire-data')
const MEMORY_DIR    = path.join(DATA_DIR, 'video-factory', 'memory')
const CHARS_DIR     = path.join(MEMORY_DIR, 'characters')
const ENVS_DIR      = path.join(MEMORY_DIR, 'environments')
const TIMELINE_DIR  = path.join(MEMORY_DIR, 'timelines')

function ensureMemoryDirs(): void {
  fs.mkdirSync(CHARS_DIR, { recursive: true })
  fs.mkdirSync(ENVS_DIR, { recursive: true })
  fs.mkdirSync(TIMELINE_DIR, { recursive: true })
}

// ── Character Engine ──────────────────────────────────────────────────────────

export const CharacterEngine = {
  save(character: CharacterRecord): void {
    ensureMemoryDirs()
    character.updatedAt = new Date().toISOString()
    fs.writeFileSync(
      path.join(CHARS_DIR, `${character.id}.json`),
      JSON.stringify(character, null, 2)
    )
  },

  load(id: string): CharacterRecord | null {
    ensureMemoryDirs()
    const p = path.join(CHARS_DIR, `${id}.json`)
    if (!fs.existsSync(p)) return null
    return JSON.parse(fs.readFileSync(p, 'utf8')) as CharacterRecord
  },

  findByName(name: string): CharacterRecord | null {
    ensureMemoryDirs()
    const normalized = name.toLowerCase().trim()
    const files = fs.readdirSync(CHARS_DIR).filter(f => f.endsWith('.json'))
    for (const f of files) {
      const char = JSON.parse(fs.readFileSync(path.join(CHARS_DIR, f), 'utf8')) as CharacterRecord
      if (
        char.name.toLowerCase() === normalized ||
        char.canonicalName.toLowerCase() === normalized ||
        char.aliases.some(a => a.toLowerCase() === normalized)
      ) return char
    }
    return null
  },

  listAll(): CharacterRecord[] {
    ensureMemoryDirs()
    return fs.readdirSync(CHARS_DIR)
      .filter(f => f.endsWith('.json'))
      .map(f => JSON.parse(fs.readFileSync(path.join(CHARS_DIR, f), 'utf8')) as CharacterRecord)
      .sort((a, b) => a.canonicalName.localeCompare(b.canonicalName))
  },

  /** Generate the complete image prompt seed for a character in a given context */
  getPromptSeed(id: string, costumeContext?: string): string {
    const char = this.load(id)
    if (!char) return ''

    const costume = costumeContext
      ? char.costumes.find(c => c.context.toLowerCase().includes(costumeContext.toLowerCase()))
      : char.costumes[0]

    return [
      char.promptSeed,
      costume ? `wearing ${costume.description}` : '',
    ].filter(Boolean).join(', ')
  },

  create(params: Omit<CharacterRecord, 'id' | 'createdAt' | 'updatedAt'>): CharacterRecord {
    const char: CharacterRecord = {
      ...params,
      id: `char-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    this.save(char)
    return char
  },

  addEpisode(characterId: string, episodeId: string): void {
    const char = this.load(characterId)
    if (!char) return
    if (!char.appearsIn.includes(episodeId)) {
      char.appearsIn.push(episodeId)
      this.save(char)
    }
  },

  getStats(): { total: number; multiEpisode: number; singleEpisode: number } {
    const all = this.listAll()
    return {
      total: all.length,
      multiEpisode: all.filter(c => c.appearsIn.length > 1).length,
      singleEpisode: all.filter(c => c.appearsIn.length === 1).length,
    }
  },
}

// ── Environment Engine ────────────────────────────────────────────────────────

export const EnvironmentEngine = {
  save(env: EnvironmentRecord): void {
    ensureMemoryDirs()
    env.updatedAt = new Date().toISOString()
    fs.writeFileSync(
      path.join(ENVS_DIR, `${env.id}.json`),
      JSON.stringify(env, null, 2)
    )
  },

  load(id: string): EnvironmentRecord | null {
    ensureMemoryDirs()
    const p = path.join(ENVS_DIR, `${id}.json`)
    if (!fs.existsSync(p)) return null
    return JSON.parse(fs.readFileSync(p, 'utf8')) as EnvironmentRecord
  },

  findByName(name: string): EnvironmentRecord | null {
    ensureMemoryDirs()
    const normalized = name.toLowerCase().trim()
    const files = fs.readdirSync(ENVS_DIR).filter(f => f.endsWith('.json'))
    for (const f of files) {
      const env = JSON.parse(fs.readFileSync(path.join(ENVS_DIR, f), 'utf8')) as EnvironmentRecord
      if (
        env.name.toLowerCase() === normalized ||
        env.canonicalName.toLowerCase() === normalized ||
        env.aliases.some(a => a.toLowerCase() === normalized)
      ) return env
    }
    return null
  },

  listAll(): EnvironmentRecord[] {
    ensureMemoryDirs()
    return fs.readdirSync(ENVS_DIR)
      .filter(f => f.endsWith('.json'))
      .map(f => JSON.parse(fs.readFileSync(path.join(ENVS_DIR, f), 'utf8')) as EnvironmentRecord)
      .sort((a, b) => a.canonicalName.localeCompare(b.canonicalName))
  },

  /** Full environment prompt seed for image generation */
  getPromptSeed(id: string, timeOfDay?: string, weather?: string): string {
    const env = this.load(id)
    if (!env) return ''

    const tod = timeOfDay ?? env.atmosphere.timeOfDay
    const wx  = weather   ?? env.atmosphere.weather

    return [
      env.promptSeed,
      `${tod} lighting`,
      wx !== 'clear' ? wx : '',
      env.lighting,
    ].filter(Boolean).join(', ')
  },

  create(params: Omit<EnvironmentRecord, 'id' | 'createdAt' | 'updatedAt'>): EnvironmentRecord {
    const env: EnvironmentRecord = {
      ...params,
      id: `env-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    this.save(env)
    return env
  },

  addEpisode(envId: string, episodeId: string): void {
    const env = this.load(envId)
    if (!env) return
    if (!env.appearsIn.includes(episodeId)) {
      env.appearsIn.push(episodeId)
      this.save(env)
    }
  },

  getStats(): { total: number; byScale: Record<string, number> } {
    const all = this.listAll()
    const byScale: Record<string, number> = {}
    for (const e of all) {
      byScale[e.scale] = (byScale[e.scale] ?? 0) + 1
    }
    return { total: all.length, byScale }
  },
}

// ── Timeline Engine ───────────────────────────────────────────────────────────

export const TimelineEngine = {
  save(timeline: TimelineRecord): void {
    ensureMemoryDirs()
    timeline.updatedAt = new Date().toISOString()
    fs.writeFileSync(
      path.join(TIMELINE_DIR, `${timeline.episodeId}.json`),
      JSON.stringify(timeline, null, 2)
    )
  },

  load(episodeId: string): TimelineRecord | null {
    ensureMemoryDirs()
    const p = path.join(TIMELINE_DIR, `${episodeId}.json`)
    if (!fs.existsSync(p)) return null
    return JSON.parse(fs.readFileSync(p, 'utf8')) as TimelineRecord
  },

  create(episodeId: string, episodeTitle: string, channel: string): TimelineRecord {
    const timeline: TimelineRecord = {
      episodeId,
      episodeTitle,
      channel,
      entries: [],
      globalNotes: '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    this.save(timeline)
    return timeline
  },

  addScene(episodeId: string, entry: Omit<TimelineEntry, 'timestamp'>): void {
    let timeline = this.load(episodeId)
    if (!timeline) return

    timeline.entries.push({
      ...entry,
      timestamp: new Date().toISOString(),
    })

    // Sort by scene number
    timeline.entries.sort((a, b) => a.sceneNumber - b.sceneNumber)
    this.save(timeline)
  },

  /** Check for continuity errors in the timeline */
  checkContinuity(episodeId: string): Array<{
    sceneNumber: number
    type: 'costume-change' | 'weather-inconsistency' | 'character-conflict' | 'lighting-jump'
    description: string
    severity: 'warning' | 'error'
  }> {
    const timeline = this.load(episodeId)
    if (!timeline || timeline.entries.length < 2) return []

    const issues: Array<{
      sceneNumber: number
      type: 'costume-change' | 'weather-inconsistency' | 'character-conflict' | 'lighting-jump'
      description: string
      severity: 'warning' | 'error'
    }> = []

    for (let i = 1; i < timeline.entries.length; i++) {
      const prev = timeline.entries[i - 1]
      const curr = timeline.entries[i]

      // Same environment — check weather consistency
      if (prev.environmentId === curr.environmentId) {
        if (prev.conditions.weather !== curr.conditions.weather) {
          issues.push({
            sceneNumber: curr.sceneNumber,
            type: 'weather-inconsistency',
            description: `Weather changed from "${prev.conditions.weather}" to "${curr.conditions.weather}" in same location`,
            severity: 'warning',
          })
        }
      }

      // Check same character costume consistency within same time period
      for (const prevChar of prev.charactersPresent) {
        const currChar = curr.charactersPresent.find(c => c.characterId === prevChar.characterId)
        if (currChar && prevChar.costumeContext !== currChar.costumeContext) {
          issues.push({
            sceneNumber: curr.sceneNumber,
            type: 'costume-change',
            description: `Character ${prevChar.characterId} costume context changed: "${prevChar.costumeContext}" → "${currChar.costumeContext}"`,
            severity: 'warning',
          })
        }
      }
    }

    return issues
  },

  /** Get all characters in a specific scene */
  getSceneCharacters(episodeId: string, sceneNumber: number): TimelineEntry | null {
    const timeline = this.load(episodeId)
    if (!timeline) return null
    return timeline.entries.find(e => e.sceneNumber === sceneNumber) ?? null
  },

  listAll(): TimelineRecord[] {
    ensureMemoryDirs()
    return fs.readdirSync(TIMELINE_DIR)
      .filter(f => f.endsWith('.json'))
      .map(f => JSON.parse(fs.readFileSync(path.join(TIMELINE_DIR, f), 'utf8')) as TimelineRecord)
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  },
}

// ── Memory Health ─────────────────────────────────────────────────────────────

export function getMemoryStats(): {
  characters: ReturnType<typeof CharacterEngine.getStats>
  environments: ReturnType<typeof EnvironmentEngine.getStats>
  timelines: number
  totalFiles: number
} {
  ensureMemoryDirs()

  const charStats = CharacterEngine.getStats()
  const envStats  = EnvironmentEngine.getStats()
  const timelines = TimelineEngine.listAll().length

  return {
    characters: charStats,
    environments: envStats,
    timelines,
    totalFiles: charStats.total + envStats.total + timelines,
  }
}
