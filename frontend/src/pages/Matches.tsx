import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, TrendingUp, Calendar, Filter, RefreshCw,
  ChevronRight, Activity, Zap, Target, AlertCircle,
  Search, Clock, CheckCircle, Radio, Flame,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'

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
  home_score?: number
  away_score?: number
}

type Tab = 'upcoming' | 'live' | 'recent' | 'all'
type Sport = 'all' | 'football' | 'basketball' | 'tennis' | 'cricket'

function useMatches(tab: Tab, sport: Sport) {
  const endpoint = tab === 'upcoming' ? '/api/matches/upcoming'
    : tab === 'live' ? '/api/matches/live'
    : tab === 'recent' ? '/api/matches/recent'
    : '/api/matches'

  return useQuery<Match[]>({
    queryKey: ['matches', tab, sport],
    queryFn: async ({ signal }) => {
      const params = sport !== 'all' ? `?sport=${sport}` : ''
      const res = await fetch(`${ENDPOINTS.gateway}${endpoint}${params}`, { signal })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.error?.message || err?.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      return Array.isArray(data) ? data : data.matches ?? data.items ?? []
    },
    retry: 1,
    staleTime: tab === 'live' ? 15_000 : 60_000,
    refetchInterval: tab === 'live' ? 20_000 : false,
  })
}

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
  const navigate = useNavigate()
  const conf = match.confidence != null ? Math.round(match.confidence * 100) : null
  const isLive = match.status?.toLowerCase() === 'live' || match.status?.toLowerCase() === 'in_play'

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04 }}
      onClick={() => navigate(`/matches/${match.id}`)}
      className="bg-surface-800/60 border border-white/8 rounded-xl p-5 hover:border-vit-500/30 hover:bg-surface-800/80 transition-all group cursor-pointer relative overflow-hidden"
    >
      {isLive && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500 to-emerald-400" />
      )}
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-white/40 font-medium">{match.league}</span>
            {match.sport && (
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-white/40 capitalize">{match.sport}</span>
            )}
            {isLive && (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-medium">
                <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />LIVE
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-3 h-3 text-white/25" />
            <span className="text-xs text-white/35">{timeAgo(match.kickoff_time)}</span>
          </div>
        </div>
        {match.status && !isLive && <StatusBadge status={match.status} size="sm" />}
      </div>

      {/* Teams & Score */}
      <div className="flex items-center gap-3 mb-5">
        <div className="flex-1 text-right">
          <p className="font-semibold text-white text-sm leading-tight">{match.home_team}</p>
          {match.home_score != null && <p className="text-2xl font-bold text-white mt-1">{match.home_score}</p>}
        </div>
        <div className="flex flex-col items-center gap-1">
          {isLive ? (
            <span className="text-emerald-400 text-xs font-bold">LIVE</span>
          ) : (
            <span className="text-white/30 text-xs font-medium">vs</span>
          )}
        </div>
        <div className="flex-1 text-left">
          <p className="font-semibold text-white text-sm leading-tight">{match.away_team}</p>
          {match.away_score != null && <p className="text-2xl font-bold text-white mt-1">{match.away_score}</p>}
        </div>
      </div>

      {/* Probability bars */}
      {(match.home_prob != null || match.draw_prob != null || match.away_prob != null) && (
        <div className="flex gap-3 mb-4 py-3 border-t border-b border-white/6">
          <ProbBar label="Home" prob={match.home_prob} color="text-vit-400" />
          <ProbBar label="Draw" prob={match.draw_prob} color="text-white/60" />
          <ProbBar label="Away" prob={match.away_prob} color="text-amber-400" />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-white/40 mt-3">
        <div className="flex items-center gap-3">
          {conf != null && (
            <span className="flex items-center gap-1">
              <Target className="w-3 h-3 text-vit-400" />
              <span className="text-vit-400 font-medium">{conf}%</span>
              <span>confidence</span>
            </span>
          )}
          {match.final_ev != null && (
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400 font-medium">EV {match.final_ev > 0 ? '+' : ''}{match.final_ev?.toFixed(2)}</span>
            </span>
          )}
          {match.bet_side && (
            <span className="px-2 py-0.5 rounded-full bg-vit-500/15 text-vit-300 text-[10px] font-medium uppercase">
              {match.bet_side}
            </span>
          )}
        </div>
        <span className="flex items-center gap-1 text-white/20 group-hover:text-vit-400 transition-colors">
          Details <ChevronRight className="w-3 h-3" />
        </span>
      </div>
    </motion.div>
  )
}

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: 'upcoming', label: 'Upcoming', icon: Clock },
  { key: 'live',     label: 'Live',     icon: Radio },
  { key: 'recent',   label: 'Recent',   icon: CheckCircle },
  { key: 'all',      label: 'All',      icon: Filter },
]

