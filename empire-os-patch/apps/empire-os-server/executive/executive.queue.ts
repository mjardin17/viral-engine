/**
 * Autonomous Executive — Master Queue
 *
 * The Master Queue is the central nervous system of the Autonomous Executive.
 * Every project, goal, and action is broken into small executable tasks and
 * stored here. Workers pull from the queue, execute, and report back.
 *
 * Features:
 *  - Task decomposition: breaks any goal into hundreds of micro-tasks
 *  - Priority management: critical/high/medium/low with automatic re-ordering
 *  - Dependency tracking: tasks can depend on other tasks completing first
 *  - Worker assignment: tasks assigned to specific workers or "any"
 *  - Auto-retry: failed tasks retry up to maxRetries times
 *  - Execution log: complete history of every task execution
 *
 * Rules:
 *  - Workers execute tasks independently without waiting for user input
 *  - Only tasks marked requiresApproval=true stop and wait for Josh
 *  - All task results are stored for learning and retrospectives
 */

import fs from 'node:fs'
import path from 'node:path'
import type { WorkerId, TaskPriority } from './executive.workers.js'

// ── Types ─────────────────────────────────────────────────────────────────────

export type TaskStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'waiting-approval'
  | 'approved'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'skipped'

export type TaskCategory =
  | 'production'    // Script, render, edit
  | 'research'      // Research, analysis
  | 'publishing'    // Upload, schedule, distribute
  | 'marketing'     // Social, promotion, SEO
  | 'engineering'   // Pipeline, code, automation
  | 'analytics'     // Metrics, reporting, insights
  | 'strategy'      // Planning, prioritization
  | 'admin'         // Housekeeping, maintenance
  | 'external'      // Requires external action (Josh or third party)

export interface MasterTask {
  id: string
  title: string
  description: string
  category: TaskCategory
  priority: TaskPriority
  status: TaskStatus
  /** The worker assigned to execute this task */
  assignedTo: WorkerId | 'any'
  /** Task IDs that must complete before this one can start */
  dependsOn: string[]
  /** Task IDs that this task blocks */
  blocks: string[]
  /** Project this task belongs to (null = company-wide) */
  projectId: string | null
  /** Episode this task relates to (null = general) */
  episodeId: string | null
  /** Channel this task relates to (null = all channels) */
  channel: string | null
  /** Does this task require Josh's explicit approval before executing? */
  requiresApproval: boolean
  /** Does this task require Josh's approval after executing? */
  requiresReview: boolean
  /** Number of times this task has been attempted */
  attemptCount: number
  /** Max retries before marking as failed */
  maxRetries: number
  /** Date this task was created */
  createdAt: string
  /** Date this task was last updated */
  updatedAt: string
  /** Due date (null = no deadline) */
  dueDate: string | null
  /** Date execution started */
  startedAt: string | null
  /** Date execution completed (success or failure) */
  completedAt: string | null
  /** Estimated time to complete in minutes */
  estimatedMinutes: number
  /** Actual time taken in ms */
  actualDurationMs: number | null
  /** The output/result of the task */
  result: unknown
  /** Error message if failed */
  error: string | null
  /** Notes from the worker about this task */
  notes: string
  /** Tags for filtering and grouping */
  tags: string[]
  /** Who created this task */
  createdBy: WorkerId | 'system' | 'josh'
}

export interface TaskExecutionLog {
  taskId: string
  workerId: WorkerId
  startedAt: string
  completedAt: string | null
  status: TaskStatus
  output: unknown
  error: string | null
  durationMs: number | null
}

export interface QueueStats {
  total: number
  byStatus: Record<TaskStatus, number>
  byPriority: Record<TaskPriority, number>
  byCategory: Record<TaskCategory, number>
  byWorker: Record<string, number>
  criticalBlocked: number
  overdue: number
  avgCompletionTimeMinutes: number
}

// ── Storage ───────────────────────────────────────────────────────────────────

