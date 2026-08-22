import { useState, type ElementType } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Trophy, Brain, TrendingUp, Calendar, ChevronRight, Activity,
  Zap, Target, Search, Clock, CheckCircle, Radio,
  RotateCcw, RefreshCw, Dumbbell, Circle,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Skeleton } from '@/components/ui/Skeleton'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

interface Match {
  id: number
  match_id?: number
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
  home_goals?: number
  away_goals?: number
}

type Tab   = 'upcoming' | 'live' | 'recent' | 'all'
type Sport = 'all' | 'football' | 'basketball' | 'tennis' | 'cricket'

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useMatches(tab: Tab, sport: Sport) {
  const endpoint =
    tab === 'upcoming' ? '/api/matches/upcoming'
    : tab === 'live'   ? '/api/matches/live'
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
      const payload = await res.json()
      const rawRows: unknown[] = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.matches)
          ? payload.matches
          : Array.isArray(payload?.items)
            ? payload.items
            : Array.isArray(payload?.data)
              ? payload.data
              : []

      // The gateway uses match_id/home_goals/away_goals while older clients
      // use id/home_score/away_score. Normalize at the API boundary so every
      // tab and card renders the same contract.
      return rawRows
        .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
        .map((row) => ({
          ...row,
          id: Number(row.id ?? row.match_id),
          home_score: row.home_score ?? row.home_goals,
          away_score: row.away_score ?? row.away_goals,
        }))
        .filter((row) => Number.isFinite(row.id) && row.id > 0) as Match[]
    },
    retry: 1,
    staleTime: tab === 'live' ? 15_000 : 60_000,
    refetchInterval: tab === 'live' ? 20_000 : false,
  })
}

function useSyncFixtures() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`${ENDPOINTS.gateway}/api/matches/sync?days=60`, {
        method: 'POST',
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.detail || `Sync failed (HTTP ${res.status})`)
      }
      return res.json()
    },
    onSuccess: (data) => {
      const synced = data?.stored ?? data?.sportsdb_new ?? 0
      toast.success(`Synced ${synced} fixture${synced !== 1 ? 's' : ''} from SportsDB`)
      qc.invalidateQueries({ queryKey: ['matches'] })
    },
    onError: (err: Error) => {
      toast.error(`Fixture sync failed: ${err.message}`)
    },
  })
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function ProbBar({ label, prob, color }: { label: string; prob?: number; color: string }) {
  const pct = prob != null ? Math.round(prob * 100) : null
  return (
    <div className="flex-1 text-center">
      <div className="text-[10px] text-white/35 mb-1 uppercase tracking-widest">{label}</div>
      <div className={cn('text-sm font-bold', color)}>{pct != null ? `${pct}%` : '—'}</div>
      <div className="mt-1.5 h-1 rounded-full bg-white/8 overflow-hidden">
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

function MatchCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/6 bg-surface-800/50 p-5" aria-hidden="true">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-2.5 w-32" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="flex items-center gap-3 mb-5">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
        <Skeleton className="h-3 w-6" />
        <div className="flex-1 space-y-2 flex flex-col items-end">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <div className="border-t border-white/5 pt-4 flex gap-3">
        <Skeleton className="h-8 flex-1" />
        <Skeleton className="h-8 flex-1" />
        <Skeleton className="h-8 flex-1" />
      </div>
    </div>
  )
}

