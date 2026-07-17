import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3, TrendingUp, Target, Award,
  ArrowUp, ArrowDown, Brain, Calendar,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Overview {
  total_predictions: number
  correct: number
  accuracy_pct: number
  roi_pct: number
  total_staked_vit: number
  total_returned_vit: number
  net_pnl_vit: number
  best_market: string
  best_market_acc: number
  worst_market: string
  worst_market_acc: number
  current_streak: number
  best_streak: number
  markets_traded: string[]
}

interface ROIPoint {
  day: string
  roi_pct: number
}

interface PnLRow {
  market: string
  bets: number
  correct: number
  roi_pct: number
  pnl_vit: number
}

interface ModelRow {
  model: string
  accuracy: number
  roc_auc: number
  roi_pct: number
  predictions: number
  correct: number
}

interface CalibrationPoint {
  predicted_prob: number
  observed_freq: number
  sample_size: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

const BASE = () => `${ENDPOINTS.gateway}/api/analytics-studio`

function useOverview() {
  return useQuery({
    queryKey: ['studio-overview'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/overview`, { signal, headers: authHeaders() })
      return r.ok ? (r.json() as Promise<Overview>) : null
    },
    staleTime: 60_000,
  })
}

function useROICurve(days: number) {
  return useQuery({
    queryKey: ['studio-roi', days],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/roi-curve?days=${days}`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { curve: [] }
    },
    staleTime: 120_000,
  })
}

function usePnLBreakdown() {
  return useQuery({
    queryKey: ['studio-pnl'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/pnl-breakdown`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { markets: [] }
    },
    staleTime: 120_000,
  })
}

function useModelComparison(sortBy: string) {
  return useQuery({
    queryKey: ['studio-models', sortBy],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/model-comparison?sort_by=${sortBy}`, { signal })
      return r.ok ? r.json() : { models: [] }
    },
    staleTime: 120_000,
  })
}

