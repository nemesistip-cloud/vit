import { useState, type ElementType } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, Medal, TrendingUp, Users, Star, ChevronRight,
  RefreshCw, Target, Zap, Activity, Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { authHeaders } from '@/hooks/useAuth'

type Tab    = 'predictors' | 'validators'
type Period = 'weekly' | 'monthly' | 'all-time'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Predictor {
  rank?: number
  user_id?: string
  username?: string
  display_name?: string
  total_predictions?: number
  correct_predictions?: number
  accuracy?: number
  roi?: number
  total_stake?: number
  vitcoin_earned?: number
  streak?: number
  tier?: string
}

interface Validator {
  rank?: number
  node_id?: string
  address?: string
  display_name?: string
  blocks_validated?: number
  uptime_pct?: number
  stake_amount?: number
  rewards_earned?: number
  reputation_score?: number
  status?: string
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

function useLeaderboard(tab: Tab, period: Period) {
  return useQuery<(Predictor | Validator)[]>({
    queryKey: ['leaderboard', tab, period],
    queryFn: async ({ signal }) => {
      const endpoint = tab === 'validators'
        ? `${ENDPOINTS.gateway}/api/analytics/leaderboard/validators`
        : `${ENDPOINTS.gateway}/api/analytics/leaderboard/users`
      const r = await fetch(`${endpoint}?period=${period}`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.items ?? d.users ?? d.validators ?? []
    },
    staleTime: 60_000,
    retry: false,
  })
}

function useGlobalStats() {
  return useQuery({
    queryKey: ['leaderboard-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/analytics/stats`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 120_000,
    retry: false,
  })
}

// ── Sub-components ────────────────────────────────────────────────────────────

const MEDAL_COLORS = ['text-amber-400', 'text-slate-300', 'text-amber-600']
const MEDAL_BG     = ['bg-amber-500/10 border-amber-500/25', 'bg-slate-400/10 border-slate-400/25', 'bg-amber-600/10 border-amber-600/25']

function RankBadge({ rank }: { rank: number }) {
  if (rank <= 3) {
    return (
      <div className={cn('w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0', MEDAL_BG[rank - 1])}>
        <Medal className={cn('w-4 h-4', MEDAL_COLORS[rank - 1])} />
      </div>
    )
  }
  return (
    <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
      <span className="text-xs font-bold text-white/40">#{rank}</span>
    </div>
  )
}

function PredictorRow({ entry, rank, i }: { entry: Predictor; rank: number; i: number }) {
  const name     = entry.display_name ?? entry.username ?? `User #${entry.user_id ?? rank}`
  const accuracy = entry.accuracy != null ? Math.round(entry.accuracy * 100) : null
  const roi      = entry.roi != null ? entry.roi.toFixed(1) : null
  const earned   = entry.vitcoin_earned != null ? Number(entry.vitcoin_earned).toLocaleString() : null

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.05 }}
      className="flex items-center gap-4 px-5 py-4 rounded-xl bg-white/3 border border-white/6 hover:border-vit-500/20 hover:bg-white/5 transition-all group"
    >
      <RankBadge rank={rank} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-white truncate">{name}</p>
          {entry.tier && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-vit-500/15 text-vit-300 font-medium uppercase">{entry.tier}</span>
          )}
          {(entry.streak ?? 0) >= 3 && (
            <span className="flex items-center gap-0.5 text-[10px] text-amber-400">
              <Zap className="w-3 h-3" />{entry.streak}
            </span>
          )}
        </div>
        <p className="text-xs text-white/35 mt-0.5">
          {entry.total_predictions ?? 0} predictions
          {entry.correct_predictions != null ? ` · ${entry.correct_predictions} correct` : ''}
        </p>
      </div>

      <div className="hidden sm:flex items-center gap-6 text-right">
        {accuracy != null && (
          <div>
            <p className={cn('text-sm font-bold', accuracy >= 60 ? 'text-emerald-400' : accuracy >= 50 ? 'text-vit-400' : 'text-white/50')}>
              {accuracy}%
            </p>
            <p className="text-[10px] text-white/30">accuracy</p>
          </div>
        )}
        {roi != null && (
          <div>
            <p className={cn('text-sm font-bold', Number(roi) >= 0 ? 'text-emerald-400' : 'text-red-400')}>
              {Number(roi) >= 0 ? '+' : ''}{roi}%
            </p>
            <p className="text-[10px] text-white/30">ROI</p>
          </div>
        )}
        {earned != null && (
          <div>
            <p className="text-sm font-bold text-amber-400">{earned}</p>
            <p className="text-[10px] text-white/30">VIT earned</p>
          </div>
        )}
      </div>