function MatchCard({ match, i }: { match: Match; i: number }) {
  const navigate = useNavigate()
  const conf   = match.confidence != null ? Math.round(match.confidence * 100) : null
  const isLive = match.status === 'live' || match.status === 'in_play'

  const autoSide = match.home_prob != null && match.draw_prob != null && match.away_prob != null
    ? (match.home_prob >= match.away_prob && match.home_prob >= match.draw_prob ? 'HOME' : match.away_prob >= match.draw_prob ? 'AWAY' : 'DRAW')
    : null
  const pickSide = (match.bet_side && match.home_prob != null && match.draw_prob != null && match.away_prob != null)
    ? match.bet_side.toUpperCase()
    : autoSide

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04, duration: 0.3 }}
      onClick={() => {
        const targetId = Number(match.id ?? match.match_id)
        if (Number.isFinite(targetId) && targetId > 0) {
          navigate(`/matches/${targetId}`)
        }
      }}
      className={cn(
        'group relative rounded-2xl border p-5 cursor-pointer transition-all duration-200',
        'bg-surface-800/50 hover:bg-surface-700/60',
        isLive
          ? 'border-emerald-500/30 shadow-md shadow-emerald-500/5'
          : 'border-white/6 hover:border-white/12',
      )}
    >
      {/* Top Header: League + Live / AI Pick Badge */}
      <div className="flex items-center justify-between mb-3.5 gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] font-medium text-white/35 uppercase tracking-wider truncate">{match.league}</span>
          <span className="text-white/15">·</span>
          <span className="text-[10px] text-white/30 shrink-0 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />
            {timeAgo(match.kickoff_time)}
          </span>
        </div>

        {isLive ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 text-[10px] font-bold uppercase tracking-wide">Live</span>
          </div>
        ) : pickSide ? (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-vit-500/15 border border-vit-500/30 shrink-0 text-[10px] font-bold text-vit-300">
            <Brain className="w-3 h-3 text-vit-400" />
            <span>AI PICK: {pickSide}</span>
          </div>
        ) : null}
      </div>

      {/* Teams */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white text-sm leading-tight truncate">{match.home_team}</p>
          {(match.home_score ?? match.home_goals) != null && (
            <p className="text-xl font-bold text-white mt-0.5">{match.home_score ?? match.home_goals}</p>
          )}
        </div>
        <div className="shrink-0 w-8 text-center">
          <span className={cn('text-xs font-semibold', isLive ? 'text-emerald-400' : 'text-white/25')}>vs</span>
        </div>
        <div className="flex-1 min-w-0 text-right">
          <p className="font-semibold text-white text-sm leading-tight truncate">{match.away_team}</p>
          {(match.away_score ?? match.away_goals) != null && (
            <p className="text-xl font-bold text-white mt-0.5">{match.away_score ?? match.away_goals}</p>
          )}
        </div>
      </div>

      {/* Probability bars */}
      {(match.home_prob != null || match.draw_prob != null || match.away_prob != null) && (
        <div className="flex gap-2 mb-4 pb-4 border-b border-white/5">
          <ProbBar label="H" prob={match.home_prob} color="text-vit-400" />
          {match.draw_prob != null && <ProbBar label="D" prob={match.draw_prob} color="text-white/40" />}
          <ProbBar label="A" prob={match.away_prob} color="text-amber-400" />
        </div>
      )}

      {/* Footer meta */}
      <div className="flex items-center justify-between text-xs text-white/30">
        <div className="flex items-center gap-3 flex-wrap">
          {conf != null && (
            <span className="flex items-center gap-1">
              <Target className="w-3 h-3 text-vit-400" />
              <span className="text-vit-400 font-medium">{conf}%</span>
            </span>
          )}
          {match.final_ev != null && (
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400 font-medium">
                EV {match.final_ev > 0 ? '+' : ''}{match.final_ev?.toFixed(2)}
              </span>
            </span>
          )}
          {match.entry_odds != null && (
            <span className="text-white/30">@ {match.entry_odds.toFixed(2)}</span>
          )}
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-white/15 group-hover:text-vit-400 group-hover:translate-x-0.5 transition-all" />
      </div>
    </motion.div>
  )
}

// ── Tab config ─────────────────────────────────────────────────────────────────

const TABS: { value: Tab; label: string; icon: ElementType }[] = [
  { value: 'upcoming', label: 'Upcoming', icon: Clock },
  { value: 'live',     label: 'Live',     icon: Radio },
  { value: 'recent',   label: 'Recent',   icon: CheckCircle },
  { value: 'all',      label: 'All',      icon: Activity },
]

