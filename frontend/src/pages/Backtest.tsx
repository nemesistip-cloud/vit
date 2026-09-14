import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from '@/lib/recharts'
import {
  FlaskConical, TrendingUp, TrendingDown, BarChart3,
  RefreshCw, Calendar, Target, Activity, AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface BacktestResult {
  equity_curve?: { date: string; balance: number; drawdown: number }[]
  metrics?: {
    total_bets: number
    wins: number
    losses: number
    win_rate: number
    roi: number
    max_drawdown: number
    sharpe_ratio?: number
    profit_factor?: number
    avg_odds?: number
    total_profit: number
    starting_bank: number
    ending_bank: number
  }
  sport_breakdown?: { sport: string; bets: number; win_rate: number; roi: number }[]
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useBacktest(params: {
  sport: string; strategy: string; stake_pct: number
  date_from: string; date_to: string; min_confidence: number
}) {
  return useQuery<BacktestResult>({
    queryKey: ['backtest', params],
    queryFn: async ({ signal }) => {
      const qs = new URLSearchParams({
        sport: params.sport,
        strategy: params.strategy,
        stake_pct: String(params.stake_pct),
        date_from: params.date_from,
        date_to: params.date_to,
        min_confidence: String(params.min_confidence),
      }).toString()
      const r = await fetch(`${ENDPOINTS.gateway}/api/backtest/run?${qs}`, {
        signal, headers: authHeaders(),
      })
      if (r.ok) return r.json()
      const body = await r.json().catch(() => ({}))
      throw new Error(body?.detail?.message || body?.detail || `Backtest unavailable (HTTP ${r.status})`)
    },
    retry: false,
    staleTime: 300_000,
    enabled: false, // only runs on demand
  })
}


// ── Custom tooltip ─────────────────────────────────────────────────────────────

function EquityTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-800 border border-white/15 rounded-xl p-3 shadow-xl text-xs">
      <p className="text-white/50 mb-1.5">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name === 'balance' ? `$${Number(p.value).toFixed(2)}` : `${Number(p.value).toFixed(1)}%`}
        </p>
      ))}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Backtest() {
  const today = new Date().toISOString().slice(0, 10)
  const threeMonthsAgo = new Date(Date.now() - 90 * 86400_000).toISOString().slice(0, 10)

  const [sport, setSport] = useState('all')
  const [strategy, setStrategy] = useState('flat')
  const [stakePct, setStakePct] = useState(2)
  const [dateFrom, setDateFrom] = useState(threeMonthsAgo)
  const [dateTo, setDateTo] = useState(today)
  const [minConfidence, setMinConfidence] = useState(60)
  const [hasRun, setHasRun] = useState(false)
  const [localResult, setLocalResult] = useState<BacktestResult | null>(null)
  const [runError, setRunError] = useState<string | null>(null)

  const { isFetching, refetch } = useBacktest({ sport, strategy, stake_pct: stakePct, date_from: dateFrom, date_to: dateTo, min_confidence: minConfidence })

  async function runBacktest() {
    setHasRun(true)
    setRunError(null)
    setLocalResult(null)
    try {
      const { data } = await refetch()
      if (data) setLocalResult(data)
      else setRunError('Backtest returned no measured result.')
    } catch (error) {
      setRunError(error instanceof Error ? error.message : 'Backtest is unavailable.')
    }
  }

  const result = localResult
  const metrics = result?.metrics
  const equity = result?.equity_curve ?? []

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <FlaskConical className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Backtest</h1>
              <p className="text-white/50 text-sm">Historical simulation — P&amp;L curve, drawdown &amp; per-sport performance</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-4 gap-8">

          {/* Config panel */}
          <div className="lg:col-span-1">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-5 sticky top-20">
              <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Parameters</h2>

              <div>
                <label className="text-xs text-white/50 block mb-1.5">Sport</label>
                <select value={sport} onChange={e => setSport(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-vit-500/50">
                  <option value="all">All Sports</option>
                  <option value="football">Football</option>
                  <option value="basketball">Basketball</option>
                  <option value="tennis">Tennis</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-white/50 block mb-1.5">Staking Strategy</label>
                <select value={strategy} onChange={e => setStrategy(e.target.value)}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-vit-500/50">
                  <option value="flat">Flat Stake</option>
                  <option value="kelly">Kelly Criterion</option>
                  <option value="proportional">Proportional</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-white/50 block mb-1.5">Stake % of Bankroll</label>
                <input type="range" min={1} max={10} value={stakePct} onChange={e => setStakePct(Number(e.target.value))}
                  className="w-full accent-vit-400" />
                <div className="flex justify-between text-xs text-white/40 mt-1">
                  <span>1%</span><span className="text-vit-400 font-medium">{stakePct}%</span><span>10%</span>
                </div>
              </div>

              <div>
                <label className="text-xs text-white/50 block mb-1.5">Min Confidence</label>
                <input type="range" min={50} max={90} step={5} value={minConfidence} onChange={e => setMinConfidence(Number(e.target.value))}
                  className="w-full accent-vit-400" />
                <div className="flex justify-between text-xs text-white/40 mt-1">
                  <span>50%</span><span className="text-vit-400 font-medium">{minConfidence}%</span><span>90%</span>
                </div>
              </div>

              <div>
                <label className="text-xs text-white/50 block mb-1.5">Date Range</label>
                <div className="space-y-2">
                  <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-vit-500/50" />
                  <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-vit-500/50" />
                </div>
              </div>

              <button onClick={runBacktest} disabled={isFetching}
                className="w-full py-3 bg-vit-500 hover:bg-vit-400 disabled:bg-vit-500/40 text-white font-semibold text-sm rounded-xl transition-all flex items-center justify-center gap-2">
                {isFetching ? <Spinner className="w-4 h-4" /> : <FlaskConical className="w-4 h-4" />}
                Run Simulation
              </button>
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-3">
            {!hasRun ? (
              <div className="border border-dashed border-white/15 rounded-2xl py-20 text-center">
                <FlaskConical className="w-10 h-10 text-white/20 mx-auto mb-4" />
                <p className="text-white/40 text-sm">Configure parameters and run a simulation</p>
              </div>
            ) : isFetching ? (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <Spinner className="w-8 h-8" />
                <p className="text-white/40 text-sm">Running simulation…</p>
              </div>
            ) : runError ? (
              <div className="border border-amber-500/25 bg-amber-500/5 rounded-2xl py-20 px-6 text-center">
                <AlertCircle className="w-10 h-10 text-amber-400 mx-auto mb-4" />
                <p className="text-white font-medium">Backtest unavailable</p>
                <p className="text-white/45 text-sm mt-2 max-w-md mx-auto">{runError}</p>
              </div>
            ) : metrics ? (
              <div className="space-y-6">
                {/* KPI grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    { label: 'ROI', value: `${metrics.roi >= 0 ? '+' : ''}${metrics.roi.toFixed(1)}%`, color: metrics.roi >= 0 ? 'text-emerald-400' : 'text-red-400' },
                    { label: 'Win Rate', value: `${metrics.win_rate.toFixed(1)}%`, color: 'text-vit-400' },
                    { label: 'Max Drawdown', value: `${metrics.max_drawdown.toFixed(1)}%`, color: 'text-red-400' },
                    { label: 'Total Bets', value: String(metrics.total_bets), color: 'text-white' },
                    { label: 'Total P&L', value: `${metrics.total_profit >= 0 ? '+' : ''}$${metrics.total_profit.toFixed(2)}`, color: metrics.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400' },
                    { label: 'Sharpe Ratio', value: metrics.sharpe_ratio?.toFixed(2) ?? '—', color: 'text-sky-400' },
                    { label: 'Profit Factor', value: metrics.profit_factor?.toFixed(2) ?? '—', color: 'text-sky-400' },
                    { label: 'Avg Odds', value: metrics.avg_odds?.toFixed(2) ?? '—', color: 'text-white' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-3">
                      <p className="text-xs text-white/40 mb-1">{label}</p>
                      <p className={cn('text-xl font-bold', color)}>{value}</p>
                    </div>
                  ))}
                </div>

                {/* Equity curve */}
                <div className="bg-white/5 border border-white/8 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="w-4 h-4 text-vit-400" />
                    <h3 className="text-sm font-semibold text-white">P&amp;L Curve</h3>
                    <span className="ml-auto text-xs text-white/30">
                      ${metrics.starting_bank.toFixed(0)} → ${metrics.ending_bank.toFixed(2)}
                    </span>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={equity} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                      <defs>
                        <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${v}`} />
                      <Tooltip content={<EquityTooltip />} />
                      <ReferenceLine y={metrics.starting_bank} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 2" />
                      <Area type="monotone" dataKey="balance" stroke="#818cf8" strokeWidth={2} fill="url(#balGrad)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Drawdown chart */}
                <div className="bg-white/5 border border-white/8 rounded-2xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingDown className="w-4 h-4 text-red-400" />
                    <h3 className="text-sm font-semibold text-white">Drawdown (%)</h3>
                  </div>
                  <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={equity} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v}%`} />
                      <Tooltip content={<EquityTooltip />} />
                      <Line type="monotone" dataKey="drawdown" stroke="#f87171" strokeWidth={1.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Sport breakdown */}
                {result?.sport_breakdown && (
                  <div className="bg-white/5 border border-white/8 rounded-2xl p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <BarChart3 className="w-4 h-4 text-sky-400" />
                      <h3 className="text-sm font-semibold text-white">Sport Breakdown</h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-xs text-white/40 border-b border-white/8">
                            <th className="pb-2 font-medium">Sport</th>
                            <th className="pb-2 font-medium">Bets</th>
                            <th className="pb-2 font-medium">Win Rate</th>
                            <th className="pb-2 font-medium">ROI</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {result.sport_breakdown.map(row => (
                            <tr key={row.sport}>
                              <td className="py-2.5 text-white font-medium">{row.sport}</td>
                              <td className="py-2.5 text-white/70">{row.bets}</td>
                              <td className="py-2.5 text-vit-400">{row.win_rate.toFixed(1)}%</td>
                              <td className={cn('py-2.5 font-medium', row.roi >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                                {row.roi >= 0 ? '+' : ''}{row.roi.toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
