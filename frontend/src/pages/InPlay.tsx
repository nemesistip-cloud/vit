import { useState, type MouseEvent, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Zap, Clock, Target, Activity,
  X, AlertTriangle, Radio, ShieldCheck, Database, Calendar
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'

// ── Types ──────────────────────────────────────────────────────────────────────

interface LiveMatch {
  id: string
  provider: string
  provider_match_id: string
  home: string
  away: string
  league: string
  sport: string
  status: 'LIVE' | 'UPCOMING' | 'FINISHED' | 'DATA_UNAVAILABLE'
  minute: number
  home_score: number
  away_score: number
  period: string
  kickoff_time?: string
  source_timestamp: number
  ingestion_timestamp: number
  last_successful_update: number
  markets_available: boolean
}

interface Selection {
  id: string
  label: string
  odds: number
  source: string
}

interface Market {
  id: string
  match_id: string
  type: string
  status: 'open' | 'suspended' | 'closed' | 'unavailable'
  home: string
  away: string
  selections: Selection[]
  updated_at: number
  odds_source: string
  odds_timestamp: number
}

interface Bet {
  id: string
  market_id: string
  selection: string
  odds: number
  stake: number
  potential_win: number
  placed_at: number
  status: string
  provider?: string
}

interface InPlayStats {
  live_matches: number
  open_markets: number
  total_bets: number
  total_staked: number
  last_sync: number
}

interface MatchesApiResponse {
  matches: LiveMatch[]
  upcoming: LiveMatch[]
  total_live: number
  total_upcoming: number
  is_live_available: boolean
  timestamp: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

const BASE = () => `${ENDPOINTS.gateway}/api/inplay`

function useLiveMatches() {
  return useQuery<MatchesApiResponse>({
    queryKey: ['inplay-matches'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/matches`, { signal })
      return r.ok ? r.json() : { matches: [], upcoming: [], total_live: 0, total_upcoming: 0, is_live_available: false, timestamp: Date.now() / 1000 }
    },
    refetchInterval: 10_000,
    retry: false,
  })
}

function useMatchMarkets(matchId: string | null) {
  return useQuery<{ match_id: string; provider: string; markets: Market[] }>({
    queryKey: ['inplay-markets', matchId],
    queryFn: async ({ signal }) => {
      if (!matchId) return { match_id: '', provider: '', markets: [] }
      const r = await fetch(`${BASE()}/matches/${matchId}/markets`, { signal })
      return r.ok ? r.json() : { match_id: matchId, provider: '', markets: [] }
    },
    enabled: !!matchId,
    refetchInterval: 8_000,
  })
}

function useMyBets() {
  return useQuery({
    queryKey: ['inplay-bets'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/my-bets`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { bets: [] }
    },
    refetchInterval: 15_000,
  })
}

function useInPlayStats() {
  return useQuery({
    queryKey: ['inplay-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/stats`, { signal })
      return r.ok ? (r.json() as Promise<InPlayStats>) : null
    },
    refetchInterval: 20_000,
  })
}

// ── Market type label ─────────────────────────────────────────────────────────

const MARKET_LABELS: Record<string, string> = {
  match_result: 'Match Result (1X2)',
  next_goal:    'Next Goal',
  total_goals:  'Total Goals (Over/Under)',
  btts:         'Both Teams To Score',
}

// ── Bet slip ──────────────────────────────────────────────────────────────────

interface BetSlipProps {
  market: Market
  selection: Selection
  onClose: () => void
}

function BetSlip({ market, selection, onClose }: BetSlipProps) {
  const qc = useQueryClient()
  const [stake, setStake] = useState('')
  const [err, setErr]     = useState('')

  const placeBet = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/bet`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          market_id:    market.id,
          selection_id: selection.id,
          stake:        parseFloat(stake),
        }),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed to place bet') }
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inplay-bets'] })
      qc.invalidateQueries({ queryKey: ['inplay-stats'] })
      onClose()
    },
    onError: (e: Error) => setErr(e.message),
  })

  const potentialWin = parseFloat(stake) ? (parseFloat(stake) * selection.odds).toFixed(2) : null

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e: MouseEvent) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }}
        className="w-full max-w-sm bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-4 border-b border-white/8">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <span className="font-semibold text-sm text-white">Place In-Play Bet</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="bg-white/5 rounded-xl p-3">
            <p className="text-xs text-white/40 mb-1">{MARKET_LABELS[market.type] ?? market.type}</p>
            <p className="font-semibold text-white">{selection.label}</p>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-white/40">{market.home} vs {market.away}</span>
              <span className="text-lg font-bold text-amber-400">@{selection.odds}</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Stake (VIT)</label>
            <input
              type="number"
              min="0.5"
              step="0.5"
              value={stake}
              onChange={e => setStake(e.target.value)}
              placeholder="Min 0.5 VIT"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50"
            />
            <div className="flex gap-1.5 mt-1.5">
              {[1, 5, 10, 25].map(v => (
                <button
                  key={v}
                  onClick={() => setStake(String(v))}
                  className="px-2 py-1 bg-white/5 hover:bg-white/10 text-white/50 hover:text-white rounded text-xs transition-colors"
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {potentialWin && (
            <div className="bg-vit-500/10 border border-vit-500/20 rounded-xl p-3 flex justify-between">
              <span className="text-sm text-white/60">Potential win</span>
              <span className="font-bold text-vit-300">{potentialWin} VIT</span>
            </div>
          )}

          {err && (
            <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              {err}
            </div>
          )}

          <button
            onClick={() => placeBet.mutate()}
            disabled={!stake || parseFloat(stake) < 0.5 || placeBet.isPending}
            className="w-full py-2.5 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-xl text-sm transition-colors disabled:opacity-40"
          >
            {placeBet.isPending ? <Spinner className="w-4 h-4 mx-auto" /> : 'Confirm Bet'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Match card ────────────────────────────────────────────────────────────────

function MatchCard({ match, selected, onSelect }: { match: LiveMatch; selected: boolean; onSelect: () => void }) {
  const isLive = match.status === 'LIVE'

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left p-4 rounded-xl border transition-all',
        selected
          ? 'bg-vit-500/10 border-vit-500/30'
          : 'bg-white/3 border-white/8 hover:border-white/20',
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-white/40">{match.league}</span>
        <div className="flex items-center gap-1.5">
          {isLive ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
              </span>
              <span className="text-xs font-medium text-red-400">{match.minute}'</span>
            </>
          ) : (
            <span className="text-xs font-medium text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 rounded">
              UPCOMING
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-sm text-white truncate max-w-[40%]">{match.home}</span>
        {isLive ? (
          <div className="flex items-center gap-2 px-3 py-1 bg-white/5 rounded-lg">
            <span className="text-lg font-bold text-white">{match.home_score}</span>
            <span className="text-white/40 text-sm">-</span>
            <span className="text-lg font-bold text-white">{match.away_score}</span>
          </div>
        ) : (
          <span className="text-xs text-white/40 px-2 py-1 bg-white/5 rounded">VS</span>
        )}
        <span className="font-semibold text-sm text-white truncate max-w-[40%] text-right">{match.away}</span>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5 text-[10px] text-white/30">
        <span className="flex items-center gap-1">
          <Database className="w-3 h-3" /> Source: {match.provider}
        </span>
        {match.kickoff_time && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" /> {new Date(match.kickoff_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </button>
  )
}

// ── Market panel ──────────────────────────────────────────────────────────────

function MarketPanel({ matchId }: { matchId: string }) {
  const { data, isLoading } = useMatchMarkets(matchId)
  const [betSlip, setBetSlip] = useState<{ market: Market; selection: Selection } | null>(null)

  const markets: Market[] = data?.markets ?? []

  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="w-5 h-5 text-vit-400" /></div>

  return (
    <div className="space-y-3">
      {markets.map(mk => (
        <div key={mk.id} className="bg-white/3 border border-white/8 rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-white/5 flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-white">{MARKET_LABELS[mk.type] ?? mk.type}</span>
              <span className="text-[10px] text-white/30 ml-2">Source: {mk.odds_source}</span>
            </div>
            <span className={cn(
              'px-2 py-0.5 rounded-full text-xs font-semibold',
              mk.status === 'open' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
              mk.status === 'unavailable' ? 'bg-white/5 text-white/30 border border-white/10' :
              'bg-amber-500/15 text-amber-400 border border-amber-500/30',
            )}>
              {mk.status.toUpperCase()}
            </span>
          </div>
          <div className="p-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {mk.selections.map(sel => (
              <button
                key={sel.id}
                onClick={() => mk.status === 'open' && sel.odds > 1.0 && setBetSlip({ market: mk, selection: sel })}
                disabled={mk.status !== 'open' || sel.odds <= 1.0}
                className={cn(
                  'flex flex-col items-center p-3 rounded-lg border text-sm font-medium transition-all',
                  mk.status === 'open' && sel.odds > 1.0
                    ? 'bg-white/5 border-white/10 hover:bg-amber-500/10 hover:border-amber-500/30 hover:text-amber-300 text-white cursor-pointer'
                    : 'bg-white/2 border-white/5 text-white/20 cursor-not-allowed',
                )}
              >
                <span className="text-xs text-white/50 mb-1 text-center leading-tight">{sel.label}</span>
                <span className="text-base font-bold text-amber-400">
                  {sel.odds > 1.0 ? sel.odds : 'N/A'}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}

      <AnimatePresence>
        {betSlip && (
          <BetSlip
            market={betSlip.market}
            selection={betSlip.selection}
            onClose={() => setBetSlip(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function InPlay() {
  const navigate = useNavigate()
  const [selectedMatch, setSelectedMatch] = useState<string | null>(null)
  const [tab, setTab] = useState<'markets' | 'my-bets'>('markets')

  useEffect(() => {
    if (!getAuthToken()) navigate('/login')
  }, [navigate])

  const { data: matchesData, isLoading: matchesLoading } = useLiveMatches()
  const { data: betsData }   = useMyBets()
  const { data: stats }      = useInPlayStats()

  const liveMatches: LiveMatch[] = matchesData?.matches ?? []
  const upcomingMatches: LiveMatch[] = matchesData?.upcoming ?? []
  const bets: Bet[] = betsData?.bets ?? []

  const displayMatches = liveMatches.length > 0 ? liveMatches : upcomingMatches

  // Auto-select first match
  useEffect(() => {
    if (!selectedMatch && displayMatches.length > 0) setSelectedMatch(displayMatches[0].id)
  }, [displayMatches, selectedMatch])

  return (
    <div className="min-h-screen bg-surface-950 pt-24 pb-16">
      <div className="max-w-5xl mx-auto px-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-500/15 border border-red-500/25 rounded-xl">
                <Radio className="w-5 h-5 text-red-400 animate-pulse" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Live In-Play Markets</h1>
                <p className="text-white/50 text-sm flex items-center gap-2">
                  <span>Verified real-time prediction feeds</span>
                  <span className="flex items-center gap-1 text-emerald-400 text-xs bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    <ShieldCheck className="w-3 h-3" /> ZERO SIMULATED DATA
                  </span>
                </p>
              </div>
            </div>
          </div>

          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Live Matches',   value: stats.live_matches,          color: 'text-red-400' },
                { label: 'Open Markets',   value: stats.open_markets,          color: 'text-emerald-400' },
                { label: 'Total Bets',     value: stats.total_bets,            color: 'text-white' },
                { label: 'Total Staked',   value: `${stats.total_staked} VIT`, color: 'text-vit-400' },
              ].map(s => (
                <div key={s.label} className="bg-white/3 border border-white/8 rounded-xl p-3 text-center">
                  <p className={cn('text-lg font-bold', s.color)}>{s.value}</p>
                  <p className="text-xs text-white/40">{s.label}</p>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Match list */}
          <div className="lg:col-span-1">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">
                {liveMatches.length > 0 ? 'Live In-Play Matches' : 'Upcoming Fixtures'}
              </h2>
              {liveMatches.length > 0 && (
                <span className="text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded font-bold">
                  {liveMatches.length} LIVE
                </span>
              )}
            </div>

            {matchesLoading && <div className="flex justify-center py-6"><Spinner className="w-5 h-5 text-vit-400" /></div>}

            {!matchesLoading && liveMatches.length === 0 && upcomingMatches.length === 0 && (
              <div className="text-center py-10 bg-white/2 border border-white/5 rounded-xl p-4">
                <Activity className="w-8 h-8 text-white/20 mx-auto mb-2" />
                <p className="text-white/80 font-semibold text-sm">No live matches currently in play</p>
                <p className="text-white/40 text-xs mt-1">No ongoing real-world matches were found across connected provider feeds.</p>
              </div>
            )}

            {!matchesLoading && liveMatches.length === 0 && upcomingMatches.length > 0 && (
              <div className="mb-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-xs text-amber-300 flex items-center gap-2">
                <Calendar className="w-4 h-4 shrink-0 text-amber-400" />
                <span>No matches are currently in-play. Showing upcoming verified real fixtures.</span>
              </div>
            )}

            <div className="space-y-2">
              {displayMatches.map(m => (
                <MatchCard
                  key={m.id}
                  match={m}
                  selected={selectedMatch === m.id}
                  onSelect={() => { setSelectedMatch(m.id); setTab('markets') }}
                />
              ))}
            </div>
          </div>

          {/* Markets / bets */}
          <div className="lg:col-span-2">
            <div className="flex gap-1 mb-4 bg-white/3 border border-white/8 rounded-xl p-1 max-w-xs">
              {[
                { id: 'markets',  label: 'Markets'  },
                { id: 'my-bets', label: `My Bets (${bets.length})` },
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id as 'markets' | 'my-bets')}
                  className={cn(
                    'flex-1 py-1.5 rounded-lg text-sm font-medium transition-all',
                    tab === t.id ? 'bg-vit-500/20 text-vit-300 border border-vit-500/30' : 'text-white/50 hover:text-white/80',
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {tab === 'markets' && selectedMatch && <MarketPanel matchId={selectedMatch} />}
            {tab === 'markets' && !selectedMatch && (
              <div className="text-center py-12 text-white/30 text-sm">Select a match to see markets</div>
            )}

            {tab === 'my-bets' && (
              <div className="space-y-3">
                {bets.length === 0 && (
                  <div className="text-center py-12">
                    <Target className="w-8 h-8 text-white/20 mx-auto mb-2" />
                    <p className="text-white/40 text-sm">No in-play bets placed yet</p>
                  </div>
                )}
                {bets.map(b => (
                  <div key={b.id} className="flex items-center justify-between p-3 bg-white/3 border border-white/8 rounded-xl">
                    <div>
                      <p className="text-sm font-medium text-white">{b.selection}</p>
                      <p className="text-xs text-white/40">Stake: {b.stake} VIT · @{b.odds} · Provider: {b.provider || 'system'}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-vit-300">{(b.potential_win ?? 0).toFixed(2)} VIT</p>
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded',
                        b.status === 'pending'  ? 'bg-amber-500/15 text-amber-400' :
                        b.status === 'settled'  ? 'bg-emerald-500/15 text-emerald-400' :
                        'bg-white/10 text-white/40',
                      )}>
                        {b.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