      <ChevronRight className="w-4 h-4 text-white/15 group-hover:text-vit-400 transition-colors flex-shrink-0" />
    </motion.div>
  )
}

function ValidatorRow({ entry, rank, i }: { entry: Validator; rank: number; i: number }) {
  const name    = entry.display_name ?? entry.address?.slice(0, 12) ?? `Node #${rank}`
  const uptime  = entry.uptime_pct != null ? Math.round(entry.uptime_pct) : null
  const rewards = entry.rewards_earned != null ? Number(entry.rewards_earned).toLocaleString() : null

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.05 }}
      className="flex items-center gap-4 px-5 py-4 rounded-xl bg-white/3 border border-white/6 hover:border-cyan-500/20 hover:bg-white/5 transition-all group"
    >
      <RankBadge rank={rank} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-white font-mono truncate">{name}</p>
          {entry.status && (
            <span className={cn(
              'px-1.5 py-0.5 rounded text-[10px] font-medium uppercase',
              entry.status === 'active' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-white/5 text-white/40'
            )}>{entry.status}</span>
          )}
        </div>
        <p className="text-xs text-white/35 mt-0.5">
          {entry.blocks_validated ?? 0} blocks validated
          {entry.stake_amount != null ? ` · ${Number(entry.stake_amount).toLocaleString()} VIT staked` : ''}
        </p>
      </div>

      <div className="hidden sm:flex items-center gap-6 text-right">
        {uptime != null && (
          <div>
            <p className={cn('text-sm font-bold', uptime >= 99 ? 'text-emerald-400' : uptime >= 95 ? 'text-vit-400' : 'text-amber-400')}>
              {uptime}%
            </p>
            <p className="text-[10px] text-white/30">uptime</p>
          </div>
        )}
        {rewards != null && (
          <div>
            <p className="text-sm font-bold text-amber-400">{rewards}</p>
            <p className="text-[10px] text-white/30">VIT rewards</p>
          </div>
        )}
        {entry.reputation_score != null && (
          <div>
            <p className="text-sm font-bold text-purple-400">{entry.reputation_score}</p>
            <p className="text-[10px] text-white/30">reputation</p>
          </div>
        )}
      </div>

      <ChevronRight className="w-4 h-4 text-white/15 group-hover:text-cyan-400 transition-colors flex-shrink-0" />
    </motion.div>
  )
}

