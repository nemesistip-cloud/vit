import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from '@/lib/recharts'
import {
  BarChart3, TrendingUp, Activity, Users, Brain,
  RefreshCw, AlertCircle, CheckCircle2, Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface ModelMetric {
  model_name: string
  accuracy?: number
  roi?: number
  predictions?: number
  active?: boolean
}

interface AnalyticsSummary {
  total_predictions?: number
  accuracy_7d?: number
  active_users?: number
  model_accuracy?: ModelMetric[]
  accuracy_over_time?: { date: string; accuracy: number; predictions: number }[]
  sport_breakdown?: { sport: string; count: number; accuracy: number }[]
}

interface SystemHealth {
  services?: Record<string, { status: string; latency?: number }>
  uptime?: number
  error_rate?: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useAnalytics() {
  return useQuery<AnalyticsSummary>({
    queryKey: ['analytics-summary'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/analytics/summary`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : {}
    },
    retry: false,
    staleTime: 60_000,
    refetchInterval: 120_000,
  })
}

function useSystemHealth() {
  return useQuery<SystemHealth>({
    queryKey: ['system-health'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/health`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : {}
    },
    retry: false,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}

// ── Custom tooltip ─────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-800 border border-white/15 rounded-xl p-3 shadow-xl text-xs">
      <p className="text-white/50 mb-1.5">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
          {p.name.toLowerCase().includes('accuracy') || p.name.toLowerCase().includes('roi') ? '%' : ''}
        </p>
      ))}
    </div>
  )
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KPI({
  label, value, sub, icon: Icon, color, delay,
}: {
  label: string; value: string; sub?: string
  icon: React.ElementType; color: string; delay: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-surface-800/60 border border-white/8 rounded-xl p-5"
    >
      <Icon className={cn('w-4 h-4 mb-3', color)} />
      <p className={cn('text-2xl font-bold mb-0.5', color)}>{value}</p>
      <p className="text-xs text-white/40">{label}</p>
      {sub && <p className="text-[11px] text-white/25 mt-0.5">{sub}</p>}
    </motion.div>
  )
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="h-[220px] flex flex-col items-center justify-center text-center border border-dashed border-white/8 rounded-xl bg-white/[0.02]">
      <BarChart3 className="w-7 h-7 text-white/15 mb-2" />
      <p className="text-sm text-white/40">{message}</p>
      <p className="text-xs text-white/25 mt-1">No verified records are available yet.</p>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Analytics() {
  const { data: analytics, isLoading, isError, refetch, isFetching } = useAnalytics()
  const { data: health } = useSystemHealth()

  const accuracyData = analytics?.accuracy_over_time ?? []
  const sportsData = analytics?.sport_breakdown ?? []
  const modelsData = analytics?.model_accuracy ?? []

  const CHART_STYLE = {
    '--recharts-tooltip-bg': 'transparent',
  } as React.CSSProperties

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2.5 mb-1">
                <BarChart3 className="w-5 h-5 text-vit-400" />
                <h1 className="text-2xl font-bold text-white">Network Intelligence</h1>
              </div>
              <p className="text-white/45 text-sm">Real-time model performance, accuracy trends, and system health.</p>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white/60 text-sm hover:text-white hover:bg-white/8 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', isFetching && 'animate-spin')} />
              Refresh
            </button>
          </div>
        </motion.div>

        {/* KPI row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <KPI delay={0}    label="Total Predictions"  value={analytics?.total_predictions != null ? analytics.total_predictions.toLocaleString() : (isLoading ? '…' : '—')} icon={Brain}     color="text-vit-400"    />
          <KPI delay={0.05} label="7-day Accuracy"     value={analytics?.accuracy_7d != null ? `${analytics.accuracy_7d.toFixed(1)}%` : (isLoading ? '…' : '—')}             icon={TrendingUp} color="text-emerald-400" />
          <KPI delay={0.1}  label="Active Users"       value={analytics?.active_users != null ? analytics.active_users.toLocaleString() : (isLoading ? '…' : '—')}           icon={Users}      color="text-sky-400"    />
          <KPI delay={0.15} label="Models Deployed"    value={isLoading ? '…' : modelsData.filter(m => m.active).length.toString()}                  icon={Activity}   color="text-purple-400" />
        </div>

        {isError && (
          <div className="flex items-center gap-2 text-xs text-amber-400 mb-5 p-3 rounded-lg bg-amber-500/8 border border-amber-500/15">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            Analytics data is temporarily unavailable. No sample values are shown.
          </div>
        )}

        {/* Accuracy over time */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-800/50 border border-white/8 rounded-2xl p-6 mb-5"
        >
          <h2 className="font-semibold text-white mb-5">Model Accuracy — 14 Days</h2>
          {accuracyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={accuracyData} style={CHART_STYLE}>
                <defs>
                  <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[50, 85]}
                  tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  name="Accuracy"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fill="url(#accGrad)"
                  dot={false}
                  activeDot={{ r: 4, fill: '#6366f1' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart message="Accuracy history is not available" />
          )}
        </motion.div>

        <div className="grid sm:grid-cols-2 gap-5 mb-5">
          {/* Sport breakdown */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-surface-800/50 border border-white/8 rounded-2xl p-6"
          >
            <h2 className="font-semibold text-white mb-5">Predictions by Sport</h2>
            {sportsData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={sportsData} barSize={24}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="sport" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Predictions" fill="#6366f1" radius={[4, 4, 0, 0]} fillOpacity={0.8} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message="Sport totals are not available" />
            )}
          </motion.div>

          {/* Accuracy by sport */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-surface-800/50 border border-white/8 rounded-2xl p-6"
          >
            <h2 className="font-semibold text-white mb-5">Accuracy by Sport (%)</h2>
            {sportsData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={sportsData} barSize={24}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="sport" tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[50, 80]} tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="accuracy" name="Accuracy" fill="#10b981" radius={[4, 4, 0, 0]} fillOpacity={0.8} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message="Sport accuracy is not available" />
            )}
          </motion.div>
        </div>

        {/* Model table */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-surface-800/50 border border-white/8 rounded-2xl overflow-hidden mb-5"
        >
          <div className="px-6 py-5 border-b border-white/6">
            <h2 className="font-semibold text-white">Model Performance</h2>
          </div>
          {modelsData.length > 0 ? <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] text-white/30 uppercase border-b border-white/6">
                  <th className="text-left px-6 py-3">Model</th>
                  <th className="text-center px-4 py-3">Accuracy</th>
                  <th className="text-center px-4 py-3">ROI</th>
                  <th className="text-center px-4 py-3">Predictions</th>
                  <th className="text-center px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {modelsData.map((m, i) => (
                  <tr key={m.model_name} className="border-b border-white/4 hover:bg-white/2 transition-colors">
                    <td className="px-6 py-3.5 font-medium text-white">{m.model_name}</td>
                    <td className="px-4 py-3.5 text-center">
                      <span className={cn('font-semibold', (m.accuracy ?? 0) >= 65 ? 'text-emerald-400' : 'text-amber-400')}>
                        {m.accuracy?.toFixed(1) ?? '—'}%
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <span className={cn('font-semibold', (m.roi ?? 0) > 0 ? 'text-emerald-400' : 'text-red-400')}>
                        {m.roi != null ? `${m.roi > 0 ? '+' : ''}${m.roi.toFixed(1)}%` : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-center text-white/60">{m.predictions?.toLocaleString() ?? '—'}</td>
                    <td className="px-4 py-3.5 text-center">
                      {m.active ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
                          <CheckCircle2 className="w-3 h-3" />Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-white/30">
                          <Clock className="w-3 h-3" />Inactive
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div> : (
            <div className="px-6 py-12">
              <EmptyChart message="Model performance is not available" />
            </div>
          )}
        </motion.div>

        {/* System health */}
        {health?.services && Object.keys(health.services).length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-surface-800/50 border border-white/8 rounded-2xl p-6"
          >
            <h2 className="font-semibold text-white mb-4">System Health</h2>
            <div className="grid sm:grid-cols-3 gap-3">
              {Object.entries(health.services).map(([name, svc]: [string, any]) => (
                <div key={name} className="flex items-center justify-between p-3 rounded-lg bg-white/3 border border-white/6">
                  <span className="text-sm text-white/70 capitalize">{name}</span>
                  <div className="flex items-center gap-2">
                    {svc.latency != null && <span className="text-xs text-white/30">{svc.latency}ms</span>}
                    <span className={cn(
                      'w-2 h-2 rounded-full',
                      svc.status === 'healthy' || svc.status === 'ok' ? 'bg-emerald-400' :
                      svc.status === 'degraded' ? 'bg-amber-400' : 'bg-red-400',
                    )} />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
