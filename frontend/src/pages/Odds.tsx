import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3, RefreshCw, Search, TrendingUp, TrendingDown,
  Minus, AlertCircle, Clock, Filter,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface BookmakerOdds {
  bookmaker: string
  home: number
  draw: number | null
  away: number
  updated_at?: string
}

interface OddsEntry {
  match_id: number | string
  home_team: string
  away_team: string
  league: string
  kickoff_time: string
  ai_pick?: 'home' | 'draw' | 'away'
  ai_confidence?: number
  best_ev?: number
  bookmakers: BookmakerOdds[]
}

// ── Hook ───────────────────────────────────────────────────────────────────────

function useOdds(sport: string, search: string) {
  return useQuery<OddsEntry[]>({
    queryKey: ['odds', sport],
    queryFn: async ({ signal }) => {
      const queryParams = new URLSearchParams()
      if (sport && sport !== 'all') {
        queryParams.set('sport', sport)
        queryParams.set('league', sport)
      }
      const qs = queryParams.toString() ? `?${queryParams.toString()}` : ''
      try {
        const r = await fetch(`${ENDPOINTS.gateway}/api/odds/compare${qs}`, { signal, headers: authHeaders() })
        if (!r.ok) return []
        const d = await r.json()
        const rawList = Array.isArray(d) ? d : d.odds ?? d.events ?? d.matches ?? d.items ?? []
        return rawList.map((item: any) => ({
          match_id: item.match_id ?? item.id ?? `${item.home_team}::${item.away_team}`,
          home_team: item.home_team ?? '',
          away_team: item.away_team ?? '',
          league: item.league ?? item.sport_key ?? 'Sports',
          kickoff_time: item.kickoff_time ?? item.kickoff ?? item.commence_time ?? new Date().toISOString(),
          ai_pick: item.ai_pick,
          ai_confidence: item.ai_confidence,
          best_ev: item.best_ev,
          bookmakers: Array.isArray(item.bookmakers)
            ? item.bookmakers
            : Object.entries(item.bookmakers ?? {}).map(([bk, val]: [string, any]) => ({
                bookmaker: bk,
                home: val.home ?? 1.0,
                draw: val.draw ?? null,
                away: val.away ?? 1.0,
              })),
        }))
      } catch (e) {
        return []
      }
    },
    staleTime: 120_000,
    refetchInterval: 120_000,
  })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function bestOdds(entries: BookmakerOdds[], key: 'home' | 'draw' | 'away') {
  const vals = entries.map(b => b[key]).filter((v): v is number => v != null && v > 0)
  return vals.length ? Math.max(...vals) : null
}

function OddsCell({
  value,
  best,
  pick,
}: {
  value: number | null
  best: number | null
  pick?: boolean
}) {
  if (value == null) return <td className="px-3 py-3 text-center text-white/20 text-sm">—</td>
  const isBest = best != null && value === best
  return (
    <td className="px-3 py-3 text-center">
      <span className={cn(
        'inline-block px-2.5 py-1 rounded-lg text-sm font-mono font-semibold transition-colors',
        pick   ? 'bg-vit-500/20 text-vit-300 ring-1 ring-vit-500/40' :
        isBest ? 'bg-emerald-500/15 text-emerald-300'                :
                 'text-white/60',
      )}>
        {value.toFixed(2)}
      </span>
    </td>
  )
}

// ── Odds row ──────────────────────────────────────────────────────────────────

function OddsRow({ entry, i }: { entry: OddsEntry; i: number }) {
  const [expanded, setExpanded] = useState(false)
  const bestH = bestOdds(entry.bookmakers, 'home')
  const bestD = bestOdds(entry.bookmakers, 'draw')
  const bestA = bestOdds(entry.bookmakers, 'away')

  return (
    <>
      <motion.tr
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: i * 0.03 }}
        onClick={() => setExpanded(e => !e)}
        className="border-b border-white/5 hover:bg-white/3 cursor-pointer transition-colors"
      >
        {/* Match */}
        <td className="px-4 py-3.5">
          <p className="text-sm font-medium text-white">{entry.home_team} <span className="text-white/30 mx-1">vs</span> {entry.away_team}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[11px] text-white/35">{entry.league}</span>
            <span className="text-white/20">·</span>
            <span className="flex items-center gap-1 text-[11px] text-white/35">
              <Clock className="w-2.5 h-2.5" />
              {timeAgo(entry.kickoff_time)}
            </span>
          </div>
        </td>

        {/* Best home */}
        <td className="px-3 py-3 text-center">
          <span className={cn('text-sm font-mono font-semibold', entry.ai_pick === 'home' ? 'text-vit-300' : 'text-white/70')}>
            {bestH?.toFixed(2) ?? '—'}
          </span>
        </td>

        {/* Best draw */}
        <td className="px-3 py-3 text-center">
          <span className="text-sm font-mono text-white/50">{bestD?.toFixed(2) ?? '—'}</span>
        </td>

        {/* Best away */}
        <td className="px-3 py-3 text-center">
          <span className={cn('text-sm font-mono font-semibold', entry.ai_pick === 'away' ? 'text-vit-300' : 'text-white/70')}>
            {bestA?.toFixed(2) ?? '—'}
          </span>
        </td>

        {/* AI pick */}
        <td className="px-3 py-3 text-center">
          {entry.ai_pick ? (
            <div className="inline-flex flex-col items-center">
              <span className="px-2 py-0.5 rounded-full bg-vit-500/15 text-vit-400 text-[10px] font-medium uppercase">
                {entry.ai_pick}
              </span>
              {entry.ai_confidence != null && (
                <span className="text-[10px] text-white/30 mt-0.5">{Math.round(entry.ai_confidence * 100)}%</span>
              )}
            </div>
          ) : <span className="text-white/20">—</span>}
        </td>

        {/* EV */}
        <td className="px-3 py-3 text-center">
          {entry.best_ev != null ? (
            <span className={cn('flex items-center justify-center gap-1 text-sm font-semibold',
              entry.best_ev > 0 ? 'text-emerald-400' : entry.best_ev < 0 ? 'text-red-400' : 'text-white/40',
            )}>
              {entry.best_ev > 0 ? <TrendingUp className="w-3 h-3" /> : entry.best_ev < 0 ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              {entry.best_ev > 0 ? '+' : ''}{entry.best_ev.toFixed(2)}
            </span>
          ) : <span className="text-white/20">—</span>}
        </td>
      </motion.tr>

      {/* Expanded bookmaker breakdown */}
      {expanded && (
        <tr className="bg-white/2">
          <td colSpan={6} className="px-4 py-3">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] text-white/30 uppercase">
                    <th className="text-left pb-2 pr-4">Bookmaker</th>
                    <th className="text-center pb-2 px-3">Home</th>
                    <th className="text-center pb-2 px-3">Draw</th>
                    <th className="text-center pb-2 px-3">Away</th>
                  </tr>
                </thead>
                <tbody>
                  {entry.bookmakers.map(bk => (
                    <tr key={bk.bookmaker} className="border-t border-white/5">
                      <td className="pr-4 py-2 text-white/60 text-xs">{bk.bookmaker}</td>
                      <OddsCell value={bk.home} best={bestH} pick={entry.ai_pick === 'home' && bk.home === bestH} />
                      <OddsCell value={bk.draw} best={bestD} pick={entry.ai_pick === 'draw' && bk.draw === bestD} />
                      <OddsCell value={bk.away} best={bestA} pick={entry.ai_pick === 'away' && bk.away === bestA} />
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[10px] text-white/25 mt-2">
              Highlighted = best available odds · AI pick marked with VIT colour · Updated every 2 minutes
            </p>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

const SPORTS = ['all', 'football', 'basketball', 'tennis', 'cricket']

export default function Odds() {
  const [sport, setSport]   = useState('all')
  const [search, setSearch] = useState('')
  const { data = [], isLoading, refetch, isFetching, dataUpdatedAt } = useOdds(sport, search)

  const filtered = search
    ? data.filter(e =>
        e.home_team.toLowerCase().includes(search.toLowerCase()) ||
        e.away_team.toLowerCase().includes(search.toLowerCase()) ||
        e.league.toLowerCase().includes(search.toLowerCase()),
      )
    : data

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2.5 mb-1">
                <BarChart3 className="w-5 h-5 text-vit-400" />
                <h1 className="text-2xl font-bold text-white">Odds Comparison</h1>
              </div>
              <p className="text-white/45 text-sm">Best available odds across bookmakers, with AI picks and EV scores.</p>
            </div>
            <div className="flex items-center gap-2">
              {dataUpdatedAt > 0 && (
                <span className="text-[11px] text-white/30">Updated {timeAgo(new Date(dataUpdatedAt).toISOString())}</span>
              )}
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white hover:bg-white/8 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={cn('w-4 h-4', isFetching && 'animate-spin')} />
              </button>
            </div>
          </div>
        </motion.div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 mb-5">
          {/* Sport filter */}
          <div className="flex gap-1.5 flex-wrap">
            {SPORTS.map(s => (
              <button
                key={s}
                onClick={() => setSport(s)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors',
                  sport === s ? 'bg-vit-600 text-white' : 'bg-white/5 text-white/50 hover:text-white hover:bg-white/8',
                )}
              >
                {s === 'all' ? 'All Sports' : s}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/30 pointer-events-none" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search team or league…"
              className="pl-8 pr-4 py-2 bg-surface-800/60 border border-white/10 rounded-lg text-white text-sm placeholder-white/25 focus:outline-none focus:border-vit-500/50 w-52 transition-colors"
            />
          </div>
        </div>

        {/* Table */}
        <div className="bg-surface-800/40 border border-white/8 rounded-2xl overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center py-20"><Spinner className="w-8 h-8" /></div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20 text-white/40">
              <AlertCircle className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">{search ? 'No matches found for your search.' : 'No odds data available right now.'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[11px] text-white/30 uppercase tracking-wide border-b border-white/8">
                    <th className="text-left px-4 py-3">Match</th>
                    <th className="text-center px-3 py-3">Best Home</th>
                    <th className="text-center px-3 py-3">Best Draw</th>
                    <th className="text-center px-3 py-3">Best Away</th>
                    <th className="text-center px-3 py-3">AI Pick</th>
                    <th className="text-center px-3 py-3">EV</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((e, i) => <OddsRow key={e.match_id} entry={e} i={i} />)}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <p className="text-[11px] text-white/25 text-center mt-4">
          Click any row to see all bookmaker odds · Odds auto-refresh every 2 minutes · AI EV = Expected Value based on VIT model confidence
        </p>
      </div>
    </div>
  )
}
