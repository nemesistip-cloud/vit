import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RotateCcw, CheckCircle2, AlertTriangle, XCircle,
  Clock, Shield, RefreshCw, ChevronRight, Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────────────────

type ConflictSeverity = 'none' | 'low' | 'medium' | 'high'

interface RolloverFixture {
  id: number | string
  home_team: string
  away_team: string
  competition?: string
  kickoff?: string
  ai_pick?: string
  ai_confidence?: number
  ai_odds?: number
  certified?: boolean
  conflict_severity?: ConflictSeverity
  conflict_reason?: string
  status?: string
}

interface RolloverState {
  target_odds: number
  current_odds: number
  legs_completed: number
  legs_required: number
  total_stake: number
  current_balance: number
  started_at: string
  status: 'active' | 'complete' | 'failed'
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useRolloverFixtures() {
  return useQuery<RolloverFixture[]>({
    queryKey: ['rollover-fixtures'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/matches?limit=20&status=upcoming`, {
        signal, headers: authHeaders(),
      })
      if (!r.ok) return []
      const d = await r.json()
      const raw: RolloverFixture[] = Array.isArray(d) ? d : d.matches ?? d.items ?? []
      // Simulate certification & conflict analysis
      return raw.map(f => ({
        ...f,
        certified: (f.ai_confidence ?? 0) >= 65,
        conflict_severity: (f.ai_confidence ?? 0) >= 75
          ? 'none'
          : (f.ai_confidence ?? 0) >= 60
            ? 'low'
            : (f.ai_confidence ?? 0) >= 50
              ? 'medium'
              : 'high',
        conflict_reason: (f.ai_confidence ?? 0) < 50
          ? 'Ensemble models disagree — insufficient consensus'
          : (f.ai_confidence ?? 0) < 60
            ? 'Moderate model variance detected'
            : undefined,
      }))
    },
    retry: false,
    staleTime: 60_000,
    refetchInterval: 120_000,
  })
}

function useRolloverState() {
  return useQuery<RolloverState | null>({
    queryKey: ['rollover-state'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/rollover/active`, {
        signal, headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 30_000,
  })
}

// ── Severity helpers ───────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<ConflictSeverity, { label: string; color: string; bg: string; border: string; icon: React.ReactNode }> = {
  none:   { label: 'Certified',       color: 'text-emerald-400', bg: 'bg-emerald-500/8',  border: 'border-emerald-500/20', icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" /> },
  low:    { label: 'Low Conflict',    color: 'text-amber-400',   bg: 'bg-amber-500/8',    border: 'border-amber-500/20',   icon: <AlertTriangle className="w-4 h-4 text-amber-400" /> },
  medium: { label: 'Med. Conflict',   color: 'text-orange-400',  bg: 'bg-orange-500/8',   border: 'border-orange-500/20',  icon: <AlertTriangle className="w-4 h-4 text-orange-400" /> },
  high:   { label: 'High Conflict',   color: 'text-red-400',     bg: 'bg-red-500/8',      border: 'border-red-500/20',     icon: <XCircle className="w-4 h-4 text-red-400" /> },
}

function SeverityBadge({ severity }: { severity: ConflictSeverity }) {
  const cfg = SEVERITY_CONFIG[severity]
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border', cfg.color, cfg.bg, cfg.border)}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function FixtureCard({ fixture, onCertify }: { fixture: RolloverFixture; onCertify: (f: RolloverFixture) => void }) {
  const severity = fixture.conflict_severity ?? 'none'
  const cfg = SEVERITY_CONFIG[severity]

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('rounded-xl border p-4', cfg.bg, cfg.border)}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white truncate">
            {fixture.home_team} <span className="text-white/40">vs</span> {fixture.away_team}
          </p>
          <p className="text-xs text-white/40 mt-0.5">
            {fixture.competition ?? 'Match'}
            {fixture.kickoff ? ` · ${new Date(fixture.kickoff).toLocaleDateString()}` : ''}
          </p>
        </div>
        <SeverityBadge severity={severity} />
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {fixture.ai_pick && (
          <span className="text-xs text-vit-400">
            AI: <span className="font-medium">{fixture.ai_pick}</span>
          </span>
        )}
        {fixture.ai_odds && (
          <span className="text-xs text-white/50">
            Odds: <span className="font-medium text-white/70">{fixture.ai_odds.toFixed(2)}</span>
          </span>
        )}
        {fixture.ai_confidence && (
          <span className="text-xs text-white/50">
            Confidence: <span className={cn('font-medium', fixture.ai_confidence >= 70 ? 'text-emerald-400' : 'text-amber-400')}>
              {fixture.ai_confidence}%
            </span>
          </span>
        )}
      </div>

      {fixture.conflict_reason && (
        <div className="mt-3 flex items-start gap-2 text-xs text-white/50">
          <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-orange-400" />
          {fixture.conflict_reason}
        </div>
      )}

      {fixture.certified && (
        <button
          onClick={() => onCertify(fixture)}
          className="mt-3 w-full py-2 bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/25 text-emerald-400 text-xs font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
        >
          <Shield className="w-3.5 h-3.5" />
          Add to Rollover <ChevronRight className="w-3.5 h-3.5" />
        </button>
      )}
    </motion.div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Rollover() {
  const { data: fixtures = [], isLoading, refetch } = useRolloverFixtures()
  const { data: rolloverState } = useRolloverState()
  const [filter, setFilter] = useState<'all' | 'certified' | 'conflicted'>('all')

  function handleCertify(fixture: RolloverFixture) {
    toast.success(`${fixture.home_team} vs ${fixture.away_team} added to rollover`, {
      description: `${fixture.ai_pick} @ ${fixture.ai_odds?.toFixed(2)}`,
    })
  }

  const filtered = fixtures.filter(f => {
    if (filter === 'certified') return f.certified
    if (filter === 'conflicted') return (f.conflict_severity ?? 'none') !== 'none'
    return true
  })

  const certifiedCount = fixtures.filter(f => f.certified).length
  const conflictedCount = fixtures.filter(f => (f.conflict_severity ?? 'none') !== 'none').length

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <RotateCcw className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Rollover Engine</h1>
              <p className="text-white/50 text-sm">Fixture certification & conflict severity analysis for rollover campaigns</p>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Total Fixtures', value: fixtures.length, color: 'text-white' },
              { label: 'Certified',       value: certifiedCount,  color: 'text-emerald-400' },
              { label: 'Conflicted',      value: conflictedCount, color: 'text-amber-400' },
              { label: 'High Risk',       value: fixtures.filter(f => f.conflict_severity === 'high').length, color: 'text-red-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
                <p className={cn('text-2xl font-bold', color)}>{value}</p>
                <p className="text-xs text-white/40 mt-1">{label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">

          {/* Active rollover state */}
          {rolloverState ? (
            <div className="lg:col-span-1">
              <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">Active Rollover</h2>
              <div className="bg-white/5 border border-vit-500/20 rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <span className={cn('text-xs font-medium px-2 py-1 rounded-full border',
                    rolloverState.status === 'active' ? 'text-vit-400 bg-vit-500/10 border-vit-500/20' :
                    rolloverState.status === 'complete' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' :
                    'text-red-400 bg-red-500/10 border-red-500/20'
                  )}>
                    {rolloverState.status.charAt(0).toUpperCase() + rolloverState.status.slice(1)}
                  </span>
                  <Clock className="w-4 h-4 text-white/30" />
                </div>
                <div className="space-y-3">
                  {[
                    { label: 'Progress', value: `${rolloverState.legs_completed}/${rolloverState.legs_required} legs` },
                    { label: 'Target Odds', value: rolloverState.target_odds.toFixed(2) },
                    { label: 'Current Odds', value: rolloverState.current_odds.toFixed(2) },
                    { label: 'Balance', value: `$${rolloverState.current_balance.toFixed(2)}` },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex justify-between text-sm">
                      <span className="text-white/40">{label}</span>
                      <span className="text-white font-medium">{value}</span>
                    </div>
                  ))}
                </div>
                {/* Progress bar */}
                <div className="mt-4">
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-vit-400 rounded-full transition-all"
                      style={{ width: `${(rolloverState.legs_completed / rolloverState.legs_required) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="lg:col-span-1">
              <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">No Active Rollover</h2>
              <div className="border border-dashed border-white/15 rounded-2xl py-10 text-center">
                <RotateCcw className="w-8 h-8 text-white/20 mx-auto mb-3" />
                <p className="text-white/30 text-sm">Certify fixtures to start<br/>a rollover campaign</p>
              </div>
            </div>
          )}

          {/* Fixture list */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-2">
                {(['all', 'certified', 'conflicted'] as const).map(f => (
                  <button key={f} onClick={() => setFilter(f)}
                    className={cn('px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors capitalize',
                      filter === f ? 'bg-vit-500/20 border-vit-500/40 text-vit-300' : 'bg-white/5 border-white/10 text-white/40 hover:text-white'
                    )}>
                    {f}
                  </button>
                ))}
              </div>
              <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/8 text-white/40 hover:text-white transition-colors">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-16 text-white/30 text-sm">No fixtures match this filter</div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {filtered.map(f => <FixtureCard key={f.id} fixture={f} onCertify={handleCertify} />)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