function useCalibration() {
  return useQuery({
    queryKey: ['studio-calibration'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/calibration`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { calibration: [] }
    },
    staleTime: 180_000,
  })
}

// ── Mini bar chart (CSS) ──────────────────────────────────────────────────────

function MiniROIChart({ data }: { data: ROIPoint[] }) {
  if (!data?.length) return null
  const values = data.map(d => d.roi_pct)
  const min    = Math.min(...values)
  const max    = Math.max(...values)
  const range  = max - min || 1
  const recent = data.slice(-20)

  return (
    <div className="flex items-end gap-0.5 h-16">
      {recent.map((pt, i) => {
        const h   = ((pt.roi_pct - min) / range) * 100
        const pos = pt.roi_pct >= 0
        return (
          <div
            key={i}
            title={`${pt.day}: ${pt.roi_pct.toFixed(1)}%`}
            className={cn(
              'flex-1 rounded-sm min-h-[2px] transition-all',
              pos ? 'bg-emerald-500/60 hover:bg-emerald-500' : 'bg-red-500/40 hover:bg-red-500',
            )}
            style={{ height: `${Math.max(4, h)}%` }}
          />
        )
      })}
    </div>
  )
}

// ── Calibration chart ─────────────────────────────────────────────────────────

function CalibrationChart({ data }: { data: CalibrationPoint[] }) {
  if (!data?.length) return null
  return (
    <div className="relative h-40 mt-2">
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map(v => (
        <div
          key={v}
          className="absolute left-0 right-0 border-t border-white/5"
          style={{ bottom: `${v * 100}%` }}
        >
          <span className="absolute right-full pr-1 text-xs text-white/30 -translate-y-1/2">{(v * 100).toFixed(0)}%</span>
        </div>
      ))}
      {/* Perfect calibration line */}
      <div className="absolute inset-0 border-l border-b border-white/10">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <line x1="0" y1="100" x2="100" y2="0" stroke="rgba(255,255,255,0.15)" strokeWidth="1" strokeDasharray="4,4" />
          {data.map((pt, i) => (
            <circle
              key={i}
              cx={pt.predicted_prob * 100}
              cy={(1 - pt.observed_freq) * 100}
              r="3"
              fill="rgb(139, 92, 246)"
              fillOpacity={0.8}
            >
              <title>Predicted {(pt.predicted_prob * 100).toFixed(0)}% → Observed {(pt.observed_freq * 100).toFixed(0)}% (n={pt.sample_size})</title>
            </circle>
          ))}
        </svg>
      </div>
    </div>
  )
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KPI({ label, value, sub, positive }: { label: string; value: string | number; sub?: string; positive?: boolean }) {
  return (
    <div className="bg-white/3 border border-white/8 rounded-xl p-4">
      <p className="text-xs text-white/40 mb-1">{label}</p>
      <p className={cn('text-xl font-bold', positive === undefined ? 'text-white' : positive ? 'text-emerald-400' : 'text-red-400')}>
        {value}
      </p>
      {sub && <p className="text-xs text-white/30 mt-0.5">{sub}</p>}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyticsStudio() {
  const navigate = useNavigate()
  const [tab,    setTab]    = useState<'personal' | 'models'>('personal')
  const [days,   setDays]   = useState(30)
  const [sortBy, setSortBy] = useState<'roi_pct' | 'accuracy' | 'roc_auc'>('roi_pct')

  useEffect(() => {
    if (!getAuthToken()) navigate('/login')
  }, [navigate])

  const { data: overview,   isLoading: overviewLoading } = useOverview()
  const { data: roiData,    isLoading: roiLoading       } = useROICurve(days)
  const { data: pnlData,    isLoading: pnlLoading       } = usePnLBreakdown()
  const { data: modelData,  isLoading: modelLoading     } = useModelComparison(sortBy)
  const { data: calibData                               } = useCalibration()

  const roiCurve: ROIPoint[]        = roiData?.curve   ?? []
  const pnlMarkets: PnLRow[]        = pnlData?.markets ?? []
  const models: ModelRow[]          = modelData?.models ?? []
  const calibration: CalibrationPoint[] = calibData?.calibration ?? []

  const TABS = [
    { id: 'personal', label: 'My Analytics', icon: Target },
    { id: 'models',   label: 'Model Comparison', icon: Brain  },
  ] as const

  return (
    <div className="min-h-screen bg-surface-950 pt-24 pb-16">
      <div className="max-w-5xl mx-auto px-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 bg-vit-500/15 border border-vit-500/25 rounded-xl">
              <BarChart3 className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Analytics Studio</h1>
              <p className="text-white/50 text-sm">Deep-dive into your prediction performance & AI model rankings</p>
            </div>
          </div>
        </motion.div>

        {/* Tab bar */}
        <div className="flex gap-1 mb-6 bg-white/3 border border-white/8 rounded-xl p-1 max-w-sm">
          {TABS.map(t => {
            const Icon = t.icon
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all',
                  tab === t.id ? 'bg-vit-500/20 text-vit-300 border border-vit-500/30' : 'text-white/50 hover:text-white/80',
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Personal analytics */}
        {tab === 'personal' && (
          <div className="space-y-6">
            {overviewLoading && <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>}
            {overview && (
              <>
                {/* KPI grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <KPI label="Accuracy"        value={`${overview.accuracy_pct}%`}    positive={overview.accuracy_pct >= 55} />
                  <KPI label="ROI"             value={`${overview.roi_pct}%`}          positive={overview.roi_pct >= 0} />
                  <KPI label="Net P&L"         value={`${overview.net_pnl_vit} VIT`}  positive={overview.net_pnl_vit >= 0} />
                  <KPI label="Best Streak"     value={overview.best_streak}            />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <KPI label="Total Bets"      value={overview.total_predictions} />
                  <KPI label="Correct"         value={overview.correct} />
                  <KPI label="Staked"          value={`${overview.total_staked_vit} VIT`} />
                  <KPI label="Returned"        value={`${overview.total_returned_vit} VIT`} />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="bg-white/3 border border-white/8 rounded-xl p-3">
                    <p className="text-xs text-white/40 mb-0.5">Best market</p>
                    <p className="font-semibold text-white">{overview.best_market}</p>
                    <p className="text-sm text-emerald-400">{overview.best_market_acc}% accuracy</p>
                  </div>
                  <div className="bg-white/3 border border-white/8 rounded-xl p-3">
                    <p className="text-xs text-white/40 mb-0.5">Worst market</p>
                    <p className="font-semibold text-white">{overview.worst_market}</p>
                    <p className="text-sm text-red-400">{overview.worst_market_acc}% accuracy</p>
                  </div>
                </div>
              </>
            )}

            {/* ROI Curve */}
            <div className="bg-white/3 border border-white/8 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-vit-400" />
                  <span className="text-sm font-semibold text-white">ROI Curve</span>
                </div>
                <div className="flex gap-1">
                  {[7, 30, 90].map(d => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      className={cn(
                        'px-2 py-1 rounded text-xs font-medium transition-all',
                        days === d ? 'bg-vit-500/20 text-vit-300' : 'text-white/40 hover:text-white/70',
                      )}
                    >
                      {d}D
                    </button>
                  ))}
                </div>
              </div>
              {roiLoading ? <div className="h-16 flex items-center justify-center"><Spinner className="w-4 h-4" /></div> : <MiniROIChart data={roiCurve} />}
              {roiCurve.length > 0 && (
                <div className="flex justify-between text-xs text-white/30 mt-2">
                  <span>{roiCurve[0]?.day}</span>
                  <span>Latest: {roiCurve[roiCurve.length - 1]?.roi_pct.toFixed(1)}%</span>
                </div>
              )}
            </div>

            {/* P&L breakdown */}
            <div className="bg-white/3 border border-white/8 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-4">
                <Award className="w-4 h-4 text-vit-400" />
                <span className="text-sm font-semibold text-white">P&L by Market</span>
              </div>
              {pnlLoading ? <Spinner className="w-4 h-4" /> : (
                <div className="space-y-2">
                  {pnlMarkets.map(row => {
                    const maxPnl = Math.max(...pnlMarkets.map(r => Math.abs(r.pnl_vit)))
                    const pct    = Math.abs(row.pnl_vit) / maxPnl * 100
                    return (
                      <div key={row.market} className="flex items-center gap-3">
                        <span className="text-xs text-white/60 w-32 shrink-0">{row.market}</span>
                        <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                          <div
                            className={cn('h-full rounded-full', row.pnl_vit >= 0 ? 'bg-emerald-500/70' : 'bg-red-500/70')}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <div className="text-right w-28 shrink-0">
                          <span className={cn('text-xs font-semibold', row.pnl_vit >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                            {row.pnl_vit >= 0 ? '+' : ''}{row.pnl_vit} VIT
                          </span>
                          <span className="text-xs text-white/30 ml-2">{row.roi_pct}% ROI</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Calibration */}
            {calibration.length > 0 && (
              <div className="bg-white/3 border border-white/8 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-vit-400" />
                  <span className="text-sm font-semibold text-white">Prediction Calibration</span>
                  <span className="text-xs text-white/30">(dashed = perfect)</span>
                </div>
                <CalibrationChart data={calibration} />
                <div className="flex justify-between text-xs text-white/30 mt-1">
                  <span>Predicted probability →</span>
                  <span>↑ Observed frequency</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Model comparison */}
        {tab === 'models' && (
          <div className="space-y-4">
            {/* Sort controls */}
            <div className="flex gap-2 items-center">
              <span className="text-xs text-white/40">Sort by:</span>
              {(['roi_pct', 'accuracy', 'roc_auc'] as const).map(s => (
                <button
                  key={s}
                  onClick={() => setSortBy(s)}
                  className={cn(
                    'px-3 py-1 rounded-lg text-xs font-medium border transition-all',
                    sortBy === s
                      ? 'bg-vit-500/20 text-vit-300 border-vit-500/30'
                      : 'bg-white/3 text-white/50 border-white/10 hover:border-white/20',
                  )}
                >
                  {s === 'roi_pct' ? 'ROI' : s === 'accuracy' ? 'Accuracy' : 'ROC AUC'}
                </button>
              ))}
            </div>

            {modelLoading && <div className="flex justify-center py-8"><Spinner className="w-5 h-5 text-vit-400" /></div>}

            <div className="space-y-2">
              {models.map((m, i) => (
                <motion.div
                  key={m.model}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center gap-3 p-3 bg-white/3 border border-white/8 rounded-xl hover:border-white/15 transition-colors"
                >
                  <div className={cn(
                    'w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0',
                    i === 0 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                    i === 1 ? 'bg-white/10 text-white/60 border border-white/15' :
                    i === 2 ? 'bg-amber-900/30 text-amber-700 border border-amber-700/30' :
                    'bg-white/5 text-white/30 border border-white/8',
                  )}>
                    {i + 1}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{m.model}</p>
                    <p className="text-xs text-white/40">{m.predictions.toLocaleString()} predictions · {m.correct.toLocaleString()} correct</p>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-center">
                      <p className="text-sm font-bold text-white">{(m.accuracy * 100).toFixed(1)}%</p>
                      <p className="text-xs text-white/30">Acc</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-bold text-sky-400">{m.roc_auc.toFixed(3)}</p>
                      <p className="text-xs text-white/30">AUC</p>
                    </div>
                    <div className="text-center">
                      <p className={cn('text-sm font-bold', m.roi_pct >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                        {m.roi_pct >= 0 ? '+' : ''}{m.roi_pct.toFixed(1)}%
                      </p>
                      <p className="text-xs text-white/30">ROI</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
