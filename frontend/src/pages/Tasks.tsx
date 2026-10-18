import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, Zap, CheckCircle2, Clock, Lock, Star,
  Target, Gift, ChevronRight, Flame, BarChart3, AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Task {
  id: number | string
  title: string
  description: string
  category?: string | { name: string }
  xp_reward?: number
  vit_reward?: number
  required_count: number
  max_completions: number
  status: 'available' | 'in_progress' | 'completed' | 'locked' | string
  progress?: number
  progress_max?: number
  completed_count?: number
  action_url?: string
  expires_at?: string | null
}

interface TaskProgress {
  task_id: number
  current_progress: number
  required_progress: number
  is_completed: boolean
  completed_count: number
  next_reset_at?: string | null
}

interface XPSummary {
  total_tasks_attempted: number
  total_completions: number
  total_vit_earned: number
  total_xp_earned: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useTasks() {
  return useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async ({ signal }) => {
      const headers = authHeaders()
      const [tasksResponse, progressResponse] = await Promise.all([
        fetch(`${ENDPOINTS.gateway}/api/tasks`, { signal, headers }),
        fetch(`${ENDPOINTS.gateway}/api/tasks/user/progress`, { signal, headers }),
      ])
      if (!tasksResponse.ok) throw new Error(`Tasks could not be loaded (${tasksResponse.status})`)
      if (!progressResponse.ok) throw new Error(`Task progress could not be loaded (${progressResponse.status})`)

      const tasks = await tasksResponse.json()
      const progress: TaskProgress[] = await progressResponse.json()
      if (!Array.isArray(tasks) || !Array.isArray(progress)) {
        throw new Error('Task service returned an invalid response')
      }
      const progressByTask = new Map(progress.map(item => [item.task_id, item]))

      return tasks.map((task: Task) => {
        const completion = progressByTask.get(Number(task.id))
        const completedCount = completion?.completed_count ?? 0
        const isAtCompletionLimit = completedCount >= task.max_completions
        const isCompleted = completion?.is_completed || isAtCompletionLimit
        const isWaitingForReset = Boolean(
          completion?.next_reset_at && new Date(completion.next_reset_at).getTime() > Date.now(),
        )

        return {
          ...task,
          status: isCompleted
            ? 'completed'
            : isWaitingForReset
              ? 'locked'
              : completion && completion.current_progress > 0
                ? 'in_progress'
                : task.status === 'active'
                  ? 'available'
                  : task.status,
          progress: completion?.current_progress ?? 0,
          progress_max: completion?.required_progress ?? task.required_count,
          completed_count: completedCount,
        }
      })
    },
    retry: false,
    staleTime: 30_000,
  })
}