const DATA_DIR  = process.env.DATA_DIR ?? path.resolve('.empire-data')
const QUEUE_DIR = path.join(DATA_DIR, 'executive', 'queue')
const LOG_FILE  = path.join(DATA_DIR, 'executive', 'execution-log.json')

function ensureQueueDirs(): void {
  fs.mkdirSync(QUEUE_DIR, { recursive: true })
}

function taskPath(taskId: string): string {
  return path.join(QUEUE_DIR, `${taskId}.json`)
}

// ── Queue API ─────────────────────────────────────────────────────────────────

export function createTask(params: Omit<MasterTask,
  'id' | 'status' | 'attemptCount' | 'createdAt' | 'updatedAt' |
  'startedAt' | 'completedAt' | 'actualDurationMs' | 'result' | 'error'
>): MasterTask {
  ensureQueueDirs()

  const id = `task-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const now = new Date().toISOString()

  const task: MasterTask = {
    ...params,
    id,
    status: 'pending',
    attemptCount: 0,
    createdAt: now,
    updatedAt: now,
    startedAt: null,
    completedAt: null,
    actualDurationMs: null,
    result: null,
    error: null,
  }

  fs.writeFileSync(taskPath(id), JSON.stringify(task, null, 2))
  return task
}

export function loadTask(taskId: string): MasterTask | null {
  ensureQueueDirs()
  const p = taskPath(taskId)
  if (!fs.existsSync(p)) return null
  return JSON.parse(fs.readFileSync(p, 'utf8')) as MasterTask
}

export function updateTask(taskId: string, update: Partial<MasterTask>): MasterTask | null {
  const task = loadTask(taskId)
  if (!task) return null
  const updated = { ...task, ...update, updatedAt: new Date().toISOString() }
  fs.writeFileSync(taskPath(taskId), JSON.stringify(updated, null, 2))
  return updated
}

export function listAllTasks(): MasterTask[] {
  ensureQueueDirs()
  return fs.readdirSync(QUEUE_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(fs.readFileSync(path.join(QUEUE_DIR, f), 'utf8')) as MasterTask)
}

export function getQueueStats(): QueueStats {
  const tasks = listAllTasks()
  const now = new Date()

  const byStatus = {} as Record<TaskStatus, number>
  const byPriority = {} as Record<TaskPriority, number>
  const byCategory = {} as Record<TaskCategory, number>
  const byWorker: Record<string, number> = {}

  let criticalBlocked = 0
  let overdue = 0
  let totalCompletedMs = 0
  let completedCount = 0

  for (const t of tasks) {
    byStatus[t.status] = (byStatus[t.status] ?? 0) + 1
    byPriority[t.priority] = (byPriority[t.priority] ?? 0) + 1
    byCategory[t.category] = (byCategory[t.category] ?? 0) + 1
    byWorker[t.assignedTo] = (byWorker[t.assignedTo] ?? 0) + 1

    if (t.priority === 'critical' && t.dependsOn.some(dep => {
      const depTask = loadTask(dep)
      return depTask && depTask.status !== 'completed' && depTask.status !== 'skipped'
    })) criticalBlocked++

    if (t.dueDate && t.status !== 'completed' && t.status !== 'cancelled') {
      if (new Date(t.dueDate) < now) overdue++
    }

    if (t.status === 'completed' && t.actualDurationMs) {
      totalCompletedMs += t.actualDurationMs
      completedCount++
    }
  }

  return {
    total: tasks.length,
    byStatus,
    byPriority,
    byCategory,
    byWorker,
    criticalBlocked,
    overdue,
    avgCompletionTimeMinutes: completedCount > 0 ? Math.round(totalCompletedMs / completedCount / 60000) : 0,
  }
}

/** Get tasks ready for execution — deps satisfied, not blocked */
export function getReadyTasks(workerId?: WorkerId, limit = 10): MasterTask[] {
  const tasks = listAllTasks()
  const completedOrSkipped = new Set(
    tasks
      .filter(t => t.status === 'completed' || t.status === 'skipped')
      .map(t => t.id)
  )

  return tasks
    .filter(t => {
      if (t.status !== 'pending' && t.status !== 'queued') return false
      if (workerId && t.assignedTo !== 'any' && t.assignedTo !== workerId) return false
      if (t.requiresApproval && t.status !== 'approved') return false
      const depsOk = t.dependsOn.every(dep => completedOrSkipped.has(dep))
      return depsOk
    })
    .sort((a, b) => {
      const priorityOrder: Record<TaskPriority, number> = { critical: 0, high: 1, medium: 2, low: 3 }
      const pDiff = priorityOrder[a.priority] - priorityOrder[b.priority]
      if (pDiff !== 0) return pDiff
      return a.createdAt.localeCompare(b.createdAt)
    })
    .slice(0, limit)
}

export function startTask(taskId: string): MasterTask | null {
  return updateTask(taskId, {
    status: 'running',
    startedAt: new Date().toISOString(),
  })
}

export function completeTask(
  taskId: string,
  result: unknown,
  notes: string = ''
): MasterTask | null {
  const task = loadTask(taskId)
  if (!task) return null

  const completedAt = new Date().toISOString()
  const durationMs = task.startedAt
    ? new Date(completedAt).getTime() - new Date(task.startedAt).getTime()
    : null

  return updateTask(taskId, {
    status: task.requiresReview ? 'waiting-approval' : 'completed',
    completedAt,
    actualDurationMs: durationMs,
    result,
    notes,
  })
}

export function failTask(taskId: string, error: string): MasterTask | null {
  const task = loadTask(taskId)
  if (!task) return null

  const newAttemptCount = task.attemptCount + 1
  const shouldRetry = newAttemptCount < task.maxRetries

  return updateTask(taskId, {
    status: shouldRetry ? 'pending' : 'failed',
    attemptCount: newAttemptCount,
    error,
    startedAt: null,
  })
}

// ── Task Decomposition Engine ─────────────────────────────────────────────────

/**
 * Standard task blueprints — used to auto-generate task lists for common goals.
 * Each blueprint generates a set of linked tasks for a specific activity.
 */
export interface TaskBlueprint {
  id: string
  name: string
  description: string
  tasks: Array<{
    title: string
    description: string
    assignedTo: WorkerId | 'any'
    category: TaskCategory
    priority: TaskPriority
    estimatedMinutes: number
    requiresApproval: boolean
    requiresReview: boolean
    dependsOnIndex: number[]  // Indices into the tasks array (this task's deps)
    tags: string[]
  }>
}

export const TASK_BLUEPRINTS: TaskBlueprint[] = [
  {
    id: 'render-full-episode',
    name: 'Render Full Episode',
    description: 'Complete pipeline from script to finished MP4',
    tasks: [
      { title: 'Verify script is complete (24 scenes)', description: 'Check the episode JSON in prompts/gods_glory/ for completeness. Must have 24 scenes, ≥600s estimated duration.', assignedTo: 'qa-director', category: 'production', priority: 'high', estimatedMinutes: 5, requiresApproval: false, requiresReview: false, dependsOnIndex: [], tags: ['script', 'qa'] },
      { title: 'Run auto_render.py for episode', description: 'Execute auto_render.py targeting the episode JSON. Monitor for errors.', assignedTo: 'engineering-lead', category: 'production', priority: 'high', estimatedMinutes: 120, requiresApproval: true, requiresReview: false, dependsOnIndex: [0], tags: ['render', 'production'] },
      { title: 'Run patch_fallbacks.py if needed', description: 'If any images are <20KB, run patch_fallbacks.py to fix them.', assignedTo: 'engineering-lead', category: 'production', priority: 'high', estimatedMinutes: 30, requiresApproval: false, requiresReview: false, dependsOnIndex: [1], tags: ['render', 'fix'] },
      { title: 'QA check final MP4', description: 'Verify final MP4: duration ≥600s, audio present, no broken scenes.', assignedTo: 'qa-director', category: 'production', priority: 'critical', estimatedMinutes: 15, requiresApproval: false, requiresReview: false, dependsOnIndex: [2], tags: ['qa', 'final'] },
      { title: 'Prepare upload package', description: 'Create upload metadata: title options (5), description with timestamps, 20 tags, chapter markers.', assignedTo: 'publishing-director', category: 'publishing', priority: 'high', estimatedMinutes: 20, requiresApproval: false, requiresReview: true, dependsOnIndex: [3], tags: ['publishing', 'metadata'] },
      { title: 'Design thumbnail', description: 'Create thumbnail concept and generate thumbnail image prompt.', assignedTo: 'creative-director', category: 'production', priority: 'high', estimatedMinutes: 30, requiresApproval: false, requiresReview: true, dependsOnIndex: [3], tags: ['thumbnail'] },
      { title: 'Josh approval: upload package', description: 'Present complete upload package to Josh for final approval before publishing.', assignedTo: 'publishing-director', category: 'publishing', priority: 'critical', estimatedMinutes: 5, requiresApproval: true, requiresReview: false, dependsOnIndex: [4, 5], tags: ['approval', 'publishing'] },
    ],
  },
  {
    id: 'launch-channel',
    name: 'Launch YouTube Channel',
    description: 'Full launch process for a new YouTube channel',
    tasks: [
      { title: 'Verify channel is created on YouTube', description: 'Confirm channel exists, has a name, and Josh has owner access.', assignedTo: 'project-manager', category: 'admin', priority: 'critical', estimatedMinutes: 5, requiresApproval: false, requiresReview: false, dependsOnIndex: [], tags: ['launch', 'youtube'] },
      { title: 'Channel branding review', description: 'Review channel art, profile picture, and banner for brand consistency.', assignedTo: 'creative-director', category: 'strategy', priority: 'high', estimatedMinutes: 30, requiresApproval: false, requiresReview: true, dependsOnIndex: [0], tags: ['branding', 'launch'] },
      { title: 'Channel description SEO', description: 'Write SEO-optimized channel description, keyword research for the channel niche.', assignedTo: 'seo' as WorkerId, category: 'marketing', priority: 'high', estimatedMinutes: 20, requiresApproval: false, requiresReview: false, dependsOnIndex: [0], tags: ['seo', 'launch'] },
      { title: 'First 3 video upload plan', description: 'Identify the first 3 videos to upload, order, and optimal timing.', assignedTo: 'marketing-director', category: 'strategy', priority: 'high', estimatedMinutes: 30, requiresApproval: false, requiresReview: true, dependsOnIndex: [1, 2], tags: ['launch', 'plan'] },
      { title: 'Write launch announcement posts', description: 'Draft social media posts for YouTube, Twitter, Instagram announcing the channel launch.', assignedTo: 'marketing-director', category: 'marketing', priority: 'medium', estimatedMinutes: 30, requiresApproval: false, requiresReview: true, dependsOnIndex: [3], tags: ['social', 'launch'] },
      { title: 'Josh approval: launch plan', description: 'Present complete launch plan for approval before going live.', assignedTo: 'project-manager', category: 'admin', priority: 'critical', estimatedMinutes: 10, requiresApproval: true, requiresReview: false, dependsOnIndex: [4], tags: ['approval', 'launch'] },
    ],
  },
  {
    id: 'weekly-content-plan',
    name: 'Weekly Content Planning',
    description: 'Generates the content plan for the coming week',
    tasks: [
      { title: 'Analytics review: last week performance', description: 'Pull metrics for all published videos from the past 7 days. Identify top performers.', assignedTo: 'analytics-director', category: 'analytics', priority: 'high', estimatedMinutes: 20, requiresApproval: false, requiresReview: false, dependsOnIndex: [], tags: ['analytics', 'weekly'] },
      { title: 'Trend research: this week', description: 'Identify trending topics across all 3 channel niches for the coming week.', assignedTo: 'research-lead', category: 'research', priority: 'high', estimatedMinutes: 30, requiresApproval: false, requiresReview: false, dependsOnIndex: [], tags: ['research', 'trends', 'weekly'] },
      { title: 'Content calendar: next 7 days', description: 'Create specific content plan for the next 7 days across all 3 channels. What to publish and when.', assignedTo: 'project-manager', category: 'strategy', priority: 'high', estimatedMinutes: 20, requiresApproval: false, requiresReview: true, dependsOnIndex: [0, 1], tags: ['plan', 'weekly'] },
      { title: 'Generate CEO weekly briefing', description: 'CEO synthesizes all inputs into a prioritized weekly briefing for Josh.', assignedTo: 'ceo', category: 'strategy', priority: 'critical', estimatedMinutes: 15, requiresApproval: false, requiresReview: true, dependsOnIndex: [2], tags: ['briefing', 'weekly'] },
    ],
  },
]

/** Generate a set of tasks from a blueprint, linked to an optional project */
export function generateTasksFromBlueprint(
  blueprintId: string,
  options: {
    projectId?: string
    episodeId?: string
    channel?: string
    createdBy?: WorkerId | 'system' | 'josh'
    dueDays?: number  // Days from now to set the final task's deadline
  } = {}
): MasterTask[] {
  const blueprint = TASK_BLUEPRINTS.find(b => b.id === blueprintId)
  if (!blueprint) return []

  const createdTasks: MasterTask[] = []
  const dueDate = options.dueDays
    ? new Date(Date.now() + options.dueDays * 86400000).toISOString()
    : null

  for (const [i, taskDef] of blueprint.tasks.entries()) {
    const dependsOn = taskDef.dependsOnIndex.map(idx => createdTasks[idx]?.id).filter(Boolean) as string[]

    const task = createTask({
      title: taskDef.title,
      description: taskDef.description,
      category: taskDef.category,
      priority: taskDef.priority,
      assignedTo: taskDef.assignedTo,
      dependsOn,
      blocks: [],
      projectId: options.projectId ?? null,
      episodeId: options.episodeId ?? null,
      channel: options.channel ?? null,
      requiresApproval: taskDef.requiresApproval,
      requiresReview: taskDef.requiresReview,
      maxRetries: 2,
      dueDate: i === blueprint.tasks.length - 1 ? dueDate : null,
      estimatedMinutes: taskDef.estimatedMinutes,
      notes: '',
      tags: taskDef.tags,
      createdBy: options.createdBy ?? 'system',
    })

    createdTasks.push(task)
  }

  // Set the blocks property on each task based on dependsOn
  for (const task of createdTasks) {
    for (const depId of task.dependsOn) {
      const depTask = loadTask(depId)
      if (depTask && !depTask.blocks.includes(task.id)) {
        updateTask(depId, { blocks: [...depTask.blocks, task.id] })
      }
    }
  }

  return createdTasks
}

// ── Bootstrap the initial task queue ──────────────────────────────────────────

/**
 * Seeds the queue with the default startup tasks that should always be present.
 * Only adds tasks that don't already exist (idempotent).
 */
export function bootstrapInitialQueue(): void {
  const existing = listAllTasks()
  if (existing.length > 0) return  // Queue already seeded

  // Seed the queue with the most important known tasks
  const initialTasks: Array<Omit<MasterTask,
    'id' | 'status' | 'attemptCount' | 'createdAt' | 'updatedAt' |
    'startedAt' | 'completedAt' | 'actualDurationMs' | 'result' | 'error'
  >> = [
    // CRITICAL: EP006 is broken
    {
      title: 'Fix EP006 Pearl Harbor — Run render_ep006.bat',
      description: 'EP006 is broken. Josh must run render_ep006.bat from C:\\Users\\jjard\\claude\\video-bot-pipeline\\ to re-render it from scratch.',
      category: 'production', priority: 'critical', assignedTo: 'engineering-lead',
      dependsOn: [], blocks: [], projectId: null, episodeId: 'EP006', channel: 'gods-glory',
      requiresApproval: true, requiresReview: true, maxRetries: 1,
      dueDate: null, estimatedMinutes: 180, notes: 'Josh must run this manually — it requires the local render environment.',
      tags: ['ep006', 'render', 'broken', 'critical'], createdBy: 'system',
    },
    // HIGH: Render Season 3
    {
      title: 'Render Gods & Glory Season 3 (EP012-EP025)',
      description: 'All 14 S3 scripts are complete. Run render_season3.bat from the video-bot-pipeline folder to render all 14 episodes.',
      category: 'production', priority: 'high', assignedTo: 'engineering-lead',
      dependsOn: [], blocks: [], projectId: null, episodeId: null, channel: 'gods-glory',
      requiresApproval: true, requiresReview: true, maxRetries: 1,
      dueDate: null, estimatedMinutes: 600, notes: '14 episodes × ~45 min each. Run overnight or in batches.',
      tags: ['season3', 'render', 'gods-glory'], createdBy: 'system',
    },
    // HIGH: Launch ML EP001
    {
      title: 'Produce Machine Learning EP001',
      description: 'ML EP001 is scripted. Needs full production pipeline: images → TTS → render → upload package.',
      category: 'production', priority: 'high', assignedTo: 'project-manager',
      dependsOn: [], blocks: [], projectId: null, episodeId: 'ML-EP001', channel: 'machine-learning',
      requiresApproval: false, requiresReview: true, maxRetries: 2,
      dueDate: null, estimatedMinutes: 300, notes: 'Use Video Factory pipeline or auto_render.py.',
      tags: ['ml', 'ep001', 'production'], createdBy: 'system',
    },
    // HIGH: Launch LO EP001
    {
      title: 'Produce Little Olympus EP001',
      description: 'LO EP001 is scripted. Needs full production pipeline: images → TTS → render → upload package.',
      category: 'production', priority: 'high', assignedTo: 'project-manager',
      dependsOn: [], blocks: [], projectId: null, episodeId: 'LO-EP001', channel: 'little-olympus',
      requiresApproval: false, requiresReview: true, maxRetries: 2,
      dueDate: null, estimatedMinutes: 300, notes: 'Use Video Factory pipeline. Children\'s story mode.',
      tags: ['lo', 'ep001', 'production'], createdBy: 'system',
    },
    // MEDIUM: Build Viral Engine website
    {
      title: 'Build Viral Engine website',
      description: 'The Viral Engine launch website needs building. Josh still needs to provide: website URL. Platform TBD.',
      category: 'engineering', priority: 'medium', assignedTo: 'engineering-lead',
      dependsOn: [], blocks: [], projectId: null, episodeId: null, channel: null,
      requiresApproval: true, requiresReview: true, maxRetries: 1,
      dueDate: null, estimatedMinutes: 480, notes: 'BLOCKED: Need website URL and platform choice from Josh.',
      tags: ['launch', 'website', 'viral-engine'], createdBy: 'system',
    },
    // MEDIUM: CEO daily briefing
    {
      title: 'Generate first Daily Executive Briefing',
      description: 'CEO worker generates the first Daily Executive Briefing covering all current projects, priorities, and recommendations.',
      category: 'strategy', priority: 'medium', assignedTo: 'ceo',
      dependsOn: [], blocks: [], projectId: null, episodeId: null, channel: null,
      requiresApproval: false, requiresReview: false, maxRetries: 2,
      dueDate: null, estimatedMinutes: 10, notes: '',
      tags: ['briefing', 'ceo', 'daily'], createdBy: 'system',
    },
    // LOW: Set up Council bots
    {
      title: 'Verify Council Bot system is running',
      description: 'Run council_run.bat and verify all 9 bots are operational. Check their logs for any errors.',
      category: 'engineering', priority: 'medium', assignedTo: 'engineering-lead',
      dependsOn: [], blocks: [], projectId: null, episodeId: null, channel: null,
      requiresApproval: false, requiresReview: false, maxRetries: 2,
      dueDate: null, estimatedMinutes: 15, notes: 'council_run.bat is at C:\\Users\\jjard\\claude\\video-bot-pipeline\\',
      tags: ['council', 'bots', 'engineering'], createdBy: 'system',
    },
  ]

  for (const t of initialTasks) {
    createTask(t)
  }
}