const SPORTS: { value: Sport; label: string }[] = [
  { value: 'all',        label: 'All Sports' },
  { value: 'football',   label: '⚽ Football' },
  { value: 'basketball', label: '🏀 Basketball' },
  { value: 'tennis',     label: '🎾 Tennis' },
  { value: 'cricket',    label: '🏏 Cricket' },
]

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Matches() {
  const [tab, setTab]     = useState<Tab>('upcoming')
  const [sport, setSport] = useState<Sport>('all')
  const [search, setSearch] = useState('')

  const qc = useQueryClient()
  const { data = [], isLoading, isError, error, refetch } = useMatches(tab, sport)
  const syncMutation = useSyncFixtures()

  const filtered = search.trim()
    ? data.filter(m =>
        m.home_team.toLowerCase().includes(search.toLowerCase()) ||
        m.away_team.toLowerCase().includes(search.toLowerCase()) ||
        m.league.toLowerCase().includes(search.toLowerCase()),
      )
    : data

  return (
    <div className="pt-16 min-h-screen bg-surface-900">
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="border-b border-white/6 bg-surface-800/30 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-start justify-between gap-4">
            {/* Title */}
            <div className="flex items-start gap-3.5 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-vit-600/15 border border-vit-500/20 flex items-center justify-center shrink-0 mt-0.5">
                <Trophy className="w-5 h-5 text-vit-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white leading-tight">Matches &amp; Predictions</h1>
                <p className="text-white/40 text-sm mt-0.5">AI-powered sports intelligence and probability forecasts</p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => refetch()}
                disabled={isLoading}
                title="Refresh"
                className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 border border-white/8 text-white/50 hover:text-white flex items-center justify-center transition-all"
              >
                <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
              </button>
              <button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vit-600/15 border border-vit-500/25 text-vit-300 text-sm font-medium hover:bg-vit-600/25 transition-all disabled:opacity-50"
              >
                {syncMutation.isPending
                  ? <><Spinner className="w-3.5 h-3.5" />Syncing…</>
                  : <><RotateCcw className="w-3.5 h-3.5" />Sync Fixtures</>
                }
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">

        {/* ── Tabs (horizontal scroll on mobile) ────────────────────────── */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-hide" role="tablist" aria-label="Match status">
          {TABS.map(({ value, label, icon: Icon }) => {
            const isLive = value === 'live'
            return (
              <button
                key={value}
                onClick={() => setTab(value)}
                role="tab"
                aria-selected={tab === value}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all shrink-0',
                  tab === value
                    ? isLive
                      ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                      : 'bg-vit-600/20 border border-vit-500/30 text-vit-200'
                    : 'text-white/45 border border-transparent hover:text-white hover:bg-white/5',
                )}
              >
                {isLive && tab === value
                  ? <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  : <Icon className="w-3.5 h-3.5" />
                }
                {label}
                {isLive && (
                  <span className="text-[10px] text-emerald-400/60 font-normal hidden sm:inline">● Live</span>
                )}
              </button>
            )
          })}
        </div>

        {/* ── Sport filters + search ─────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Sport chips — horizontal scroll, never wrap */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide shrink-0" role="group" aria-label="Filter by sport">
            {SPORTS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setSport(value)}
                aria-pressed={sport === value}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all shrink-0',
                  sport === value
                    ? 'bg-white text-surface-900 shadow-sm'
                    : 'bg-white/5 border border-white/8 text-white/50 hover:text-white hover:bg-white/10',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Search — grows to fill remaining space */}
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/25 pointer-events-none" />
            <input
              type="text"
              placeholder="Search teams or leagues…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-surface-800/60 border border-white/8 rounded-xl pl-10 pr-4 py-2 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-vit-500/50 focus:ring-1 focus:ring-vit-500/15 transition-all"
            />
          </div>
        </div>

        {/* ── Results count ──────────────────────────────────────────────── */}
        {!isLoading && (
          <div className="flex items-center justify-between gap-3 px-1">
            <p className="text-xs text-white/35" aria-live="polite">
              <span className="font-medium text-white/60">{filtered.length}</span>{' '}
              {filtered.length === 1 ? 'match' : 'matches'}
              {search && <span className="text-white/25"> · searching "{search}"</span>}
            </p>
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-white/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Live data
            </span>
          </div>
        )}

        {/* ── Loading ────────────────────────────────────────────────────── */}
        {isLoading && (
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4" aria-label="Loading matches" aria-busy="true">
            {Array.from({ length: 6 }).map((_, i) => <MatchCardSkeleton key={i} />)}
          </div>
        )}

        {/* ── Error ─────────────────────────────────────────────────────── */}
        {isError && (
          <div className="rounded-2xl border border-red-500/15 bg-red-500/5 p-6 text-center">
            <p className="text-red-400 text-sm font-medium mb-1">Failed to load matches</p>
            <p className="text-white/30 text-xs mb-4">{(error as Error)?.message}</p>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm hover:bg-red-500/15 transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {/* ── Empty state ────────────────────────────────────────────────── */}
        {!isLoading && !isError && filtered.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-20 text-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-white/3 border border-white/6 flex items-center justify-center mb-5">
              <Trophy className="w-7 h-7 text-white/15" />
            </div>
            <h3 className="text-white font-semibold text-base mb-2">
              {search ? 'No matches found' : tab === 'live' ? 'No live matches' : 'No upcoming matches'}
            </h3>
            <p className="text-white/30 text-sm mb-6 max-w-xs">
              {tab === 'live'     ? 'No matches in play right now. Check back soon.' :
               tab === 'upcoming' ? 'No fixtures scheduled in the next 48 hours.' :
               tab === 'recent'   ? 'No results from the last 24 hours.' :
               search             ? `No matches matching "${search}".` : 'No matches found.'}
            </p>
            {(tab === 'upcoming' || tab === 'all') && !search && (
              <button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-vit-600/15 border border-vit-500/25 text-vit-300 text-sm font-medium hover:bg-vit-600/25 transition-all disabled:opacity-50"
              >
                {syncMutation.isPending
                  ? <><Spinner className="w-4 h-4" /> Syncing fixtures…</>
                  : <><RotateCcw className="w-4 h-4" /> Pull latest fixtures</>
                }
              </button>
            )}
          </motion.div>
        )}

        {/* ── Match grid ────────────────────────────────────────────────── */}
        {!isLoading && filtered.length > 0 && (
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map((m, i) => <MatchCard key={m.id ?? m.match_id} match={m} i={i} />)}
          </div>
        )}

        {/* ── AI Engine CTA (empty upcoming + no sync pending) ───────────── */}
        {!isLoading && filtered.length === 0 && tab === 'upcoming' && !syncMutation.isPending && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="rounded-2xl border border-vit-500/15 bg-gradient-to-br from-vit-600/5 to-transparent p-8 text-center"
          >
            <div className="w-12 h-12 rounded-xl bg-vit-600/15 border border-vit-500/20 flex items-center justify-center mx-auto mb-4">
              <Zap className="w-6 h-6 text-vit-400" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">AI Prediction Engine Ready</h3>
            <p className="text-white/40 text-sm mb-5 max-w-md mx-auto">
              Submit a match for real-time analysis across 13+ ML models with market-calibrated probabilities.
            </p>
            <a
              href="/developers"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors"
            >
              Open API Reference <ChevronRight className="w-4 h-4" />
            </a>
          </motion.div>
        )}
      </div>
    </div>
  )
}