const SPORTS: { key: Sport; label: string }[] = [
  { key: 'all',        label: 'All Sports' },
  { key: 'football',   label: 'Football' },
  { key: 'basketball', label: 'Basketball' },
  { key: 'tennis',     label: 'Tennis' },
  { key: 'cricket',    label: 'Cricket' },
]

export default function Matches() {
  const [tab, setTab]     = useState<Tab>('upcoming')
  const [sport, setSport] = useState<Sport>('all')
  const [search, setSearch] = useState('')
  const { data, isLoading, isError, error, refetch } = useMatches(tab, sport)

  const filtered = (data ?? []).filter(m => {
    if (!search) return true
    const q = search.toLowerCase()
    return m.home_team.toLowerCase().includes(q) ||
      m.away_team.toLowerCase().includes(q) ||
      m.league.toLowerCase().includes(q)
  })

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                <Trophy className="w-5 h-5 text-vit-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Matches & Predictions</h1>
                <p className="text-white/50 text-sm">AI-powered sports intelligence and probability forecasts</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Tab bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-xl p-1">
            {TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all',
                  tab === t.key
                    ? 'bg-vit-500 text-white shadow-lg shadow-vit-500/20'
                    : 'text-white/50 hover:text-white hover:bg-white/5',
                )}
              >
                <t.icon className={cn('w-4 h-4', t.key === 'live' && tab === t.key && 'animate-pulse')} />
                {t.label}
                {t.key === 'live' && tab === 'live' && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                )}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              placeholder="Search teams or leagues..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-500/50 focus:bg-white/8 transition-colors"
            />
          </div>

          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm text-white/60 hover:text-white hover:bg-white/10 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Sport filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          {SPORTS.map(s => (
            <button
              key={s.key}
              onClick={() => setSport(s.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
                sport === s.key
                  ? 'bg-vit-500/20 border-vit-500/40 text-vit-300'
                  : 'bg-white/5 border-white/10 text-white/50 hover:text-white hover:border-white/20',
              )}
            >
              {s.label}
            </button>
          ))}
          <span className="ml-auto text-xs text-white/30 flex items-center">
            {isLoading ? 'Loading…' : `${filtered.length} match${filtered.length !== 1 ? 'es' : ''}`}
          </span>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Spinner className="w-8 h-8 text-vit-400" />
            <p className="text-white/40 text-sm">Loading {tab} matches…</p>
          </div>
        ) : isError ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-24">
            <AlertCircle className="w-12 h-12 text-red-400/60 mx-auto mb-4" />
            <p className="text-white/60 font-medium">Failed to load matches</p>
            <p className="text-white/30 text-sm mt-1">{(error as Error)?.message}</p>
            <button onClick={() => refetch()} className="mt-4 px-4 py-2 rounded-lg bg-vit-500/20 text-vit-400 text-sm hover:bg-vit-500/30 transition-colors">
              Try again
            </button>
          </motion.div>
        ) : filtered.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-24">
            <Trophy className="w-14 h-14 text-white/10 mx-auto mb-4" />
            <p className="text-white/60 font-medium">No {tab} matches</p>
            <p className="text-white/30 text-sm mt-1">
              {tab === 'live' ? 'No matches in play right now.' :
               tab === 'upcoming' ? 'No fixtures scheduled in the next 48 hours.' :
               tab === 'recent' ? 'No results from the last 24 hours.' :
               search ? 'No matches match your search.' : 'No matches found.'}
            </p>
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map((m, i) => <MatchCard key={m.id} match={m} i={i} />)}
          </div>
        )}

        {/* AI Engine CTA */}
        {!isLoading && filtered.length === 0 && tab === 'upcoming' && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-8 rounded-2xl border border-vit-500/20 bg-gradient-to-br from-vit-500/5 to-transparent p-8 text-center"
          >
            <Zap className="w-8 h-8 text-vit-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">AI Prediction Engine Ready</h3>
            <p className="text-white/50 text-sm mb-4 max-w-md mx-auto">
              Submit a match for real-time analysis across 13+ ML models with market-calibrated probabilities.
            </p>
            <a href="/developers" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white text-sm font-medium transition-colors">
              Open API Reference <ChevronRight className="w-4 h-4" />
            </a>
          </motion.div>
        )}
      </div>
    </div>
  )
}
