/**
 * Video Factory — 20-Stage Production Pipeline
 *
 * State machine that drives every video project from Idea to Analytics.
 * Each stage has a status, assigned department, input/output contract,
 * and auto-advance logic.
 *
 * Stages:
 *  1. idea            → Development
 *  2. research        → Research
 *  3. outline         → Scriptwriting
 *  4. script          → Scriptwriting
 *  5. storyboard      → Storyboarding
 *  6. character-bible → Character Design
 *  7. environment-bible → Environment Design
 *  8. shot-list       → Shot Planning
 *  9. image-prompts   → Shot Planning
 * 10. video-prompts   → Video Generation
 * 11. narration       → Narration
 * 12. voice           → Voice
 * 13. music           → Music
 * 14. sound-fx        → Sound Design
 * 15. editing-instructions → Editing
 * 16. thumbnail       → Thumbnail
 * 17. seo-package     → SEO
 * 18. metadata        → Metadata
 * 19. publishing-package → Publishing
 * 20. analytics-tracking → Analytics
 */

import fs from 'node:fs'
import path from 'node:path'
import type { ProductionMode } from './video-factory.departments.js'

// ── Types ─────────────────────────────────────────────────────────────────────

export type StageStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'needs-review'
  | 'approved'
  | 'completed'
  | 'failed'
  | 'skipped'

export type PipelineStage =
  | 'idea'
  | 'research'
  | 'outline'
  | 'script'
  | 'storyboard'
  | 'character-bible'
  | 'environment-bible'
  | 'shot-list'
  | 'image-prompts'
  | 'video-prompts'
  | 'narration'
  | 'voice'
  | 'music'
  | 'sound-fx'
  | 'editing-instructions'
  | 'thumbnail'
  | 'seo-package'
  | 'metadata'
  | 'publishing-package'
  | 'analytics-tracking'

export type ProjectStatus =
  | 'development'
  | 'pre-production'
  | 'production'
  | 'post-production'
  | 'publishing'
  | 'live'
  | 'archived'
  | 'cancelled'

export interface StageResult {
  stageId: PipelineStage
  status: StageStatus
  startedAt: string | null
  completedAt: string | null
  durationMs: number | null
  department: string
  output: unknown
  error: string | null
  retryCount: number
  qualityScore: number | null   // 0-100
  approvedBy: string | null
  notes: string
}

export interface VideoProject {
  id: string
  title: string
  channel: 'gods-glory' | 'machine-learning' | 'little-olympus' | string
  mode: ProductionMode
  episodeNumber: string
  season: number
  status: ProjectStatus
  createdAt: string
  updatedAt: string
  targetPublishDate: string | null
  stages: Record<PipelineStage, StageResult>
  metadata: {
    logline: string
    hook: string
    angle: string
    sceneCount: number
    estimatedDurationSec: number
    targetKeyword: string
    viralityScore: number
    priority: number
  }
  assets: {
    scriptFile: string | null
    imageFiles: string[]
    videoFiles: string[]
    audioFiles: string[]
    thumbnailFile: string | null
    finalVideoFile: string | null
  }
  costs: {
    imageGen: number
    videoGen: number
    tts: number
    llm: number
    total: number
    currency: 'USD'
  }
}

// ── Stage Definitions ─────────────────────────────────────────────────────────

export const STAGE_ORDER: PipelineStage[] = [
  'idea',
  'research',
  'outline',
  'script',
  'storyboard',
  'character-bible',
  'environment-bible',
  'shot-list',
  'image-prompts',
  'video-prompts',
  'narration',
  'voice',
  'music',
  'sound-fx',
  'editing-instructions',
  'thumbnail',
  'seo-package',
  'metadata',
  'publishing-package',
  'analytics-tracking',
]

export interface StageDefinition {
  id: PipelineStage
  name: string
  department: string
  phase: ProjectStatus
  /** Can run in parallel with other stages? */
  parallel: boolean
  /** Stages that must complete before this one starts */
  dependsOn: PipelineStage[]
  /** Does this stage auto-advance or wait for approval? */
  autoAdvance: boolean
  /** Retry limit before marking as failed */
  maxRetries: number
  /** Expected duration in seconds */
  estimatedDurationSec: number
  /** Can this stage be skipped for certain modes? */
  optionalForModes: ProductionMode[]
}

