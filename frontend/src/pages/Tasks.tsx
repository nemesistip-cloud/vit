import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Trophy, Zap, CheckCircle2, Clock, Lock, Star,
  Target, Gift, ChevronRight, Flame, BarChart3, AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Task {
  id: number | string
  title: string
  description: string
  category?: string
  reward_xp?: number
  reward_vit?: number
  status: 'available' | 'in_progress' | 'completed' | 'locked' | string
  progress?: number
  progress_max?: number
  action_url?: string
  expires_at?: string | null
}

interface XPSummary {
  level: number
  xp: number
  xp_for_next_level: number
  total_xp: number
  rank?: string
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useTasks() {
  return useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/tasks`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.tasks ?? d.items ?? []
    },
    retry: false,
    staleTime: 30_000,
  })
}

function useXP() {
  return useQuery<XPSummary | null>({
    queryKey: ['xp-summary'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/users/me/xp`, { signal, headers: authHeaders() })
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
  const qc = useQueryClient()
  const navigate = useNavigate()
  const isCompleted = task.status === 'completed'
  const isLocked    = task.status === 'locked'
  const catColor    = CAT_COLOR[task.category ?? ''] ?? 'text-white/40'
  const catBg       = CAT_BG[task.category ?? '']   ?? 'bg-white/5'
  const pct         = task.progress != null && task.progress_max
    ? Math.round((task.progress / task.progress_max) * 100)
    : null

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/tasks/${task.id}/complete`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? 'Could not claim reward')
      return d
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
      qc.invalidateQueries({ queryKey: ['xp-summary'] })
      const reward = [
        d.xp_earned   && `+${d.xp_earned} XP`,
        d.vit_earned  && `+${d.vit_earned} VIT`,
      ].filter(Boolean).join(' · ')
      toast.success(`Task claimed!${reward ? ` ${reward}` : ''}`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

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
        {task.category && (
          <span className={cn('mt-0.5 px-2 py-0.5 rounded-md text-[10px] font-medium capitalize shrink-0', catBg, catColor)}>
            {task.category}
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
          {task.reward_xp  && <span className="flex items-center gap-1 text-amber-400"><Star className="w-3 h-3" />+{task.reward_xp} XP</span>}
          {task.reward_vit && <span className="flex items-center gap-1 text-emerald-400"><Zap className="w-3 h-3" />+{task.reward_vit} VIT</span>}
        </div>

        {!isCompleted && !isLocked && (
          task.action_url ? (
            <button
              onClick={() => navigate(task.action_url!)}
              className="flex items-center gap-1 text-xs text-vit-400 hover:text-vit-300 transition-colors"
            >
              Start <ChevronRight className="w-3 h-3" />
            </button>
          ) : pct != null && pct >= 100 ? (
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/15 text-emerald-400 text-xs font-medium hover:bg-emerald-500/25 disabled:opacity-50 transition-colors"
            >
              {mutation.isPending ? 'Claiming…' : '✓ Claim'}
            </button>
          ) : null
        )}
      </div>
    </motion.div>
  )
}

// ── XP bar ────────────────────────────────────────────────────────────────────

function XPBar({ xp }: { xp: XPSummary }) {
  const pct = xp.xp_for_next_level > 0
    ? Math.round((xp.xp / xp.xp_for_next_level) * 100)
    : 100

  return (
    <div className="bg-surface-800/60 border border-white/8 rounded-2xl p-5 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/20 flex items-center justify-center">
            <Flame className="w-4.5 h-4.5 text-amber-400" />
          </div>
          <div>
            <p className="text-xs text-white/40">Your level</p>
            <p className="font-bold text-white">Level {xp.level}{xp.rank && ` · ${xp.rank}`}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-white/40">Total XP</p>
          <p className="font-bold text-amber-400">{(xp.total_xp ?? xp.xp).toLocaleString()}</p>
        </div>
      </div>
      <div className="space-y-1.5">
        <div className="flex justify-between text-[10px] text-white/30">
          <span>{xp.xp.toLocaleString()} XP</span>
          <span>{xp.xp_for_next_level.toLocaleString()} XP to Level {xp.level + 1}</span>
        </div>
        <div className="h-2 rounded-full bg-white/8 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400"
          />
        </div>
      </div>
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
  const { data: tasks = [], isLoading } = useTasks()
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
          <p className="text-white/45 text-sm">Complete tasks to earn XP, level up, and claim VIT rewards.</p>
        </motion.div>

        {/* XP bar */}
        {xp && <XPBar xp={xp} />}

        {/* Progress summary */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'Completed',  value: completedCount, icon: CheckCircle2, color: 'text-emerald-400' },
            { label: 'Available',  value: tasks.filter(t => t.status === 'available').length, icon: Target, color: 'text-vit-400' },
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
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
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