function EmptyState({ tab }: { tab: Tab }) {
  const steps = tab === 'predictors'
    ? [
        { icon: Target,   label: 'Make predictions',  desc: 'Submit AI-backed match forecasts on any live fixture.' },
        { icon: TrendingUp, label: 'Build accuracy',  desc: 'Your win rate, ROI, and streak are tracked automatically.' },
        { icon: Trophy,   label: 'Earn VIT rewards',  desc: 'Top weekly predictors receive VIT coin distributions.' },
      ]
    : [
        { icon: Shield,   label: 'Run a validator node',  desc: 'Stake VIT and join the consensus network.' },
        { icon: Activity, label: 'Validate blocks',       desc: 'Earn rewards for each block you sign and attest.' },
        { icon: Star,     label: 'Build reputation',      desc: 'High-uptime validators unlock elite node tiers.' },
      ]

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-12">
      <div className="text-center mb-10">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4">
          <Trophy className="w-8 h-8 text-amber-400/50" />
        </div>
        <p className="text-white/60 font-medium mb-1">No rankings yet</p>
        <p className="text-white/30 text-sm">
          {tab === 'predictors'
            ? 'Rankings populate as predictions are made and validated.'
            : 'Validator rankings appear once nodes are active on the network.'}
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4 max-w-2xl mx-auto">
        {steps.map(({ icon: Icon, label, desc }, i) => (
          <div key={label} className="p-5 rounded-xl bg-white/3 border border-white/6 text-center">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mx-auto mb-3">
              <Icon className="w-5 h-5 text-white/40" />
            </div>
            <p className="text-sm font-medium text-white/70 mb-1">{i + 1}. {label}</p>
            <p className="text-xs text-white/30">{desc}</p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const TAB_DEFS: { key: Tab; label: string; icon: ElementType }[] = [
  { key: 'predictors', label: 'Predictors', icon: TrendingUp },
  { key: 'validators', label: 'Validators', icon: Shield },
]

const PERIOD_DEFS: { key: Period; label: string }[] = [
  { key: 'weekly',   label: 'This Week' },
  { key: 'monthly',  label: 'Month' },
  { key: 'all-time', label: 'All Time' },
]

export default function Leaderboard() {
  const [tab, setTab]       = useState<Tab>('predictors')
  const [period, setPeriod] = useState<Period>('weekly')
  const { data = [], isLoading, refetch, isFetching } = useLeaderboard(tab, period)
  const { data: stats } = useGlobalStats()

  return (
    <div className="pt-16 min-h-screen">
      {/* Header ────────────────────────────────────────────────────────────── */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Trophy className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Leaderboard</h1>
              <p className="text-white/50 text-sm">Top predictors and validators on VIT Network</p>
            </div>
            <button
              onClick={() => refetch()}
              className="ml-auto p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/8 transition-colors"
            >
              <RefreshCw className={cn('w-4 h-4 text-white/40', isFetching && 'animate-spin')} />
            </button>
          </motion.div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
        {/* Global stats ────────────────────────────────────────────────────── */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            {[
              { icon: Users,      label: 'Total Users',       value: stats.total_users ?? stats.users ?? '—',         color: 'bg-vit-500/10 text-vit-400' },
              { icon: Target,     label: 'Predictions Made',  value: stats.total_predictions ?? stats.predictions ?? '—', color: 'bg-emerald-500/10 text-emerald-400' },
              { icon: TrendingUp, label: 'Avg Accuracy',      value: stats.avg_accuracy ? `${Math.round(stats.avg_accuracy * 100)}%` : '—', color: 'bg-amber-500/10 text-amber-400' },
              { icon: Zap,        label: 'VIT Distributed',   value: stats.vit_distributed ? `${Number(stats.vit_distributed).toLocaleString()}` : '—', color: 'bg-purple-500/10 text-purple-400' },
            ].map(({ icon: Icon, label, value, color }) => (
              <div key={label} className="bg-surface-800/60 border border-white/8 rounded-xl p-4">
                <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center mb-2', color.split(' ')[0])}>
                  <Icon className={cn('w-3.5 h-3.5', color.split(' ')[1])} />
                </div>
                <p className="text-lg font-bold text-white">{value}</p>
                <p className="text-xs text-white/35">{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tabs & period ───────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex items-center gap-1 p-1 bg-white/5 border border-white/8 rounded-xl">
            {TAB_DEFS.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                  tab === t.key ? 'bg-white/10 text-white shadow-sm' : 'text-white/40 hover:text-white/60'
                )}
              >
                <t.icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 p-1 bg-white/5 border border-white/8 rounded-xl">
            {PERIOD_DEFS.map(p => (
              <button
                key={p.key}
                onClick={() => setPeriod(p.key)}
                className={cn(
                  'px-3 py-2 rounded-lg text-sm font-medium transition-all',
                  period === p.key ? 'bg-white/10 text-white shadow-sm' : 'text-white/40 hover:text-white/60'
                )}
              >
                {p.label}
              </button>
            ))}
          </div>

          <span className="ml-auto text-xs text-white/30">
            {isLoading ? 'Loading…' : `${data.length} ranked`}
          </span>
        </div>

        {/* List ────────────────────────────────────────────────────────────── */}
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner className="w-6 h-6 text-vit-400" /></div>
        ) : data.length === 0 ? (
          <EmptyState tab={tab} />
        ) : (
          <div className="space-y-2">
            {data.map((entry, i) =>
              tab === 'predictors'
                ? <PredictorRow key={i} entry={entry as Predictor} rank={i + 1} i={i} />
                : <ValidatorRow key={i} entry={entry as Validator}  rank={i + 1} i={i} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
