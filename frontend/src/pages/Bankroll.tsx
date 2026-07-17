import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
  Wallet, Calculator, TrendingDown, Shield,
  Info, AlertTriangle, CheckCircle2, BarChart3,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Kelly Criterion ────────────────────────────────────────────────────────────

interface KellyResult {
  fraction: number          // full Kelly fraction
  halfKelly: number
  quarterKelly: number
  stake: number             // recommended stake given bankroll
  ev: number
  impliedEdge: number
}

function calcKelly(bankroll: number, odds: number, confidence: number): KellyResult {
  const p = confidence / 100
  const q = 1 - p
  const b = odds - 1                  // decimal odds − 1 = net odds
  const fraction = Math.max(0, (b * p - q) / b)
  const ev = p * b - q                // per unit wagered
  const impliedEdge = (p - 1 / odds) * 100
  return {
    fraction,
    halfKelly: fraction / 2,
    quarterKelly: fraction / 4,
    stake: bankroll * fraction,
    ev,
    impliedEdge,
  }
}

// ── Drawdown simulation ────────────────────────────────────────────────────────

interface DrawdownPoint { bet: number; balance: number; drawdown: number }

function simulateDrawdown(bankroll: number, fraction: number, winRate: number, bets: number): DrawdownPoint[] {
  let balance = bankroll
  let peak = balance
  const points: DrawdownPoint[] = [{ bet: 0, balance, drawdown: 0 }]
  for (let i = 1; i <= bets; i++) {
    const win = Math.random() < winRate / 100
    if (win) balance *= (1 + fraction * 1.9)  // simplified 1.9 net return
    else balance *= (1 - fraction)
    balance = Math.max(0, balance)
    peak = Math.max(peak, balance)
    const drawdown = peak > 0 ? ((peak - balance) / peak) * 100 : 0
    points.push({ bet: i, balance: Math.round(balance * 100) / 100, drawdown: Math.round(drawdown * 10) / 10 })
  }
  return points
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function KellyCard({ label, pct, stake, color }: { label: string; pct: number; stake: number; color: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <p className="text-xs text-white/40 mb-2">{label}</p>
      <p className={cn('text-2xl font-bold', color)}>{(pct * 100).toFixed(1)}%</p>
      <p className="text-sm text-white/50 mt-1">${stake.toFixed(2)} stake</p>
    </div>
  )
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-800 border border-white/15 rounded-xl p-3 shadow-xl text-xs">
      <p className="text-white/50 mb-1.5">Bet #{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name === 'balance' ? `$${Number(p.value).toFixed(2)}` : `${Number(p.value).toFixed(1)}%`}
        </p>
      ))}
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Bankroll() {
  const [bankroll, setBankroll] = useState(1000)
  const [odds, setOdds] = useState(2.0)
  const [confidence, setConfidence] = useState(65)
  const [winRate, setWinRate] = useState(58)
  const [numBets, setNumBets] = useState(100)
  const [simSeed, setSimSeed] = useState(0)   // re-run simulation

  const kelly = useMemo(() => calcKelly(bankroll, odds, confidence), [bankroll, odds, confidence])

  const simData = useMemo(() => {
    void simSeed
    return simulateDrawdown(bankroll, kelly.halfKelly, winRate, numBets)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bankroll, kelly.halfKelly, winRate, numBets, simSeed])

  const maxDrawdown = simData.reduce((m, p) => Math.max(m, p.drawdown), 0)
  const finalBalance = simData[simData.length - 1]?.balance ?? bankroll
  const roi = ((finalBalance - bankroll) / bankroll) * 100

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Wallet className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Bankroll Manager</h1>
              <p className="text-white/50 text-sm">Kelly Criterion staking calculator &amp; drawdown tracker</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">

          {/* ── Left — inputs ── */}
          <div className="lg:col-span-1 space-y-6">

            {/* Kelly inputs */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-5">
                <Calculator className="w-4 h-4 text-vit-400" />
                <h2 className="text-sm font-semibold text-white">Kelly Calculator</h2>
              </div>

              {[
                { label: `Bankroll ($)`, value: bankroll, set: setBankroll, min: 10, max: 100000, step: 10, format: (v: number) => `$${v.toLocaleString()}` },
                { label: `Decimal Odds`, value: odds, set: setOdds, min: 1.1, max: 10, step: 0.1, format: (v: number) => v.toFixed(2) },
                { label: `Model Confidence (%)`, value: confidence, set: setConfidence, min: 50, max: 95, step: 1, format: (v: number) => `${v}%` },
              ].map(({ label, value, set, min, max, step, format }) => (
                <div key={label} className="mb-4">
                  <div className="flex justify-between text-xs text-white/50 mb-1.5">
                    <span>{label}</span>
                    <span className="text-vit-400 font-medium">{format(value)}</span>
                  </div>
                  <input type="range" min={min} max={max} step={step} value={value}
                    onChange={e => set(Number(e.target.value))}
                    className="w-full accent-vit-400" />
                </div>
              ))}

              {/* EV indicator */}
              <div className={cn('flex items-start gap-2 text-xs rounded-xl px-3 py-2.5 border',
                kelly.ev > 0
                  ? 'text-emerald-300/80 bg-emerald-500/8 border-emerald-500/20'
                  : 'text-red-300/80 bg-red-500/8 border-red-500/20'
              )}>
                {kelly.ev > 0 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                               : <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />}
                <span>
                  {kelly.ev > 0
                    ? `Positive edge: +${(kelly.ev * 100).toFixed(1)}¢ per $1 wagered`
                    : 'Negative edge — Kelly recommends no bet (0% stake)'}
                </span>
              </div>

              {kelly.impliedEdge > 0 && (
                <div className="mt-2 flex items-center gap-2 text-xs text-white/40">
                  <Info className="w-3 h-3 flex-shrink-0" />
                  Implied edge over market: {kelly.impliedEdge.toFixed(1)}%
                </div>
              )}
            </div>

            {/* Simulation inputs */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-5">
                <TrendingDown className="w-4 h-4 text-red-400" />
                <h2 className="text-sm font-semibold text-white">Drawdown Simulation</h2>
              </div>

              {[
                { label: `Historical Win Rate (%)`, value: winRate, set: setWinRate, min: 40, max: 80, step: 1, format: (v: number) => `${v}%` },
                { label: `Number of Bets`, value: numBets, set: setNumBets, min: 20, max: 500, step: 10, format: (v: number) => String(v) },
              ].map(({ label, value, set, min, max, step, format }) => (
                <div key={label} className="mb-4">
                  <div className="flex justify-between text-xs text-white/50 mb-1.5">
                    <span>{label}</span>
                    <span className="text-vit-400 font-medium">{format(value)}</span>
                  </div>
                  <input type="range" min={min} max={max} step={step} value={value}
                    onChange={e => set(Number(e.target.value))}
                    className="w-full accent-vit-400" />
                </div>
              ))}

              <button onClick={() => setSimSeed(s => s + 1)}
                className="w-full py-2.5 bg-white/8 hover:bg-white/12 border border-white/10 text-white/60 hover:text-white text-sm rounded-xl transition-colors">
                Re-run Simulation
              </button>
            </div>
          </div>

          {/* ── Right — results ── */}
          <div className="lg:col-span-2 space-y-6">

            {/* Kelly recommendations */}
            <div>
              <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-4">Kelly Recommendations</h2>
              <div className="grid grid-cols-3 gap-4">
                <KellyCard label="Full Kelly" pct={kelly.fraction} stake={kelly.fraction * bankroll} color="text-red-400" />
                <KellyCard label="Half Kelly ✦ Recommended" pct={kelly.halfKelly} stake={kelly.halfKelly * bankroll} color="text-vit-400" />
                <KellyCard label="Quarter Kelly" pct={kelly.quarterKelly} stake={kelly.quarterKelly * bankroll} color="text-emerald-400" />
              </div>
              <p className="text-xs text-white/30 mt-3 flex items-center gap-1.5">
                <Shield className="w-3 h-3" />
                Half Kelly reduces variance significantly with minimal ROI sacrifice — recommended for most bettors.
              </p>
            </div>

            {/* Simulation KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: 'Final Balance', value: `$${finalBalance.toFixed(2)}`, color: finalBalance >= bankroll ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Simulated ROI', value: `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`, color: roi >= 0 ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Max Drawdown', value: `${maxDrawdown.toFixed(1)}%`, color: 'text-red-400' },
                { label: 'Bets Simulated', value: String(numBets), color: 'text-white' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4">
                  <p className="text-xs text-white/40 mb-1">{label}</p>
                  <p className={cn('text-xl font-bold', color)}>{value}</p>
                </div>
              ))}
            </div>

            {/* Balance chart */}
            <div className="bg-white/5 border border-white/8 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-vit-400" />
                <h3 className="text-sm font-semibold text-white">Balance Simulation (Half Kelly)</h3>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={simData} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="bankrollGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="bet" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Bets', fill: 'rgba(255,255,255,0.3)', fontSize: 10, position: 'insideBottom', offset: -5 }} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="balance" stroke="#818cf8" strokeWidth={2} fill="url(#bankrollGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Drawdown chart */}
            <div className="bg-white/5 border border-white/8 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingDown className="w-4 h-4 text-red-400" />
                <h3 className="text-sm font-semibold text-white">Drawdown Tracker</h3>
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={simData} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="bet" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="drawdown" stroke="#f87171" strokeWidth={1.5} fill="url(#ddGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
