import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, TrendingUp, Calendar, Filter, RefreshCw,
  ChevronRight, Activity, Zap, Target, AlertCircle,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Match {
  id: number
  home_team: string
  away_team: string
  league: string
  sport?: string
  kickoff_time: string
  status?: string
  home_prob?: number
  draw_prob?: number
  away_prob?: number
  confidence?: number
  final_ev?: number
  bet_side?: string
  entry_odds?: number
}

// ── Data hook ─────────────────────────────────────────────────────────────────

function useMatches(sport: string) {
  return useQuery<Match[]>({
    queryKey: ['matches', sport],
    queryFn: async ({ signal }) => {
      const params = sport !== 'all' ? `?sport=${sport}` : ''
      const res = await fetch(`${ENDPOINTS.gateway}/api/matches${params}`, { signal })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.error?.message || err?.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      return Array.isArray(data) ? data : data.matches ?? data.items ?? []
    },
    retry: 1,
    staleTime: 60_000,
  })
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ProbBar({ label, prob, color }: { label: string; prob?: number; color: string }) {
  const pct = prob != null ? Math.round(prob * 100) : null
  return (
    <div className="flex-1 text-center">
      <div className="text-[10px] text-white/40 mb-1 uppercase tracking-wide">{label}</div>
      <div className={cn('text-base font-bold', color)}>{pct != null ? `${pct}%` : '—'}</div>
      <div className="mt-1.5 h-1 rounded-full bg-white/10 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct ?? 0}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={cn('h-full rounded-full', color.replace('text-', 'bg-'))}
        />
      </div>
    </div>
  )
}

function MatchCard({ match, i }: { match: Match; i: number }) {
  const conf = match.confidence != null ? Math.round(match.confidence * 100) : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04 }}
      className="bg-surface-800/60 border border-white/8 rounded-xl p-5 hover:border-white/20 hover:bg-surface-800/80 transition-all group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-white/40 font-medium">{match.league}</span>
            {match.sport && (
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-white/40 capitalize">
                {match.sport}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-3 h-3 text-white/25" />
            <span className="text-xs text-white/35">{timeAgo(match.kickoff_time)}</span>
          </div>
        </div>
        {match.status && <StatusBadge status={match.status} size="sm" />}
      </div>

      {/* Teams */}
      <div className="flex items-center gap-3 mb-5">
        <div className="flex-1 text-right">
          <p className="font-semibold text-white text-sm leading-tight">{match.home_team}</p>
          <p className="text-white/35 text-xs mt-0.5">Home</p>
        </div>
        <div className="px-3 py-1.5 rounded-lg bg-surface-900/60 border border-white/8">
          <span className="text-white/50 font-bold text-sm">VS</span>
        </div>
        <div className="flex-1">
          <p className="font-semibold text-white text-sm leading-tight">{match.away_team}</p>
          <p className="text-white/35 text-xs mt-0.5">Away</p>
        </div>
      </div>

      {/* Probability bars */}
      {(match.home_prob != null || match.draw_prob != null || match.away_prob != null) && (
        <div className="flex gap-3 mb-4 px-1">
          <ProbBar label="Home" prob={match.home_prob} color="text-vit-400" />
          {match.draw_prob != null && (
            <ProbBar label="Draw" prob={match.draw_prob} color="text-white/60" />
          )}
          <ProbBar label="Away" prob={match.away_prob} color="text-emerald-400" />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-white/6">
        <div className="flex items-center gap-3">
          {conf != null && (
            <div className="flex items-center gap-1.5">
              <Target className="w-3 h-3 text-vit-400/70" />
              <span className="text-xs text-white/50">
                <span className="text-vit-400 font-medium">{conf}%</span> confidence
              </span>
            </div>
          )}
          {match.bet_side && (
            <div className="flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-yellow-400/70" />
              <span className="text-xs text-yellow-400/80 capitalize">{match.bet_side}</span>
              {match.entry_odds != null && (
                <span className="text-xs text-white/35">@ {match.entry_odds.toFixed(2)}</span>
              )}
            </div>
          )}
        </div>
        {match.final_ev != null && (
          <div className={cn(
            'text-xs font-medium font-mono',
            match.final_ev > 0 ? 'text-emerald-400' : 'text-red-400'
          )}>
            EV {match.final_ev > 0 ? '+' : ''}{(match.final_ev * 100).toFixed(1)}%
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ── Sports filter ─────────────────────────────────────────────────────────────

const SPORTS = [
  { value: 'all',        label: 'All' },
  { value: 'football',   label: 'Football' },
  { value: 'basketball', label: 'Basketball' },
  { value: 'tennis',     label: 'Tennis' },
  { value: 'cricket',    label: 'Cricket' },
]

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Matches() {
  const [sport, setSport] = useState('all')
  const { data, isLoading, isError, error, refetch, isFetching } = useMatches(sport)

  const matches = data ?? []

  return (
    <div className="pt-16 min-h-screen">
      {/* Hero */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-30" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-14">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-vit-500 to-vit-700 flex items-center justify-center shadow-lg shadow-vit-500/30">
                <Trophy className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Matches & Predictions</h1>
                <p className="text-white/40 text-sm">AI-powered sports intelligence and probability forecasts</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-7">
          {/* Sport filter */}
          <div className="flex items-center gap-1.5 p-1 bg-surface-800/60 rounded-lg border border-white/8">
            <Filter className="w-3.5 h-3.5 text-white/30 ml-2" />
            {SPORTS.map(s => (
              <button
                key={s.value}
                onClick={() => setSport(s.value)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                  sport === s.value
                    ? 'bg-vit-600 text-white'
                    : 'text-white/50 hover:text-white hover:bg-white/5',
                )}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Stats + refresh */}
          <div className="flex items-center gap-3">
            {!isLoading && !isError && (
              <div className="flex items-center gap-1.5 text-white/35 text-xs">
                <Activity className="w-3.5 h-3.5" />
                <span>{matches.length} match{matches.length !== 1 ? 'es' : ''}</span>
              </div>
            )}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-800/60 border border-white/8 text-white/50 hover:text-white hover:border-white/20 text-xs transition-all disabled:opacity-50"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', isFetching && 'animate-spin')} />
              Refresh
            </button>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Spinner className="w-8 h-8 text-vit-400" />
            <p className="text-white/40 text-sm">Loading matches…</p>
          </div>
        )}

        {/* Error */}
        {isError && !isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-20 gap-4"
          >
            <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-400" />
            </div>
            <div className="text-center">
              <p className="text-white font-medium mb-1">Could not load matches</p>
              <p className="text-white/40 text-sm">{(error as Error)?.message}</p>
            </div>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors"
            >
              Try Again
            </button>
          </motion.div>
        )}

        {/* Empty */}
        {!isLoading && !isError && matches.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-20 gap-4 text-center"
          >
            <div className="w-14 h-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
              <Trophy className="w-6 h-6 text-white/25" />
            </div>
            <div>
              <p className="text-white/60 font-medium mb-1">No matches found</p>
              <p className="text-white/30 text-sm">
                {sport !== 'all'
                  ? `No ${sport} matches available right now.`
                  : 'No upcoming matches at the moment.'}
              </p>
            </div>
            {sport !== 'all' && (
              <button
                onClick={() => setSport('all')}
                className="flex items-center gap-1.5 text-vit-400 hover:text-vit-300 text-sm transition-colors"
              >
                View all sports <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </motion.div>
        )}

        {/* Match grid */}
        {!isLoading && !isError && matches.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {matches.map((m, i) => (
              <MatchCard key={m.id} match={m} i={i} />
            ))}
          </div>
        )}

        {/* Explore predictions CTA */}
        {!isLoading && (
          <div className="mt-12 rounded-2xl bg-gradient-to-br from-vit-900/40 to-surface-800/40 border border-vit-500/20 p-8 text-center">
            <TrendingUp className="w-8 h-8 text-vit-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">AI Prediction Engine</h3>
            <p className="text-white/40 text-sm max-w-md mx-auto mb-5">
              Submit a match for real-time analysis across 13+ ML models with market-calibrated probabilities.
            </p>
            <a
              href={`${ENDPOINTS.gateway}/docs#/Predict`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors shadow-lg shadow-vit-600/25"
            >
              Open API Reference <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