function useXP() {
  return useQuery<XPSummary | null>({
    queryKey: ['xp-summary'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/tasks/user/stats`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 60_000,
  })
}

// ── Category colours ──────────────────────────────────────────────────────────

const CAT_COLOR: Record<string, string> = {
  prediction: 'text-vit-400',
  social:     'text-sky-400',
  defi:       'text-teal-400',
  governance: 'text-cyan-400',
  wallet:     'text-emerald-400',
  referral:   'text-orange-400',
  daily:      'text-amber-400',
  onboarding: 'text-purple-400',
}

const CAT_BG: Record<string, string> = {
  prediction: 'bg-vit-500/10',
  social:     'bg-sky-500/10',
  defi:       'bg-teal-500/10',
  governance: 'bg-cyan-500/10',
  wallet:     'bg-emerald-500/10',
  referral:   'bg-orange-500/10',
  daily:      'bg-amber-500/10',
  onboarding: 'bg-purple-500/10',
}

// ── Task card ─────────────────────────────────────────────────────────────────

function TaskCard({ task, i }: { task: Task; i: number }) {
  const navigate = useNavigate()
  const isCompleted = task.status === 'completed'
  const isLocked    = task.status === 'locked'
  const category    = typeof task.category === 'string' ? task.category : task.category?.name
  const catColor    = CAT_COLOR[category ?? ''] ?? 'text-white/40'
  const catBg       = CAT_BG[category ?? '']   ?? 'bg-white/5'
  const pct         = task.progress != null && task.progress_max
    ? Math.round((task.progress / task.progress_max) * 100)
    : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04 }}
      className={cn(
        'relative p-5 rounded-xl border transition-colors',
        isCompleted ? 'bg-emerald-500/5 border-emerald-500/20' :
        isLocked    ? 'bg-surface-800/30 border-white/5 opacity-60' :
                     'bg-surface-800/60 border-white/8 hover:border-white/14',
      )}
    >
      {/* Completed overlay */}
      {isCompleted && (
        <div className="absolute top-3 right-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        </div>
      )}
      {isLocked && (
        <div className="absolute top-3 right-3">
          <Lock className="w-4 h-4 text-white/20" />
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        {category && (
          <span className={cn('mt-0.5 px-2 py-0.5 rounded-md text-[10px] font-medium capitalize shrink-0', catBg, catColor)}>
          {category}
          </span>
        )}
      </div>

      <h3 className={cn('font-semibold text-sm mb-1', isLocked ? 'text-white/35' : 'text-white')}>
        {task.title}
      </h3>
      <p className="text-xs text-white/40 mb-3 leading-relaxed">{task.description}</p>

      {/* Progress bar */}
      {pct != null && !isCompleted && (
        <div className="mb-3">
          <div className="flex justify-between text-[10px] text-white/35 mb-1">
            <span>{task.progress} / {task.progress_max}</span>
            <span>{pct}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-white/8 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
              className="h-full rounded-full bg-vit-500"
            />
          </div>
        </div>
      )}

      {/* Rewards + action */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs">
          {task.xp_reward  && <span className="flex items-center gap-1 text-amber-400"><Star className="w-3 h-3" />+{task.xp_reward} XP</span>}
          {task.vit_reward && <span className="flex items-center gap-1 text-emerald-400"><Zap className="w-3 h-3" />+{task.vit_reward} VIT</span>}
        </div>

        {!isCompleted && !isLocked && (
          task.action_url ? (
            <button
              onClick={() => navigate(task.action_url!)}
              className="flex items-center gap-1 text-xs text-vit-400 hover:text-vit-300 transition-colors"
            >
              Start <ChevronRight className="w-3 h-3" />
            </button>
          ) : task.status === 'in_progress' ? (
            <span className="text-xs text-white/40">In progress</span>
          ) : null
        )}
      </div>
    </motion.div>
  )
}

// ── XP bar ────────────────────────────────────────────────────────────────────

function XPBar({ stats }: { stats: XPSummary }) {
  return (
    <div className="bg-surface-800/60 border border-white/8 rounded-2xl p-5 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/20 flex items-center justify-center">
            <Flame className="w-4.5 h-4.5 text-amber-400" />
          </div>
          <div>
            <p className="text-xs text-white/40">Task rewards</p>
            <p className="font-bold text-white">{stats.total_completions.toLocaleString()} completed</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-white/40">XP earned</p>
          <p className="font-bold text-amber-400">{stats.total_xp_earned.toLocaleString()}</p>
        </div>
      </div>
      <p className="mt-3 text-xs text-white/35">
        {stats.total_tasks_attempted.toLocaleString()} tasks attempted
        {' · '}
        {stats.total_vit_earned.toLocaleString()} VIT earned
      </p>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

type Filter = 'all' | 'available' | 'completed'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all',       label: 'All'       },
  { key: 'available', label: 'Available' },
  { key: 'completed', label: 'Completed' },
]

export default function Tasks() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('available')
  const { data: tasks = [], isLoading, isError, error, refetch } = useTasks()
  const { data: xp } = useXP()

  useEffect(() => {
    if (!getAuthToken()) navigate('/login')
  }, [navigate])

  const filtered = tasks.filter(t => {
    if (filter === 'available') return t.status !== 'completed' && t.status !== 'locked'
    if (filter === 'completed') return t.status === 'completed'
    return true
  })

  const completedCount = tasks.filter(t => t.status === 'completed').length
  const totalCount     = tasks.filter(t => t.status !== 'locked').length

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-3xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h1 className="text-2xl font-bold text-white">Tasks & Rewards</h1>
          </div>
          <p className="text-white/45 text-sm">Complete tasks to earn XP and VIT rewards.</p>
        </motion.div>

        {/* XP bar */}
        {xp && <XPBar stats={xp} />}

        {/* Progress summary */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'Completed',  value: completedCount, icon: CheckCircle2, color: 'text-emerald-400' },
            { label: 'Available',  value: tasks.filter(t => t.status !== 'completed' && t.status !== 'locked').length, icon: Target, color: 'text-vit-400' },
            { label: 'Total',      value: totalCount,     icon: BarChart3,    color: 'text-white/60'   },
          ].map(s => (
            <div key={s.label} className="bg-surface-800/50 border border-white/8 rounded-xl p-3.5 text-center">
              <s.icon className={cn('w-4 h-4 mx-auto mb-1.5', s.color)} />
              <p className={cn('text-xl font-bold', s.color)}>{s.value}</p>
              <p className="text-[11px] text-white/35">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex gap-1.5 mb-5">
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                'px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors',
                filter === f.key ? 'bg-vit-600 text-white' : 'bg-white/5 text-white/50 hover:text-white hover:bg-white/8',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Tasks */}
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>
        ) : isError ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <AlertCircle className="w-8 h-8 text-amber-400/80" />
            <p className="text-sm text-white/70">Tasks could not be loaded.</p>
            <p className="max-w-sm text-xs text-white/35">
              {error instanceof Error ? error.message : 'Check your connection and try again.'}
            </p>
            <button
              onClick={() => void refetch()}
              className="px-3 py-1.5 rounded-lg border border-white/10 text-xs text-white/60 hover:text-white"
            >
              Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-white/40">
            <Gift className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              {filter === 'completed' ? 'No completed tasks yet — start earning!' : 'No tasks available right now.'}
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {filtered.map((t, i) => <TaskCard key={t.id} task={t} i={i} />)}
          </div>
        )}
      </div>
    </div>
  )
}
