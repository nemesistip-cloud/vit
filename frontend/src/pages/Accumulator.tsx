import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Layers, Plus, Trash2, TrendingUp, AlertTriangle,
  CheckCircle2, XCircle, RefreshCw, Calculator, Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Fixture {
  id: number | string
  home_team: string
  away_team: string
  competition?: string
  kickoff?: string
  ai_pick?: string
  ai_confidence?: number
  ai_odds?: number
  status?: string
}

interface AccumLeg {
  fixtureId: number | string
  home_team: string
  away_team: string
  selection: string
  odds: number
  confidence: number
  conflict?: boolean
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useFixtures() {
  return useQuery<Fixture[]>({
    queryKey: ['fixtures-accum'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/matches?limit=30&status=upcoming`, {
        signal, headers: authHeaders(),
      })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.matches ?? d.items ?? []
    },
    retry: false,
    staleTime: 60_000,
  })
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function calcCombinedOdds(legs: AccumLeg[]): number {
  return legs.reduce((acc, l) => acc * l.odds, 1)
}

function calcEV(legs: AccumLeg[], stake: number): { ev: number; returnIfWin: number; impliedProb: number } {
  const combined = calcCombinedOdds(legs)
  const impliedProb = legs.reduce((p, l) => p * (l.confidence / 100), 1)
  const returnIfWin = stake * combined
  const ev = impliedProb * returnIfWin - stake
  return { ev, returnIfWin, impliedProb }
}

function detectConflicts(legs: AccumLeg[]): Set<number | string> {
  const conflicts = new Set<number | string>()
  // Same fixture appears twice
  const seen = new Map<number | string, number>()
  legs.forEach((l, i) => {
    if (seen.has(l.fixtureId)) {
      conflicts.add(l.fixtureId)
      const prevIdx = seen.get(l.fixtureId)!
      conflicts.add(legs[prevIdx].fixtureId)
    } else {
      seen.set(l.fixtureId, i)
    }
  })
  return conflicts
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function FixtureRow({ fixture, onAdd }: { fixture: Fixture; onAdd: (f: Fixture) => void }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-white/6 hover:bg-white/3 transition-colors">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-white truncate">
          {fixture.home_team} <span className="text-white/40">vs</span> {fixture.away_team}
        </p>
        <p className="text-xs text-white/40 mt-0.5">
          {fixture.competition ?? 'Match'}{fixture.kickoff ? ` · ${new Date(fixture.kickoff).toLocaleDateString()}` : ''}
        </p>
      </div>
      <div className="flex items-center gap-3 ml-3 flex-shrink-0">
        {fixture.ai_pick && (
          <span className="text-xs text-vit-400 bg-vit-400/10 px-2 py-0.5 rounded-full">
            {fixture.ai_pick} @ {fixture.ai_odds?.toFixed(2) ?? '—'}
          </span>
        )}
        <button
          onClick={() => onAdd(fixture)}
          className="p-1.5 rounded-lg bg-vit-500/15 hover:bg-vit-500/30 text-vit-400 transition-colors"
          title="Add to accumulator"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

function LegCard({ leg, idx, onRemove, conflict }: {
  leg: AccumLeg; idx: number; onRemove: (i: number) => void; conflict: boolean
}) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={cn(
        'flex items-start justify-between gap-3 p-3.5 rounded-xl border',
        conflict
          ? 'border-red-500/30 bg-red-500/5'
          : 'border-white/10 bg-white/5'
      )}
    >
      <div className="flex items-start gap-2.5 min-w-0 flex-1">
        <span className="w-5 h-5 rounded-full bg-vit-500/20 text-vit-400 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
          {idx + 1}
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium text-white truncate">
            {leg.home_team} vs {leg.away_team}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-xs text-vit-300 bg-vit-500/10 px-2 py-0.5 rounded-full">{leg.selection}</span>
            <span className="text-xs text-white/50">odds {leg.odds.toFixed(2)}</span>
            <span className="text-xs text-emerald-400">{leg.confidence}% conf.</span>
            {conflict && (
              <span className="text-xs text-red-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Conflict
              </span>
            )}
          </div>
        </div>
      </div>
      <button
        onClick={() => onRemove(idx)}
        className="p-1.5 rounded-lg hover:bg-red-500/15 text-white/30 hover:text-red-400 transition-colors flex-shrink-0"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Accumulator() {
  const { data: fixtures = [], isLoading, refetch } = useFixtures()
  const [legs, setLegs] = useState<AccumLeg[]>([])
  const [stake, setStake] = useState(10)
  const [search, setSearch] = useState('')

  const conflictIds = detectConflicts(legs)

  function addLeg(fixture: Fixture) {
    if (legs.some(l => l.fixtureId === fixture.id)) {
      toast.error('Fixture already added — would create a conflict')
      return
    }
    if (legs.length >= 10) {
      toast.error('Maximum 10 legs per accumulator')
      return
    }
    const leg: AccumLeg = {
      fixtureId: fixture.id,
      home_team: fixture.home_team,
      away_team: fixture.away_team,
      selection: fixture.ai_pick ?? 'Home Win',
      odds: fixture.ai_odds ?? 1.8,
      confidence: fixture.ai_confidence ?? 60,
    }
    setLegs(prev => [...prev, leg])
    toast.success(`Added: ${fixture.home_team} vs ${fixture.away_team}`)
  }

  function removeLeg(idx: number) {
    setLegs(prev => prev.filter((_, i) => i !== idx))
  }

  const hasConflicts = conflictIds.size > 0
  const { ev, returnIfWin, impliedProb } = legs.length ? calcEV(legs, stake) : { ev: 0, returnIfWin: 0, impliedProb: 0 }
  const combinedOdds = legs.length ? calcCombinedOdds(legs) : 0

  const filtered = fixtures.filter(f => {
    const q = search.toLowerCase()
    return !q || f.home_team.toLowerCase().includes(q) || f.away_team.toLowerCase().includes(q)
  })

  function placeBet() {
    if (legs.length < 2) { toast.error('Add at least 2 legs'); return }
    if (hasConflicts) { toast.error('Remove conflicting legs first'); return }
    toast.success(`Accumulator placed — ${legs.length} legs @ ${combinedOdds.toFixed(2)}`, {
      description: `Potential return: $${returnIfWin.toFixed(2)}`,
    })
  }

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Layers className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Accumulator Builder</h1>
              <p className="text-white/50 text-sm">Build multi-leg accumulators with AI-powered EV analysis</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-2 gap-8">

          {/* Left — fixture picker */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Available Fixtures</h2>
              <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/8 text-white/40 hover:text-white transition-colors">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search teams…"
              className="w-full mb-3 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-500/50"
            />
            <div className="bg-white/3 border border-white/8 rounded-2xl overflow-hidden max-h-[420px] overflow-y-auto">
              {isLoading ? (
                <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>
              ) : filtered.length === 0 ? (
                <p className="text-center text-white/30 py-10 text-sm">No fixtures found</p>
              ) : (
                filtered.map(f => <FixtureRow key={f.id} fixture={f} onAdd={addLeg} />)
              )}
            </div>
          </div>

          {/* Right — builder */}
          <div className="flex flex-col gap-5">
            {/* Legs */}
            <div>
              <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">
                Your Legs <span className="text-white/30 font-normal normal-case">({legs.length}/10)</span>
              </h2>
              {legs.length === 0 ? (
                <div className="border border-dashed border-white/15 rounded-2xl py-12 text-center">
                  <Layers className="w-8 h-8 text-white/20 mx-auto mb-3" />
                  <p className="text-white/30 text-sm">Add fixtures from the left panel</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <AnimatePresence>
                    {legs.map((leg, i) => (
                      <LegCard
                        key={`${leg.fixtureId}-${i}`}
                        leg={leg}
                        idx={i}
                        onRemove={removeLeg}
                        conflict={conflictIds.has(leg.fixtureId)}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>

            {/* EV Summary */}
            {legs.length > 0 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-4">
                <div className="flex items-center gap-2 mb-1">
                  <Calculator className="w-4 h-4 text-vit-400" />
                  <h3 className="text-sm font-semibold text-white">EV Analysis</h3>
                  {hasConflicts && (
                    <span className="ml-auto flex items-center gap-1 text-xs text-red-400">
                      <XCircle className="w-3.5 h-3.5" /> Conflicts detected
                    </span>
                  )}
                  {!hasConflicts && legs.length >= 2 && (
                    <span className="ml-auto flex items-center gap-1 text-xs text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" /> No conflicts
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'Combined Odds', value: combinedOdds.toFixed(2), color: 'text-vit-400' },
                    { label: 'Implied Prob.', value: `${(impliedProb * 100).toFixed(1)}%`, color: 'text-sky-400' },
                    { label: 'Potential Return', value: `$${returnIfWin.toFixed(2)}`, color: 'text-emerald-400' },
                    { label: 'Expected Value', value: `${ev >= 0 ? '+' : ''}$${ev.toFixed(2)}`, color: ev >= 0 ? 'text-emerald-400' : 'text-red-400' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-white/5 rounded-xl p-3">
                      <p className="text-xs text-white/40 mb-1">{label}</p>
                      <p className={cn('text-lg font-bold', color)}>{value}</p>
                    </div>
                  ))}
                </div>

                {ev < 0 && (
                  <div className="flex items-start gap-2 text-xs text-amber-300/80 bg-amber-500/8 border border-amber-500/20 rounded-xl px-3 py-2.5">
                    <Info className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                    Negative EV — the combined odds don't justify the probability. Consider removing low-confidence legs.
                  </div>
                )}

                {/* Stake */}
                <div>
                  <label className="text-xs text-white/50 block mb-1.5">Stake ($)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min={1}
                      value={stake}
                      onChange={e => setStake(Math.max(1, Number(e.target.value)))}
                      className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-vit-500/50"
                    />
                    {[5, 10, 25, 50].map(v => (
                      <button key={v} onClick={() => setStake(v)}
                        className={cn('px-3 py-2 rounded-xl text-xs font-medium border transition-colors',
                          stake === v ? 'bg-vit-500/20 border-vit-500/40 text-vit-300' : 'bg-white/5 border-white/10 text-white/50 hover:text-white'
                        )}>
                        ${v}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={placeBet}
                  disabled={legs.length < 2 || hasConflicts}
                  className={cn(
                    'w-full py-3 rounded-xl text-sm font-semibold transition-all',
                    legs.length >= 2 && !hasConflicts
                      ? 'bg-vit-500 hover:bg-vit-400 text-white shadow-lg shadow-vit-500/20'
                      : 'bg-white/5 text-white/30 cursor-not-allowed'
                  )}
                >
                  <TrendingUp className="w-4 h-4 inline mr-2" />
                  Place Accumulator ({legs.length} {legs.length === 1 ? 'leg' : 'legs'})
                </button>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