export const STAGE_DEFINITIONS: Record<PipelineStage, StageDefinition> = {
  'idea': {
    id: 'idea',
    name: 'Concept Development',
    department: 'development',
    phase: 'development',
    parallel: false,
    dependsOn: [],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 30,
    optionalForModes: [],
  },
  'research': {
    id: 'research',
    name: 'Deep Research',
    department: 'research',
    phase: 'pre-production',
    parallel: false,
    dependsOn: ['idea'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 120,
    optionalForModes: ['shorts', 'tiktok', 'instagram-reels'],
  },
  'outline': {
    id: 'outline',
    name: 'Script Outline',
    department: 'scriptwriting',
    phase: 'pre-production',
    parallel: false,
    dependsOn: ['research'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 60,
    optionalForModes: [],
  },
  'script': {
    id: 'script',
    name: 'Full Script',
    department: 'scriptwriting',
    phase: 'pre-production',
    parallel: false,
    dependsOn: ['outline'],
    autoAdvance: true,
    maxRetries: 3,
    estimatedDurationSec: 300,
    optionalForModes: [],
  },
  'storyboard': {
    id: 'storyboard',
    name: 'Visual Storyboard',
    department: 'storyboarding',
    phase: 'pre-production',
    parallel: false,
    dependsOn: ['script'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 120,
    optionalForModes: [],
  },
  'character-bible': {
    id: 'character-bible',
    name: 'Character Bible',
    department: 'character-design',
    phase: 'pre-production',
    parallel: true,
    dependsOn: ['script'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 60,
    optionalForModes: ['product-reviews', 'amazon-product-videos'],
  },
  'environment-bible': {
    id: 'environment-bible',
    name: 'Environment Bible',
    department: 'environment-design',
    phase: 'pre-production',
    parallel: true,
    dependsOn: ['script'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 60,
    optionalForModes: ['product-reviews', 'amazon-product-videos'],
  },
  'shot-list': {
    id: 'shot-list',
    name: 'Shot List (4 per scene)',
    department: 'shot-planning',
    phase: 'production',
    parallel: false,
    dependsOn: ['storyboard', 'character-bible', 'environment-bible'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 120,
    optionalForModes: [],
  },
  'image-prompts': {
    id: 'image-prompts',
    name: 'Image Generation',
    department: 'image-generation',
    phase: 'production',
    parallel: false,
    dependsOn: ['shot-list'],
    autoAdvance: true,
    maxRetries: 5,
    estimatedDurationSec: 600,
    optionalForModes: [],
  },
  'video-prompts': {
    id: 'video-prompts',
    name: 'Video Generation',
    department: 'video-generation',
    phase: 'production',
    parallel: true,
    dependsOn: ['image-prompts'],
    autoAdvance: true,
    maxRetries: 3,
    estimatedDurationSec: 1200,
    optionalForModes: ['educational-courses'],
  },
  'narration': {
    id: 'narration',
    name: 'Narration Finalization',
    department: 'narration',
    phase: 'production',
    parallel: true,
    dependsOn: ['script'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 60,
    optionalForModes: [],
  },
  'voice': {
    id: 'voice',
    name: 'Voice Generation (ElevenLabs)',
    department: 'voice',
    phase: 'production',
    parallel: true,
    dependsOn: ['narration'],
    autoAdvance: true,
    maxRetries: 3,
    estimatedDurationSec: 180,
    optionalForModes: [],
  },
  'music': {
    id: 'music',
    name: 'Music Score',
    department: 'music',
    phase: 'post-production',
    parallel: true,
    dependsOn: ['narration'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 120,
    optionalForModes: [],
  },
  'sound-fx': {
    id: 'sound-fx',
    name: 'Sound Design',
    department: 'sound-design',
    phase: 'post-production',
    parallel: true,
    dependsOn: ['narration'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 60,
    optionalForModes: ['product-reviews'],
  },
  'editing-instructions': {
    id: 'editing-instructions',
    name: 'Editing Instructions',
    department: 'editing',
    phase: 'post-production',
    parallel: false,
    dependsOn: ['video-prompts', 'voice', 'music', 'sound-fx'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 120,
    optionalForModes: [],
  },
  'thumbnail': {
    id: 'thumbnail',
    name: 'Thumbnail Design',
    department: 'thumbnail',
    phase: 'post-production',
    parallel: true,
    dependsOn: ['image-prompts'],
    autoAdvance: true,
    maxRetries: 3,
    estimatedDurationSec: 120,
    optionalForModes: [],
  },
  'seo-package': {
    id: 'seo-package',
    name: 'SEO Package',
    department: 'seo',
    phase: 'post-production',
    parallel: true,
    dependsOn: ['script'],
    autoAdvance: true,
    maxRetries: 2,
    estimatedDurationSec: 60,
    optionalForModes: [],
  },
  'metadata': {
    id: 'metadata',
    name: 'Upload Metadata',
    department: 'metadata',
    phase: 'publishing',
    parallel: false,
    dependsOn: ['seo-package', 'thumbnail'],
    autoAdvance: true,
    maxRetries: 1,
    estimatedDurationSec: 30,
    optionalForModes: [],
  },
  'publishing-package': {
    id: 'publishing-package',
    name: 'Publishing Package',
    department: 'publishing',
    phase: 'publishing',
    parallel: false,
    dependsOn: ['editing-instructions', 'metadata'],
    autoAdvance: false,   // ALWAYS requires approval before publishing
    maxRetries: 1,
    estimatedDurationSec: 60,
    optionalForModes: [],
  },
  'analytics-tracking': {
    id: 'analytics-tracking',
    name: 'Analytics Tracking Setup',
    department: 'analytics',
    phase: 'live',
    parallel: false,
    dependsOn: ['publishing-package'],
    autoAdvance: true,
    maxRetries: 1,
    estimatedDurationSec: 30,
    optionalForModes: [],
  },
}

// ── Pipeline Engine ───────────────────────────────────────────────────────────

const DATA_DIR      = process.env.DATA_DIR ?? path.resolve('.empire-data')
const PROJECTS_DIR  = path.join(DATA_DIR, 'video-factory', 'projects')

function ensureProjectsDir(): void {
  fs.mkdirSync(PROJECTS_DIR, { recursive: true })
}

function projectPath(projectId: string): string {
  return path.join(PROJECTS_DIR, `${projectId}.json`)
}

function buildInitialStages(mode: ProductionMode): Record<PipelineStage, StageResult> {
  const stages = {} as Record<PipelineStage, StageResult>
  for (const stageId of STAGE_ORDER) {
    const def = STAGE_DEFINITIONS[stageId]
    const skipped = def.optionalForModes.includes(mode)
    stages[stageId] = {
      stageId,
      status: skipped ? 'skipped' : 'pending',
      startedAt: null,
      completedAt: null,
      durationMs: null,
      department: def.department,
      output: null,
      error: null,
      retryCount: 0,
      qualityScore: null,
      approvedBy: null,
      notes: '',
    }
  }
  return stages
}

// ── Public API ────────────────────────────────────────────────────────────────

export function createProject(params: {
  title: string
  channel: string
  mode: ProductionMode
  episodeNumber: string
  season: number
  logline?: string
  targetPublishDate?: string
}): VideoProject {
  ensureProjectsDir()

  const id = `vf-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const now = new Date().toISOString()

  const project: VideoProject = {
    id,
    title: params.title,
    channel: params.channel,
    mode: params.mode,
    episodeNumber: params.episodeNumber,
    season: params.season,
    status: 'development',
    createdAt: now,
    updatedAt: now,
    targetPublishDate: params.targetPublishDate ?? null,
    stages: buildInitialStages(params.mode),
    metadata: {
      logline: params.logline ?? '',
      hook: '',
      angle: '',
      sceneCount: 24,
      estimatedDurationSec: 1200,
      targetKeyword: '',
      viralityScore: 0,
      priority: 5,
    },
    assets: {
      scriptFile: null,
      imageFiles: [],
      videoFiles: [],
      audioFiles: [],
      thumbnailFile: null,
      finalVideoFile: null,
    },
    costs: {
      imageGen: 0,
      videoGen: 0,
      tts: 0,
      llm: 0,
      total: 0,
      currency: 'USD',
    },
  }

  saveProject(project)
  return project
}

export function loadProject(projectId: string): VideoProject | null {
  ensureProjectsDir()
  const p = projectPath(projectId)
  if (!fs.existsSync(p)) return null
  return JSON.parse(fs.readFileSync(p, 'utf8')) as VideoProject
}

export function saveProject(project: VideoProject): void {
  ensureProjectsDir()
  project.updatedAt = new Date().toISOString()
  fs.writeFileSync(projectPath(project.id), JSON.stringify(project, null, 2))
}

export function listProjects(): VideoProject[] {
  ensureProjectsDir()
  return fs.readdirSync(PROJECTS_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(fs.readFileSync(path.join(PROJECTS_DIR, f), 'utf8')) as VideoProject)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export function updateStage(
  projectId: string,
  stage: PipelineStage,
  update: Partial<StageResult>
): VideoProject | null {
  const project = loadProject(projectId)
  if (!project) return null

  project.stages[stage] = { ...project.stages[stage], ...update }

  // Auto-advance project status based on current stage
  const currentPhase = STAGE_DEFINITIONS[stage].phase
  if (update.status === 'completed') {
    project.status = currentPhase
  }

  saveProject(project)
  return project
}

export function getNextStages(project: VideoProject): PipelineStage[] {
  const ready: PipelineStage[] = []

  for (const stageId of STAGE_ORDER) {
    const stage = project.stages[stageId]
    if (stage.status !== 'pending') continue

    const def = STAGE_DEFINITIONS[stageId]
    const depsComplete = def.dependsOn.every(dep => {
      const depStage = project.stages[dep]
      return depStage.status === 'completed' || depStage.status === 'skipped'
    })

    if (depsComplete) ready.push(stageId)
  }

  return ready
}

export function getProjectProgress(project: VideoProject): {
  total: number
  completed: number
  skipped: number
  running: number
  failed: number
  pending: number
  percentComplete: number
  currentStages: PipelineStage[]
} {
  const stages = Object.values(project.stages)
  const total     = stages.length
  const completed = stages.filter(s => s.status === 'completed').length
  const skipped   = stages.filter(s => s.status === 'skipped').length
  const running   = stages.filter(s => s.status === 'running').length
  const failed    = stages.filter(s => s.status === 'failed').length
  const pending   = stages.filter(s => s.status === 'pending').length
  const active    = completed + skipped

  return {
    total,
    completed,
    skipped,
    running,
    failed,
    pending,
    percentComplete: Math.round((active / total) * 100),
    currentStages: stages.filter(s => s.status === 'running').map(s => s.stageId),
  }
}

export function startStage(projectId: string, stage: PipelineStage): VideoProject | null {
  return updateStage(projectId, stage, {
    status: 'running',
    startedAt: new Date().toISOString(),
  })
}

export function completeStage(
  projectId: string,
  stage: PipelineStage,
  output: unknown,
  qualityScore?: number
): VideoProject | null {
  const now = new Date().toISOString()
  const project = loadProject(projectId)
  if (!project) return null

  const startedAt = project.stages[stage].startedAt
  const durationMs = startedAt ? Date.now() - new Date(startedAt).getTime() : null

  return updateStage(projectId, stage, {
    status: 'completed',
    completedAt: now,
    durationMs,
    output,
    qualityScore: qualityScore ?? null,
    error: null,
  })
}

export function failStage(
  projectId: string,
  stage: PipelineStage,
  error: string
): VideoProject | null {
  const project = loadProject(projectId)
  if (!project) return null

  const currentRetry = project.stages[stage].retryCount
  const maxRetries = STAGE_DEFINITIONS[stage].maxRetries

  return updateStage(projectId, stage, {
    status: currentRetry < maxRetries ? 'pending' : 'failed',
    error,
    retryCount: currentRetry + 1,
  })
}

export function getStagesSummary(): { stage: PipelineStage; name: string; department: string; phase: ProjectStatus }[] {
  return STAGE_ORDER.map(id => ({
    stage: id,
    name: STAGE_DEFINITIONS[id].name,
    department: STAGE_DEFINITIONS[id].department,
    phase: STAGE_DEFINITIONS[id].phase,
  }))
}
