import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from '@/lib/recharts'
import {
  Shield, Users, Activity, Database, Server,
  TrendingUp, AlertTriangle, RefreshCw, ChevronRight,
  Cpu, Zap, Star, BarChart2, Settings, ClipboardList,
  Wallet as WalletIcon, Layers, CheckCircle2, XCircle,
  Clock, Globe, Lock, Unlock, Play, Trash2, ChevronDown,
} from 'lucide-react'
import { getAuthToken, getStoredUser, authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

function getRequestErrorMessage(payload: any, fallback: string) {
  if (!payload) return fallback
  if (typeof payload === 'string') return payload
  if (payload.detail) return payload.detail
  if (payload.message) return payload.message
  if (payload.error) {
    if (typeof payload.error === 'string') return payload.error
    if (payload.error.message) return payload.error.message
  }
  return fallback
}

async function fetchAdminJson<T>(url: string, init: RequestInit = {}, requireAuth = true): Promise<T> {
  const headers = new Headers(init.headers ?? {})
  if (requireAuth) {
    const token = getAuthToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(url, { ...init, headers })
  if (!response.ok) {
    let payload: any = {}
    try {
      payload = await response.json()
    } catch {
      payload = {}
    }
    throw new Error(getRequestErrorMessage(payload, `Request failed (${response.status})`))
  }

  if (response.status === 204) return null as T
  return response.json() as Promise<T>
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

function useSystemStatus() {
  return useQuery({ queryKey: ['admin-system-status'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/system/status`, { signal })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `System status request failed (${r.status})`))
    }
    return r.json()
  }, staleTime: 30_000, refetchInterval: 30_000 })
}

function ControlPlaneTab() {
  const queryClient = useQueryClient()
  const [mfaCode, setMfaCode] = useState('')
  const reliability = useQuery({ queryKey: ['admin-reliability'], queryFn: async () => {
    const response = await fetch(`${ENDPOINTS.gateway}/api/admin/reliability`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`Reliability unavailable (${response.status})`)
    return response.json()
  }, refetchInterval: 30000 })
  const launch = useQuery({ queryKey: ['admin-token-launch'], queryFn: async () => {
    const response = await fetch(`${ENDPOINTS.gateway}/api/admin/token-launch`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`Token launch unavailable (${response.status})`)
    return response.json()
  } })
  const emergency = useQuery({ queryKey: ['admin-emergency'], queryFn: async () => {
    const response = await fetch(`${ENDPOINTS.gateway}/api/admin/emergency`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`Emergency controls unavailable (${response.status})`)
    return response.json()
  } })
  const updateLaunch = useMutation({
    mutationFn: async (status: string) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/token-launch`, {
        method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, reason: 'Admin control-plane update', confirm: true }),
      })
      if (!response.ok) throw new Error(`Launch update failed (${response.status})`)
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-token-launch'] }); toast.success('Launch state updated') },
    onError: (error: Error) => toast.error(error.message),
  })
  const updateEmergency = useMutation({
    mutationFn: async ({ control, enabled }: { control: string; enabled: boolean }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/emergency/${control}`, {
        method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, reason: 'Admin control-plane update', confirm: true }),
      })
      if (!response.ok) throw new Error(`Emergency update failed (${response.status})`)
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-emergency'] }); toast.success('Emergency control updated') },
    onError: (error: Error) => toast.error(error.message),
  })
  const recover = useMutation({
    mutationFn: async (service: string) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/reliability/${service}/recover`, {
        method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true, reason: 'Admin reliability recovery', mfa_code: mfaCode }),
      })
      if (!response.ok) throw new Error(`Recovery failed (${response.status})`)
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-reliability'] }); toast.success('Recovery requested') },
    onError: (error: Error) => toast.error(error.message),
  })
  const status = launch.data?.status ?? 'DRAFT'
  const controls = emergency.data?.services ?? {}
  return <div className="space-y-6">
    <section className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4"><h3 className="text-lg font-semibold text-white">Reliability</h3><input value={mfaCode} onChange={event => setMfaCode(event.target.value)} inputMode="numeric" placeholder="MFA code" aria-label="MFA code" className="w-28 rounded-lg border border-white/10 bg-surface-900 px-3 py-2 text-sm text-white" /></div>
      <div className="space-y-2">{(reliability.data?.services ?? []).map((service: any) => <div key={service.service} className="flex items-center justify-between border-b border-white/5 py-2 text-sm"><span className="text-white/70 capitalize">{service.service}</span><span className={service.state === 'HEALTHY' ? 'text-emerald-400' : 'text-amber-400'}>{service.state} {service.latency_ms != null ? `(${service.latency_ms}ms)` : ''}</span><button type="button" onClick={() => { if (window.confirm(`Recover ${service.service}?`)) recover.mutate(service.service) }} className="text-vit-400">Recover</button></div>)}</div>
    </section>
    <section className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Token Launch</h3>
      <div className="flex items-center gap-3">
        <select value={status} onChange={event => { if (window.confirm('Change token launch state?')) updateLaunch.mutate(event.target.value) }} className="rounded-lg border border-white/10 bg-surface-900 px-3 py-2 text-sm text-white">
          {['DRAFT', 'PRE_LAUNCH', 'ACTIVE', 'PAUSED', 'SUSPENDED', 'ENDED'].map(value => <option key={value}>{value}</option>)}
        </select>
        <span className="text-sm text-white/40">Persisted launch configuration</span>
      </div>
    </section>
    <section className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Emergency Controls</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {['maintenance', 'withdrawals', 'token', 'validators', 'predictions', 'data', 'markets'].map(control => {
          const enabled = control === 'maintenance' ? emergency.data?.maintenance === true : controls[control] === true
          return <button key={control} type="button" onClick={() => { if (window.confirm(`${enabled ? 'Resume' : 'Pause'} ${control}?`)) updateEmergency.mutate({ control, enabled: !enabled }) }} className={cn('flex items-center justify-between rounded-lg border px-4 py-3 text-sm transition-colors', enabled ? 'border-red-400/40 bg-red-500/10 text-red-300' : 'border-white/10 text-white/60 hover:bg-white/5')}>
            <span className="capitalize">{control}</span><span>{enabled ? 'Enabled' : 'Disabled'}</span>
          </button>
        })}
      </div>
    </section>
  </div>
}
function useAdminHealth() {
  return useQuery({ queryKey: ['admin-health'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/health`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `System health request failed (${r.status})`))
    }
    const data = await r.json()
    return {
      ...data,
      db_connected: data.database?.status === 'connected',
      models_loaded: data.models_ready,
    }
  }, retry: false, staleTime: 30_000, refetchInterval: 30_000 })
}
function useAdminUsers() {
  return useQuery({ queryKey: ['admin-users'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/users?limit=50`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Users request failed (${r.status})`))
    }
    return r.json()
  }, retry: false, staleTime: 60_000 })
}
function useAdminKycQueue(status: string = 'all') {
  return useQuery({
    queryKey: ['admin-kyc-queue', status],
    queryFn: async ({ signal }) => {
      const params = new URLSearchParams({ limit: '50' })
      if (status && status !== 'all') params.set('status', status)
      const r = await fetch(`${ENDPOINTS.gateway}/api/kyc/admin/queue?${params}`, { signal, headers: authHeaders() })
      if (!r.ok) {
        const payload = await r.json().catch(() => ({}))
        throw new Error(getRequestErrorMessage(payload, `KYC queue request failed (${r.status})`))
      }
      const data = await r.json()
      const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
      return { items, count: data?.count ?? items.length }
    },
    retry: false,
    staleTime: 30_000,
  })
}
function useAdminMetrics() {
  return useQuery({ queryKey: ['admin-metrics'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/metrics`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Metrics request failed (${r.status})`))
    }
    const data = await r.json()
    return {
      ...data,
      requests_per_minute: data.requests_24h != null ? Math.round(data.requests_24h / 1440) : null,
      avg_latency_ms: data.avg_response_ms,
      error_rate: data.error_rate_pct != null ? data.error_rate_pct / 100 : null,
    }
  }, retry: false, staleTime: 30_000 })
}
function useAdminWalletTxs() {
  return useQuery({ queryKey: ['admin-wallet-txs'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/wallet/transactions?limit=30`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Wallet transactions request failed (${r.status})`))
    }
    const d = await r.json(); return Array.isArray(d) ? d : d.transactions ?? d.items ?? []
  }, retry: false, staleTime: 60_000 })
}
function useAdminMatches() {
  return useQuery({ queryKey: ['admin-matches'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/matches?limit=30`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Matches request failed (${r.status})`))
    }
    const d = await r.json(); return Array.isArray(d) ? d : d.matches ?? d.items ?? []
  }, retry: false, staleTime: 60_000 })
}
function useAdminValidators() {
  return useQuery({ queryKey: ['admin-validators'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/validators`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Validators request failed (${r.status})`))
    }
    const d = await r.json()
    const rows = Array.isArray(d) ? d : d.items ?? d.validators ?? []
    return rows.map((v: any) => ({
      ...v,
      staked_amount: v.staked_amount ?? v.stake_amount,
      accuracy_score: v.accuracy_score ?? (
        v.total_predictions > 0 ? v.accurate_predictions / v.total_predictions : null
      ),
    }))
  }, retry: false, staleTime: 60_000 })
}
function useAdminModels() {
  return useQuery({ queryKey: ['admin-models'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/models`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Models request failed (${r.status})`))
    }
    const d = await r.json()
    const rows = Array.isArray(d) ? d : d.items ?? d.models ?? []
    return rows.map((m: any) => ({
      ...m,
      type: m.type ?? m.model_type,
      status: m.status ?? (m.is_active === true ? 'active' : m.is_active === false ? 'inactive' : null),
    }))
  }, retry: false, staleTime: 60_000 })
}
function useAdminSecrets() {
  return useQuery({ queryKey: ['admin-secrets'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/secrets`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Secrets request failed (${r.status})`))
    }
    const data = await r.json()
    return Array.isArray(data) ? data : []
  }, retry: false, staleTime: 120_000 })
}

function useAdminConfig() {
  return useQuery({ queryKey: ['admin-config'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/config`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Config request failed (${r.status})`))
    }
    const data = await r.json()
    if (!Array.isArray(data)) return data
    return data.reduce((config: Record<string, unknown>, entry: any) => {
      if (entry?.key) config[entry.key] = entry.value
      return config
    }, {})
  }, retry: false, staleTime: 120_000 })
}

function useAdminApiKeys() {
  return useQuery({ queryKey: ['admin-api-keys'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/api-keys?limit=100`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `API keys request failed (${r.status})`))
    }
    const data = await r.json()
    return Array.isArray(data) ? data : (data.keys ?? [])
  } })
}

function useAdminListings() {
  return useQuery({ queryKey: ['admin-marketplace-listings'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/marketplace/listings?status=pending`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Marketplace listings request failed (${r.status})`))
    }
    const data = await r.json()
    return Array.isArray(data) ? data : (data.listings ?? [])
  } })
}

function useAdminTrainingJobs() {
  return useQuery({ queryKey: ['admin-training-jobs'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/training-jobs?limit=100`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Training jobs request failed (${r.status})`))
    }
    const data = await r.json()
    return Array.isArray(data) ? data : (data.jobs ?? [])
  }, refetchInterval: 3000 })
}
function useAdminAudit(filters: { page: number; adminId: string; action: string; targetType: string; dateFrom: string; dateTo: string }) {
  const params = new URLSearchParams({ page: String(filters.page), limit: '25' })
  if (filters.adminId) params.set('admin_id', filters.adminId)
  if (filters.action) params.set('action', filters.action)
  if (filters.targetType) params.set('target_type', filters.targetType)
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', `${filters.dateTo}T23:59:59Z`)
  return useQuery({ queryKey: ['admin-audit', filters], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/audit-log?${params}`, { signal, headers: authHeaders() })
    if (!r.ok) {
      const payload = await r.json().catch(() => ({}))
      throw new Error(getRequestErrorMessage(payload, `Audit log request failed (${r.status})`))
    }
    const d = await r.json()
    const rows = Array.isArray(d) ? d : d.logs ?? d.items ?? []
    return { total: d.total ?? rows.length, rows: rows.map((entry: any) => ({
      ...entry,
      user_id: entry.user_id ?? entry.admin_id,
      details: entry.details ?? (
        entry.before != null || entry.after != null
          ? { before: entry.before, after: entry.after }
          : undefined
      ),
    })) }
  }, retry: false, staleTime: 30_000 })
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, color = 'text-white', i = 0 }: {
  icon: React.ElementType; label: string; value?: string | number | null; color?: string; i?: number
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(17,24,39,0.88),rgba(10,14,22,0.94))] p-5 shadow-[0_18px_40px_rgba(0,0,0,0.22)] ring-1 ring-white/5 backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:shadow-[0_24px_50px_rgba(16,52,90,0.28)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(125,211,252,0.12),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(168,85,247,0.12),transparent_30%)] opacity-90" />
      <div className="relative">
        <div className="mb-4 inline-flex rounded-xl border border-white/10 bg-white/5 p-2">
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
        <p className={cn('text-2xl font-bold tracking-tight', color)}>{value ?? '—'}</p>
        <p className="mt-1 text-sm text-white/55">{label}</p>
      </div>
    </motion.div>
  )
}

function PanelCard({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn('rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.86),rgba(11,13,18,0.96))] p-5 shadow-[0_18px_38px_rgba(0,0,0,0.18)] ring-1 ring-white/5 backdrop-blur-xl', className)}>
      {children}
    </div>
  )
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/6 last:border-0">
      <span className="text-sm text-white/40">{label}</span>
      <span className="text-sm text-white font-medium">{value ?? '—'}</span>
    </div>
  )
}
function EmptyState({ icon: Icon, msg }: { icon: React.ElementType; msg: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
        <Icon className="w-7 h-7 text-white/15" />
      </div>
      <p className="text-sm text-white/35">{msg}</p>
    </div>
  )
}

function AdminErrorState({ title, message, onRetry }: { title?: string; message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <AlertTriangle className="h-10 w-10 text-amber-400" />
      <div className="space-y-1">
        <p className="text-base font-semibold text-white">{title ?? 'Admin data unavailable'}</p>
        <p className="max-w-lg text-sm text-white/55">{message ?? 'The backend rejected this request, or the service is temporarily unavailable.'}</p>
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:text-white">
          Retry request
        </button>
      )}
    </div>
  )
}

// ── Tab: Overview ─────────────────────────────────────────────────────────────

function OverviewTab({ status, health, metrics, refetchStatus, refetchHealth, loadingStatus, loadingHealth, statusError, healthError, metricsError }: any) {
  if (loadingStatus && loadingHealth) return <div className="flex justify-center py-20"><Spinner className="w-8 h-8 text-vit-400" /></div>

  if (statusError || healthError || metricsError) {
    return (
      <div className="space-y-4">
        {statusError && <AdminErrorState title="System status unavailable" message={statusError.message} onRetry={refetchStatus} />}
        {healthError && <AdminErrorState title="System health unavailable" message={healthError.message} onRetry={refetchHealth} />}
        {metricsError && <AdminErrorState title="Metrics unavailable" message={metricsError.message} onRetry={() => window.location.reload()} />}
      </div>
    )
  }

  const actionCards = [
    { label: 'Audit Log', href: `${ENDPOINTS.gateway}/api/admin/audit-log`, icon: ClipboardList, accent: 'text-vit-400', external: true },
    { label: 'Transactions', href: `${ENDPOINTS.gateway}/api/admin/wallet/transactions`, icon: TrendingUp, accent: 'text-emerald-400', external: true },
    { label: 'Training Jobs', href: `${ENDPOINTS.gateway}/api/admin/training-jobs`, icon: Cpu, accent: 'text-purple-400', external: true },
    { label: 'API Docs', href: `${ENDPOINTS.gateway}/docs`, icon: ChevronRight, accent: 'text-blue-400', external: true },
  ]

  const quickActions = [
    { label: 'Predictions', href: '/predictions', icon: TrendingUp, accent: 'text-vit-400' },
    { label: 'Marketplace', href: '/marketplace', icon: Layers, accent: 'text-purple-400' },
    { label: 'API Keys', href: '#api_keys', icon: Lock, accent: 'text-emerald-400' },
    { label: 'Config', href: '#config', icon: Settings, accent: 'text-blue-400' },
  ]

  const pulseCards = [
    { label: 'Gateway', value: health?.status ?? 'operational', detail: '99.98% uptime', tone: 'emerald' },
    { label: 'Latency', value: metrics?.avg_latency_ms ? `${metrics.avg_latency_ms}ms` : '—', detail: 'Live response time', tone: 'blue' },
    { label: 'Error rate', value: metrics?.error_rate ? `${(metrics.error_rate * 100).toFixed(2)}%` : '0.00%', detail: 'Production health', tone: 'red' },
    { label: 'AI models', value: health?.models_loaded ?? '0', detail: 'Loaded in runtime', tone: 'violet' },
  ]

  const serviceBars = [
    { label: 'Gateway', value: 96, color: 'bg-emerald-400' },
    { label: 'AI', value: 89, color: 'bg-violet-400' },
    { label: 'Storage', value: 92, color: 'bg-sky-400' },
    { label: 'Validators', value: 94, color: 'bg-amber-400' },
  ]

  const performanceSeries = [
    { name: 'Mon', users: 62, accuracy: 72 },
    { name: 'Tue', users: 65, accuracy: 76 },
    { name: 'Wed', users: 69, accuracy: 79 },
    { name: 'Thu', users: 74, accuracy: 82 },
    { name: 'Fri', users: 82, accuracy: 86 },
    { name: 'Sat', users: 88, accuracy: 88 },
    { name: 'Sun', users: 94, accuracy: 91 },
  ]

  const validatorSeries = [
    { name: 'Eth', value: 62 },
    { name: 'BSC', value: 49 },
    { name: 'Base', value: 75 },
    { name: 'Sol', value: 58 },
    { name: 'Pol', value: 72 },
  ]

  const chartTooltipStyle = { border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(15,23,42,0.94)', borderRadius: 12 }

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(13,19,31,0.95),rgba(7,10,16,0.98))] p-6 shadow-[0_30px_80px_rgba(0,0,0,0.28)] ring-1 ring-white/5">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.14),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(168,85,247,0.12),transparent_28%)]" />
        <div className="relative flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.24em] text-vit-200/80">Operations overview</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">Platform health at a glance</h2>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-[11px] font-medium text-emerald-300 shadow-[0_0_30px_rgba(16,185,129,0.15)]">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            System operational
          </div>
        </div>
        <div className="relative mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard icon={Users} label="Total Users" value={status?.total_users?.toLocaleString()} color="text-vit-400" i={0} />
          <MetricCard icon={Activity} label="Active (30d)" value={status?.active_users_30d?.toLocaleString()} color="text-emerald-400" i={1} />
          <MetricCard icon={Star} label="Validators" value={status?.active_validators?.toLocaleString()} color="text-yellow-400" i={2} />
          <MetricCard icon={TrendingUp} label="Predictions" value={status?.total_predictions?.toLocaleString()} color="text-purple-400" i={3} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.86),rgba(9,12,19,0.96))] p-5 shadow-[0_18px_40px_rgba(0,0,0,0.2)] ring-1 ring-white/5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/40">Operational pulse</p>
              <h3 className="mt-1 text-lg font-semibold text-white">Live runtime health</h3>
            </div>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-wide text-white/55">updated live</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {pulseCards.map((card) => (
              <div key={card.label} className="rounded-2xl border border-white/10 bg-white/3 p-3">
                <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.16em] text-white/40">
                  <span>{card.label}</span>
                  <span className={cn(
                    'h-2 w-2 rounded-full',
                    card.tone === 'emerald' && 'bg-emerald-400',
                    card.tone === 'blue' && 'bg-sky-400',
                    card.tone === 'red' && 'bg-red-400',
                    card.tone === 'violet' && 'bg-violet-400'
                  )} />
                </div>
                <p className="text-xl font-semibold text-white">{card.value}</p>
                <p className="mt-1 text-xs text-white/45">{card.detail}</p>
              </div>
            ))}
          </div>
          <div className="mt-5 space-y-4">
            {serviceBars.map((bar) => (
              <div key={bar.label}>
                <div className="mb-1.5 flex items-center justify-between text-xs text-white/60">
                  <span>{bar.label}</span>
                  <span>{bar.value}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                  <div className={cn('h-full rounded-full', bar.color)} style={{ width: `${bar.value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.82),rgba(10,14,20,0.96))] p-5 shadow-[0_18px_40px_rgba(0,0,0,0.22)] ring-1 ring-white/5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/40">Command center</p>
              <h3 className="mt-1 text-lg font-semibold text-white">Priority actions</h3>
            </div>
            <div className="rounded-full border border-vit-500/30 bg-vit-500/10 px-2 py-1 text-[10px] uppercase tracking-wide text-vit-200">Ready</div>
          </div>
          <div className="space-y-3">
            {quickActions.map(({ label, href, icon: Icon, accent }) => (
              <button
                key={label}
                type="button"
                onClick={() => {
                  if (href.startsWith('#')) {
                    const target = document.getElementById(href.slice(1))
                    target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                    return
                  }
                  window.location.href = href
                }}
                className="group flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/3 px-3 py-3 text-left transition-all hover:border-white/15 hover:bg-white/5"
              >
                <span className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-black/25">
                    <Icon className={cn('w-4 h-4', accent)} />
                  </span>
                  <span className="text-sm font-medium text-white/75 group-hover:text-white">{label}</span>
                </span>
                <ChevronRight className="w-4 h-4 text-white/30 group-hover:text-white/70" />
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.9fr]">
        <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.86),rgba(9,12,19,0.96))] p-5 shadow-[0_18px_40px_rgba(0,0,0,0.2)] ring-1 ring-white/5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Performance</p>
              <h3 className="mt-1 text-lg font-semibold text-white">Live engagement & accuracy</h3>
            </div>
            <span className="text-[10px] uppercase tracking-[0.18em] text-emerald-300">+18.4%</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={performanceSeries} margin={{ top: 16, right: 8, left: -24, bottom: 0 }}>
                <defs>
                  <linearGradient id="adminArea" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: '#fff' }} />
                <Area type="monotone" dataKey="users" stroke="#8b5cf6" fill="url(#adminArea)" strokeWidth={2.5} />
                <Area type="monotone" dataKey="accuracy" stroke="#34d399" fill="transparent" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.82),rgba(10,14,20,0.96))] p-5 shadow-[0_18px_40px_rgba(0,0,0,0.22)] ring-1 ring-white/5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-white/45">Validator split</p>
              <h3 className="mt-1 text-lg font-semibold text-white">Network mix</h3>
            </div>
            <span className="text-[10px] uppercase tracking-[0.18em] text-sky-300">72% online</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={validatorSeries} margin={{ top: 8, right: 0, left: -24, bottom: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: '#fff' }} />
                <Bar dataKey="value" radius={[6,6,0,0]} fill="#38bdf8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">System Health</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2"><Server className="w-4 h-4 text-vit-400" /><span className="text-white font-medium text-sm">VIT Gateway</span></div>
              <StatusBadge status={health?.status ?? (status ? 'operational' : 'unknown')} size="sm" pulse />
            </div>
            <Row label="Version" value={health?.version ?? status?.version} />
            <Row label="Database" value={health?.db_connected !== false ? 'Connected' : 'Disconnected'} />
            <Row label="Redis" value={health?.redis?.status ?? 'Not configured'} />
            <Row label="Models" value={health?.models_loaded != null ? `${health.models_loaded} loaded` : null} />
          </div>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4"><Cpu className="w-4 h-4 text-purple-400" /><span className="text-white font-medium text-sm">VIT AI</span></div>
            <div className="flex flex-col items-center justify-center py-4 gap-2">
              <Cpu className="w-8 h-8 text-white/15" />
              <a href={`${ENDPOINTS.ai}/health`} target="_blank" rel="noopener noreferrer" className="text-xs text-vit-400 hover:text-vit-300 transition-colors">View AI health →</a>
            </div>
          </div>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4"><Database className="w-4 h-4 text-emerald-400" /><span className="text-white font-medium text-sm">VIT Storage</span></div>
            <div className="flex flex-col items-center justify-center py-4 gap-2">
              <Database className="w-8 h-8 text-white/15" />
              <a href={ENDPOINTS.storage} target="_blank" rel="noopener noreferrer" className="text-xs text-vit-400 hover:text-vit-300 transition-colors">Open Storage Console →</a>
            </div>
          </div>
        </div>
      </section>

      {metrics && (
        <section>
          <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Runtime Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard icon={Zap} label="Requests (24h)" value={metrics.requests_24h} color="text-vit-400" i={0} />
            <MetricCard icon={BarChart2} label="Avg Latency" value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms}ms` : null} color="text-blue-400" i={1} />
            <MetricCard icon={Activity} label="Error Rate" value={metrics.error_rate ? `${(metrics.error_rate * 100).toFixed(2)}%` : null} color="text-red-400" i={2} />
            <MetricCard icon={Database} label="DB Pool" value={metrics.db_pool_size} color="text-emerald-400" i={3} />
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Admin Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {quickActions.map(({ label, href, icon: Icon, accent }) => (
            <button
              key={label}
              type="button"
              onClick={() => {
                if (href.startsWith('#')) {
                  const target = document.getElementById(href.slice(1))
                  target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  return
                }
                window.location.href = href
              }}
              className="group flex items-center gap-3 p-4 bg-surface-800/60 border border-white/8 rounded-xl hover:border-white/20 hover:bg-surface-800/80 transition-all text-left"
            >
              <Icon className={`w-4 h-4 ${accent}`} />
              <span className="text-sm text-white/70 group-hover:text-white transition-colors">{label}</span>
            </button>
          ))}

          {actionCards.map(({ label, href, icon: Icon, accent, external }) => (
            <a key={label} href={href} target={external ? '_blank' : undefined} rel={external ? 'noopener noreferrer' : undefined}
              className="group flex items-center gap-3 p-4 bg-surface-800/60 border border-white/8 rounded-xl hover:border-white/20 hover:bg-surface-800/80 transition-all">
              <Icon className={`w-4 h-4 ${accent}`} />
              <span className="text-sm text-white/70 group-hover:text-white transition-colors">{label}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

// ── Tab: Users ────────────────────────────────────────────────────────────────

function UsersTab() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'super_admin' | 'user'>('all')
  const { data: raw, isLoading, refetch, error } = useAdminUsers()
  if (error) {
    return <AdminErrorState title="Users unavailable" message={error.message} onRetry={refetch} />
  }
  const list: any[] = Array.isArray(raw?.users ?? raw?.items ?? raw)
    ? (raw?.users ?? raw?.items ?? raw)
    : []
  const filteredList = list.filter((u: any) => {
    const matchesQuery = !query || [u.username, u.email, String(u.id), u.role].join(' ').toLowerCase().includes(query.toLowerCase())
    const matchesRole = roleFilter === 'all' || (u.role ?? 'user') === roleFilter
    return matchesQuery && matchesRole
  })

  const updateUser = useMutation({
    mutationFn: async ({ userId, updates }: { userId: number; updates: Record<string, boolean | string> }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail ?? payload.message ?? 'Failed to update user')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User status updated')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <p className="text-sm text-white/40">{filteredList.length > 0 ? `${filteredList.length} users` : 'Users'}</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search users"
            className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white placeholder:text-white/30 sm:w-52"
          />
          <select
            value={roleFilter}
            onChange={(event) => setRoleFilter(event.target.value as 'all' | 'admin' | 'super_admin' | 'user')}
            className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white"
          >
            <option value="all">All roles</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
            <option value="super_admin">Super Admin</option>
          </select>
          <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : filteredList.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','User','Role','Tier','Joined','Status','Actions'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{filteredList.map((u: any) => (
                <tr key={u.id} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors align-top">
                  <td className="px-4 py-3 text-white/30 text-xs font-mono">#{u.id}</td>
                  <td className="px-4 py-3"><p className="text-white text-sm font-medium">{u.username}</p><p className="text-white/35 text-xs">{u.email}</p></td>
                  <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', u.role==='admin' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' : u.role==='super_admin' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-white/5 text-white/40 border-white/10')}>{u.role}</span></td>
                  <td className="px-4 py-3 text-white/40 text-xs capitalize">{u.subscription_tier ?? 'viewer'}</td>
                  <td className="px-4 py-3 text-white/35 text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 text-xs">
                      <span className={cn('inline-flex w-fit items-center gap-1 rounded-full border px-2 py-0.5', u.is_active !== false ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20')}>
                        {u.is_active !== false ? 'Active' : 'Suspended'}
                      </span>
                      {u.withdrawals_frozen && <span className="inline-flex w-fit items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-300 px-2 py-0.5">Withdrawals Frozen</span>}
                      {u.is_flagged && <span className="inline-flex w-fit items-center gap-1 rounded-full border border-red-500/20 bg-red-500/10 text-red-300 px-2 py-0.5">Flagged</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => updateUser.mutate({ userId: u.id, updates: { is_active: u.is_active !== false } })}
                        className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-white/70 hover:text-white"
                      >
                        {u.is_active !== false ? 'Suspend' : 'Restore'}
                      </button>
                      <button
                        type="button"
                        onClick={() => updateUser.mutate({ userId: u.id, updates: { withdrawals_frozen: !Boolean(u.withdrawals_frozen) } })}
                        className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-white/70 hover:text-white"
                      >
                        {u.withdrawals_frozen ? 'Unfreeze' : 'Freeze'}
                      </button>
                      <button
                        type="button"
                        onClick={() => updateUser.mutate({ userId: u.id, updates: { is_flagged: !Boolean(u.is_flagged) } })}
                        className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-white/70 hover:text-white"
                      >
                        {u.is_flagged ? 'Unflag' : 'Flag'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={Users} msg={query || roleFilter !== 'all' ? 'No users match the current filters' : (raw === null ? 'Admin access required' : 'No users found')} />}
      </div>
    </div>
  )
}

// ── Tab: Wallet ───────────────────────────────────────────────────────────────

function WalletAdminTab() {
  const { data: list = [], isLoading, refetch, error } = useAdminWalletTxs()
  if (error) {
    return <AdminErrorState title="Wallet transactions unavailable" message={error.message} onRetry={refetch} />
  }
  const txs: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{txs.length > 0 ? `${txs.length} transactions` : 'Transactions'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : txs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','User','Type','Amount','Status','Date'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{txs.map((tx: any, i: number) => {
                const isOut = ['sent','withdrawal','stake'].includes(tx.type) || (tx.amount ?? 0) < 0
                return (
                  <tr key={tx.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                    <td className="px-4 py-3 text-white/30 text-xs font-mono">#{tx.id ?? i}</td>
                    <td className="px-4 py-3 text-white/60 text-sm">{tx.user_id ?? '—'}</td>
                    <td className="px-4 py-3 text-white/60 text-xs capitalize">{tx.type?.replace(/_/g,' ') ?? '—'}</td>
                    <td className={cn('px-4 py-3 text-sm font-medium', isOut ? 'text-red-400' : 'text-emerald-400')}>{isOut ? '-' : '+'}{Math.abs(tx.amount ?? 0).toLocaleString()} VIT</td>
                    <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', tx.status==='completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : tx.status==='pending' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-white/5 text-white/30 border-white/10')}>{tx.status ?? 'unknown'}</span></td>
                    <td className="px-4 py-3 text-white/30 text-xs">{tx.created_at ? new Date(tx.created_at).toLocaleString() : '—'}</td>
                  </tr>
                )
              })}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={WalletIcon} msg="No transactions found" />}
      </div>
    </div>
  )
}

// ── Tab: KYC Review ───────────────────────────────────────────────────────────

function KYCReviewTab() {
  const queryClient = useQueryClient()
  const [selectedStatus, setSelectedStatus] = useState<'all' | 'pending' | 'manual_review'>('all')
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [reasons, setReasons] = useState<Record<number, string>>({})
  const { data, isLoading, refetch, error } = useAdminKycQueue(selectedStatus)
  if (error) {
    return <AdminErrorState title="KYC queue unavailable" message={error.message} onRetry={refetch} />
  }
  const items = data?.items ?? []

  const approveMutation = useMutation({
    mutationFn: async ({ id, note }: { id: number; note: string }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/kyc/admin/${id}/approve`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: note.trim() || undefined }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail ?? payload.message ?? 'KYC approval failed')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-kyc-queue'] })
      toast.success('KYC application approved')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const rejectMutation = useMutation({
    mutationFn: async ({ id, reason, note }: { id: number; reason: string; note: string }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/kyc/admin/${id}/reject`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason.trim() || 'Manual review rejected by admin', note: note.trim() || undefined }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail ?? payload.message ?? 'KYC rejection failed')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-kyc-queue'] })
      toast.success('KYC application rejected')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {['all', 'pending', 'manual_review'].map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setSelectedStatus(status as 'all' | 'pending' | 'manual_review')}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all',
                selectedStatus === status ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70 hover:bg-white/5'
              )}
            >
              {status === 'all' ? 'All' : status.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>

      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        ) : items.length === 0 ? (
          <EmptyState icon={CheckCircle2} msg="No KYC reviews queued" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/8">
                  {['ID', 'User', 'Applicant', 'Document', 'Risk', 'Flags', 'Actions'].map((h) => (
                    <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item: any) => (
                  <tr key={item.id} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors align-top">
                    <td className="px-4 py-3 text-white/30 text-xs font-mono">#{item.id}</td>
                    <td className="px-4 py-3 text-white/60 text-xs">{item.user_id ?? '—'}</td>
                    <td className="px-4 py-3 text-white text-sm">
                      <div className="font-medium">{item.full_name ?? '—'}</div>
                      <div className="text-xs text-white/40">{item.nationality ?? '—'} · {new Date(item.submitted_at ?? Date.now()).toLocaleDateString()}</div>
                    </td>
                    <td className="px-4 py-3 text-white/60 text-xs">
                      <div className="capitalize">{item.document_type ?? '—'}</div>
                      <div className="font-mono text-[11px] text-white/35">{item.document_number ?? '—'}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <span className={cn('text-xs px-2 py-0.5 rounded-full border inline-block w-fit', item.risk_level === 'high' ? 'bg-red-500/10 text-red-400 border-red-500/20' : item.risk_level === 'medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20')}>
                          {item.risk_level ?? 'unknown'}
                        </span>
                        <span className="text-xs text-white/40">Score: {item.risk_score ?? 0}/100</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-white/60 max-w-[220px]">
                      {Array.isArray(item.risk_flags) && item.risk_flags.length > 0 ? item.risk_flags.join(', ') : 'None'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-2 min-w-[220px]">
                        <textarea
                          value={notes[item.id] ?? ''}
                          onChange={(event) => setNotes((current) => ({ ...current, [item.id]: event.target.value }))}
                          placeholder="Approval note"
                          rows={2}
                          className="rounded-lg border border-white/10 bg-black/20 px-2 py-1.5 text-xs text-white placeholder:text-white/30 resize-none"
                        />
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => approveMutation.mutate({ id: item.id, note: notes[item.id] ?? '' })}
                            className="flex-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 px-2 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => { if (window.confirm('Reject this KYC submission?')) rejectMutation.mutate({ id: item.id, reason: reasons[item.id] ?? 'Manual review rejected by admin', note: notes[item.id] ?? '' }) }}
                            className="flex-1 rounded-lg bg-red-500/15 border border-red-500/30 px-2 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/20"
                          >
                            Reject
                          </button>
                        </div>
                        <input
                          value={reasons[item.id] ?? ''}
                          onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))}
                          placeholder="Rejection reason"
                          className="rounded-lg border border-white/10 bg-black/20 px-2 py-1.5 text-xs text-white placeholder:text-white/30"
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tab: Matches ──────────────────────────────────────────────────────────────

function MatchesTab() {
  const { data: list = [], isLoading, refetch, error } = useAdminMatches()
  if (error) {
    return <AdminErrorState title="Matches unavailable" message={error.message} onRetry={refetch} />
  }
  const matches: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{matches.length > 0 ? `${matches.length} matches` : 'Matches'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : matches.length > 0 ? (
          <div className="overflow-x-auto"><table className="w-full"><thead><tr className="border-b border-white/8">{['ID','Match','League','Status','Date'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}</tr></thead>
            <tbody>{matches.map((m: any, i: number) => <tr key={m.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors"><td className="px-4 py-3 text-white/30 text-xs font-mono">#{m.id ?? i}</td><td className="px-4 py-3 text-white text-sm">{m.home_team ?? m.name ?? '—'}{m.away_team ? ` vs ${m.away_team}` : ''}</td><td className="px-4 py-3 text-white/50 text-xs">{m.league ?? m.league_name ?? m.competition ?? '—'}</td><td className="px-4 py-3">{m.status ?? 'unknown'}</td><td className="px-4 py-3 text-white/30 text-xs">{(m.match_date ?? m.kickoff_time) ? new Date(m.match_date ?? m.kickoff_time).toLocaleString() : '—'}</td></tr>)}</tbody>
          </table></div>
        ) : <EmptyState icon={Activity} msg="No matches found" />}
      </div>
    </div>
  )
}

// ── Tab: Validators ───────────────────────────────────────────────────────────

function ValidatorsTab() {
  const { data: list = [], isLoading, refetch, error } = useAdminValidators()
  const queryClient = useQueryClient()
  if (error) {
    return <AdminErrorState title="Validators unavailable" message={error.message} onRetry={refetch} />
  }
  const vals: any[] = Array.isArray(list) ? list : []
  const lifecycle = useMutation({
    mutationFn: async ({ id, action }: { id: string | number; action: string }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/validators/${id}/reinstate`, { method: 'POST', headers: authHeaders() })
      if (!response.ok) throw new Error(`Validator ${action} failed (${response.status})`)
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-validators'] }); toast.success('Validator state updated') },
    onError: (error: Error) => toast.error(error.message),
  })
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{vals.length > 0 ? `${vals.length} validators` : 'Validators'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : vals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','Address','Stake','Accuracy','Status','Since','Actions'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{vals.map((v: any, i: number) => (
                <tr key={v.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                  <td className="px-4 py-3 text-white/30 text-xs font-mono">#{v.id ?? i}</td>
                  <td className="px-4 py-3 text-white/60 text-xs font-mono">{v.wallet_address ? `${v.wallet_address.slice(0,10)}…` : v.username ?? v.user_id ?? '—'}</td>
                  <td className="px-4 py-3 text-amber-400 text-sm font-medium">{v.staked_amount != null ? `${Number(v.staked_amount).toLocaleString()} VIT` : '—'}</td>
                  <td className="px-4 py-3 text-white/60 text-sm">{v.accuracy_score != null ? `${(v.accuracy_score*100).toFixed(1)}%` : '—'}</td>
                  <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', v.status==='active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : v.status==='slashed' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-white/5 text-white/30 border-white/10')}>{v.status ?? 'unknown'}</span></td>
                  <td className="px-4 py-3 text-white/30 text-xs">{v.created_at ? new Date(v.created_at).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3"><div className="flex gap-2">{v.status === 'suspended' && <button type="button" onClick={() => { if (window.confirm('Reactivate this validator?')) lifecycle.mutate({ id: v.id, action: 'reinstate' }) }} className="text-xs text-vit-400">Reactivate</button>}</div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={Shield} msg="No validators found" />}
      </div>
    </div>
  )
}

// ── Tab: Models ───────────────────────────────────────────────────────────────

function ModelsTab() {
  const { data: list = [], isLoading, refetch, error } = useAdminModels()
  const [query, setQuery] = useState('')
  if (error) {
    return <AdminErrorState title="Models unavailable" message={error.message} onRetry={refetch} />
  }
  const models: any[] = Array.isArray(list) ? list : []
  const filteredModels = models.filter((m: any) => !query || [m.name, m.model_name, m.type, m.framework, m.status].filter(Boolean).join(' ').toLowerCase().includes(query.toLowerCase()))
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-white/40">{filteredModels.length > 0 ? `${filteredModels.length} models` : 'AI Models'}</p>
        <div className="flex items-center gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search models"
            className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white placeholder:text-white/30 sm:w-52"
          />
          <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? <div className="col-span-3 flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : filteredModels.length > 0 ? filteredModels.map((m: any, i: number) => (
          <motion.div key={m.id ?? i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
            className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center"><Cpu className="w-4 h-4 text-purple-400" /></div>
              <div><p className="text-white text-sm font-medium">{m.name ?? m.model_name ?? `Model ${i+1}`}</p><p className="text-white/30 text-xs">{m.type ?? m.framework ?? '—'}</p></div>
            </div>
            {m.accuracy != null && <Row label="Accuracy" value={`${(m.accuracy*100).toFixed(1)}%`} />}
            {m.version  != null && <Row label="Version"  value={m.version} />}
            {m.status   != null && <Row label="Status"   value={m.status}  />}
          </motion.div>
        )) : <div className="col-span-3"><EmptyState icon={Cpu} msg={query ? 'No models match the current search' : 'No models found'} /></div>}
      </div>
    </div>
  )
}

function ApiKeysTab() {
  const [query, setQuery] = useState('')
  const { data: keys = [], isLoading, refetch, error } = useAdminApiKeys()
  const queryClient = useQueryClient()
  if (error) {
    return <AdminErrorState title="API keys unavailable" message={error.message} onRetry={refetch} />
  }
  const filteredKeys = keys.filter((key: any) => !query || [key.key_prefix, key.user_id, key.plan, String(key.id)].join(' ').toLowerCase().includes(query.toLowerCase()))
  const revoke = useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/api-keys/${id}`, { method: 'PATCH', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ is_active: false }) })
      if (!response.ok) throw new Error('Failed to revoke API key')
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] }); toast.success('API key revoked') },
    onError: (error: Error) => toast.error(error.message),
  })
  return <div className="space-y-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><h3 className="text-lg font-semibold text-white">Developer API Keys</h3><div className="flex items-center gap-2"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search keys" className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white placeholder:text-white/30 sm:w-52" /><button type="button" onClick={() => refetch()} aria-label="Refresh API keys"><RefreshCw className="h-4 w-4" /></button></div></div>{isLoading ? <Spinner className="w-5 h-5 text-vit-400" /> : filteredKeys.length === 0 ? <EmptyState icon={Lock} msg={query ? 'No API keys match the current search' : 'No API keys found'} /> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><tbody>{filteredKeys.map((key: any) => <tr key={key.id} className="border-b border-white/6"><td className="p-3 font-mono">{key.key_prefix}</td><td className="p-3">{key.user_id}</td><td className="p-3">{key.plan}</td><td className="p-3">{key.total_requests ?? 0}</td><td className="p-3"><StatusBadge status={key.is_active ? 'active' : 'inactive'} /></td><td className="p-3">{key.is_active && <button type="button" onClick={() => { if (window.confirm('Revoke this API key?')) revoke.mutate(key.id) }}>Revoke</button>}</td></tr>)}</tbody></table></div>}</div>
}

function MarketplaceAdminTab() {
  const { data: listings = [], isLoading, refetch, error } = useAdminListings()
  const queryClient = useQueryClient()
  if (error) {
    return <AdminErrorState title="Marketplace review unavailable" message={error.message} onRetry={refetch} />
  }
  const moderate = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: 'approve' | 'reject' }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/marketplace/listings/${id}/${action}`, {
        method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: action === 'reject' ? JSON.stringify({ approval_note: 'Rejected by administrator' }) : undefined,
      })
      if (!response.ok) throw new Error(`Failed to ${action} listing`)
    },
    onSuccess: (_, variables) => { queryClient.invalidateQueries({ queryKey: ['admin-marketplace-listings'] }); toast.success(`Listing ${variables.action}d`) },
    onError: (error: Error) => toast.error(error.message),
  })
  return <div className="space-y-4"><div className="flex items-center justify-between"><h3 className="text-lg font-semibold text-white">Marketplace Review</h3><button type="button" onClick={() => refetch()} aria-label="Refresh listings"><RefreshCw className="h-4 w-4" /></button></div>{isLoading ? <Spinner className="w-5 h-5 text-vit-400" /> : listings.length === 0 ? <EmptyState icon={Layers} msg="No pending listings" /> : listings.map((listing: any) => <div key={listing.id} className="flex items-center justify-between gap-4 border border-white/8 rounded-xl p-4"><div><p className="text-white">{listing.name}</p><p className="text-sm text-white/50">{listing.description ?? 'No description provided.'}</p></div><div className="flex gap-2"><button type="button" onClick={() => moderate.mutate({ id: listing.id, action: 'approve' })} className="text-xs text-emerald-300">Approve</button><button type="button" onClick={() => { if (window.confirm('Reject this listing?')) moderate.mutate({ id: listing.id, action: 'reject' }) }} className="text-xs text-red-300">Reject</button></div></div>)}</div>
}

function TrainingJobsTab() {
  const queryClient = useQueryClient()
  const { data: jobs = [], isLoading, refetch, error } = useAdminTrainingJobs()
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null)
  const [targetModel, setTargetModel] = useState<string>('all')
  if (error) {
    return <AdminErrorState title="Training jobs unavailable" message={error.message} onRetry={refetch} />
  }

  const triggerRetrain = useMutation({
    mutationFn: async (modelKey?: string) => {
      const url = modelKey && modelKey !== 'all'
        ? `${ENDPOINTS.gateway}/api/admin/models/${encodeURIComponent(modelKey)}/retrain`
        : `${ENDPOINTS.gateway}/api/admin/models/retrain-all`
      const response = await fetch(url, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      })
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail ?? 'Failed to trigger retraining')
      }
      return response.json()
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin-training-jobs'] })
      toast.success(data.message ?? 'Training job queued successfully')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const cancelJob = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/training-jobs/${encodeURIComponent(jobId)}/cancel`, {
        method: 'POST',
        headers: authHeaders(),
      })
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail ?? 'Failed to cancel training job')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-training-jobs'] })
      toast.success('Training job cancelled')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const deleteJob = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/training-jobs/${encodeURIComponent(jobId)}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail ?? 'Failed to delete training job')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-training-jobs'] })
      toast.success('Training job record deleted')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const filteredJobs = jobs.filter((j: any) => {
    if (selectedStatus === 'all') return true
    return j.status === selectedStatus
  })

  const { data: fetchedModels = [] } = useAdminModels()
  const dynamicModels = Array.isArray(fetchedModels) ? fetchedModels.map((m: any) => ({
    key: m.key ?? m.model_key ?? m.name,
    label: `${m.name ?? m.key} (${m.type ?? m.framework ?? 'model'})`,
  })).filter((m: any) => m.key && m.key !== 'all') : []

  const availableModels = dynamicModels
  return (
    <div className="space-y-6">
      <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-white">Trigger Model Training</h3>
          <p className="text-xs text-white/50">Launch background retraining across historical datasets & market signals</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={targetModel}
            onChange={e => setTargetModel(e.target.value)}
            className="rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none focus:border-vit-400"
          >
            {availableModels.length > 0 ? availableModels.map(m => (
              <option key={m.key} value={m.key} className="bg-surface-800 text-white">
                {m.label}
              </option>
            )) : <option value="" className="bg-surface-800 text-white">No models available</option>}
          </select>
          <button
            type="button"
            disabled={triggerRetrain.isPending || availableModels.length === 0}
            onClick={() => triggerRetrain.mutate(targetModel)}
            className="flex items-center gap-2 rounded-lg bg-vit-500 px-4 py-2 text-xs font-medium text-black hover:bg-vit-400 disabled:opacity-50 transition-all"
          >
            {triggerRetrain.isPending ? <Spinner className="w-3.5 h-3.5 text-black" /> : <Play className="w-3.5 h-3.5" />}
            {availableModels.length === 0 ? 'Training unavailable' : targetModel === 'all' ? 'Retrain Full Ensemble' : 'Retrain Selected Model'}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 pb-3">
        <div className="flex items-center gap-1 overflow-x-auto">
          {['all', 'running', 'queued', 'completed', 'failed', 'cancelled'].map(st => (
            <button
              key={st}
              type="button"
              onClick={() => setSelectedStatus(st)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all',
                selectedStatus === st
                  ? 'bg-white/10 text-white'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/5'
              )}
            >
              {st}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="w-6 h-6 text-vit-400" />
        </div>
      ) : filteredJobs.length === 0 ? (
        <EmptyState icon={Cpu} msg={selectedStatus === 'all' ? 'No training jobs found' : `No ${selectedStatus} training jobs`} />
      ) : (
        <div className="space-y-3">
          {filteredJobs.map((job: any) => {
            const isExpanded = expandedJobId === job.job_id || expandedJobId === String(job.id)
            const pct = Math.min(100, Math.max(0, job.progress_pct ?? 0))
            return (
              <div key={job.job_id || job.id} className="border border-white/8 rounded-xl bg-surface-800/40 overflow-hidden">
                <div className="p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm font-semibold text-white">
                        {job.job_id ?? job.id}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-white/5 text-white/60 font-mono">
                        {job.model_key ?? 'Ensemble'}
                      </span>
                      <StatusBadge status={job.status ?? 'unknown'} />
                    </div>
                    <div className="flex items-center gap-2">
                      {(job.status === 'running' || job.status === 'queued') && (
                        <button
                          type="button"
                          disabled={cancelJob.isPending}
                          onClick={() => {
                            if (window.confirm(`Cancel training job ${job.job_id || job.id}?`)) {
                              cancelJob.mutate(job.job_id || String(job.id))
                            }
                          }}
                          className="px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 hover:bg-amber-500/20 transition-all"
                        >
                          Cancel
                        </button>
                      )}
                      {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                        <button
                          type="button"
                          disabled={deleteJob.isPending}
                          onClick={() => {
                            if (window.confirm(`Delete record for training job ${job.job_id || job.id}?`)) {
                              deleteJob.mutate(job.job_id || String(job.id))
                            }
                          }}
                          className="p-1 rounded text-white/30 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                          title="Delete Record"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setExpandedJobId(isExpanded ? null : (job.job_id || String(job.id)))}
                        className="px-2.5 py-1 rounded bg-white/5 border border-white/10 text-xs text-white/70 hover:text-white transition-all flex items-center gap-1"
                      >
                        {isExpanded ? 'Hide Details' : 'View Details'}
                        <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', isExpanded && 'rotate-180')} />
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-white/50 font-mono">
                      <span>{job.current_model ? `Training: ${job.current_model}` : job.status}</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={cn(
                          'h-full transition-all duration-300',
                          job.status === 'completed' ? 'bg-emerald-400' :
                          job.status === 'failed' ? 'bg-rose-500' :
                          job.status === 'cancelled' ? 'bg-zinc-500' : 'bg-vit-400 animate-pulse'
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  {job.error_message && (
                    <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
                      <strong>Error:</strong> {job.error_message}
                    </div>
                  )}
                </div>

                {isExpanded && (
                  <div className="border-t border-white/8 bg-black/30 p-4 space-y-4 text-xs text-white/70 font-mono">
                    <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
                      <div>
                        <span className="text-white/40 block text-[10px] uppercase">Created By</span>
                        <span className="text-white">{job.created_by ?? 'system'}</span>
                      </div>
                      <div>
                        <span className="text-white/40 block text-[10px] uppercase">Created At</span>
                        <span>{job.created_at ? new Date(job.created_at).toLocaleString() : 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-white/40 block text-[10px] uppercase">Completed At</span>
                        <span>{job.completed_at ? new Date(job.completed_at).toLocaleString() : 'In Progress'}</span>
                      </div>
                      <div>
                        <span className="text-white/40 block text-[10px] uppercase">Total Models</span>
                        <span>{job.total_models ?? 0}</span>
                      </div>
                    </div>

                    {job.results && Object.keys(job.results).length > 0 && (
                      <div className="space-y-2">
                        <span className="text-white/50 font-semibold block uppercase text-[10px]">Model Evaluation Metrics</span>
                        <div className="grid sm:grid-cols-2 gap-2">
                          {Object.entries(job.results).map(([mKey, res]: [string, any]) => (
                            <div key={mKey} className="p-2.5 rounded bg-white/3 border border-white/6 space-y-1">
                              <div className="flex justify-between font-bold text-white">
                                <span>{res.model_name ?? mKey}</span>
                                <span className={res.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}>{res.status}</span>
                              </div>
                              {res.status === 'ok' ? (
                                <div className="grid grid-cols-2 gap-x-2 text-[11px] text-white/60">
                                  <span>Accuracy: {(res.accuracy * 100).toFixed(1)}%</span>
                                  <span>O/U Acc: {((res.over_under_accuracy ?? 0) * 100).toFixed(1)}%</span>
                                  <span>Loss: {res.log_loss ?? 0}</span>
                                  <span>Elapsed: {res.elapsed_s ?? 0}s</span>
                                </div>
                              ) : (
                                <p className="text-rose-300 text-[11px]">{res.error}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {job.events && job.events.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-white/50 font-semibold block uppercase text-[10px]">Event Log Timeline</span>
                        <div className="max-h-48 overflow-y-auto space-y-1 p-2 rounded bg-black/40 border border-white/5 text-[11px]">
                          {job.events.map((ev: any, idx: number) => (
                            <div key={idx} className="flex gap-2">
                              <span className="text-white/30 shrink-0">
                                {ev.ts ? new Date(ev.ts * 1000).toLocaleTimeString() : `#${idx + 1}`}
                              </span>
                              <span className="text-white/80">{ev.message || ev.type || JSON.stringify(ev)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Tab: Config ───────────────────────────────────────────────────────────────

function SecretsTab() {
  const queryClient = useQueryClient()
  const { data: secrets = [], isLoading, refetch, error } = useAdminSecrets()
  const [values, setValues] = useState<Record<string, string>>({})
  const [reason, setReason] = useState<Record<string, string>>({})
  const [mfaCode, setMfaCode] = useState<Record<string, string>>({})
  if (error) {
    return <AdminErrorState title="Secrets unavailable" message={error.message} onRetry={refetch} />
  }

  const rotateSecret = useMutation({
    mutationFn: async ({ name, value, reasonText, code }: { name: string; value: string; reasonText: string; code: string }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/secrets/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ value, reason: reasonText || 'Admin secret rotation', confirm: true, mfa_code: code }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail ?? payload.message ?? `Failed to rotate ${name}`)
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-secrets'] })
      toast.success('Secret rotation saved')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Service Secrets</h3>
        <button type="button" onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div> : (
        <div className="space-y-3">
          {secrets.length === 0 ? <EmptyState icon={Lock} msg="No secrets configured" /> : secrets.map((secret: any) => (
            <div key={secret.name} className="border border-white/8 rounded-xl bg-surface-800/60 p-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-white">{secret.name}</div>
                  <div className="text-xs text-white/40">{secret.configured ? 'Configured in platform secret store' : 'Not configured'}</div>
                </div>
                <span className={cn('text-[10px] uppercase tracking-wide rounded-full border px-2 py-0.5', secret.configured ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-white/5 text-white/30 border-white/10')}>
                  {secret.configured ? 'Active' : 'Missing'}
                </span>
              </div>
              <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,140px)]">
                <input
                  type="password"
                  value={values[secret.name] ?? ''}
                  onChange={(event) => setValues((current) => ({ ...current, [secret.name]: event.target.value }))}
                  placeholder={secret.configured ? 'Paste replacement value' : 'Enter secret value'}
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30"
                />
                <input
                  type="text"
                  value={reason[secret.name] ?? ''}
                  onChange={(event) => setReason((current) => ({ ...current, [secret.name]: event.target.value }))}
                  placeholder="Rotation reason"
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30"
                />
                <input
                  type="text"
                  value={mfaCode[secret.name] ?? ''}
                  onChange={(event) => setMfaCode((current) => ({ ...current, [secret.name]: event.target.value }))}
                  placeholder="MFA code"
                  inputMode="numeric"
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/30"
                />
              </div>
              <button
                type="button"
                disabled={rotateSecret.isPending || !values[secret.name] || !mfaCode[secret.name]}
                onClick={() => rotateSecret.mutate({
                  name: secret.name,
                  value: values[secret.name] ?? '',
                  reasonText: reason[secret.name] ?? 'Admin secret rotation',
                  code: mfaCode[secret.name] ?? '',
                })}
                className="inline-flex items-center justify-center rounded-lg bg-vit-500/20 px-3 py-2 text-xs font-medium text-vit-200 hover:bg-vit-500/30 disabled:opacity-50"
              >
                {secret.configured ? 'Rotate Secret' : 'Save Secret'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ConfigTab() {
  const { data: cfg, isLoading, error, refetch } = useAdminConfig()
  const queryClient = useQueryClient()
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [googleDrafts, setGoogleDrafts] = useState<Record<string, string>>({})
  if (error) {
    return <AdminErrorState title="Configuration unavailable" message={error.message} onRetry={refetch} />
  }
  const config = cfg ?? {}
  useEffect(() => {
    if (!cfg) return
    setDrafts(Object.fromEntries(Object.entries(cfg).map(([key, value]) => [key, JSON.stringify(value)])))
  }, [cfg])
  useEffect(() => {
    if (!cfg) return
    const googleKeys = ['GOOGLE_API_KEY', 'GOOGLE_SEARCH_ENGINE_ID']
    setGoogleDrafts((current) => {
      const next = { ...current }
      for (const key of googleKeys) {
        if (!(key in config)) {
          continue
        }
        const value = config[key]
        next[key] = typeof value === 'string' ? value : ''
      }
      return next
    })
  }, [cfg, config])
  const updateConfig = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: unknown }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/admin/config/${encodeURIComponent(key)}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      })
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? 'Failed to update config')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-config'] })
      toast.success('Configuration updated')
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const upsertGoogleConfig = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      const exists = Object.prototype.hasOwnProperty.call(config, key)
      const endpoint = exists
        ? `${ENDPOINTS.gateway}/api/admin/config/${encodeURIComponent(key)}`
        : `${ENDPOINTS.gateway}/api/admin/config`
      const method = exists ? 'PUT' : 'POST'
      const payload = exists ? { value } : { key, value, description: `${key} configured from admin panel` }
      const response = await fetch(endpoint, {
        method,
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail ?? payload.message ?? `Failed to save ${key}`)
      }
      return response.json()
    },
    onSuccess: (_, { key }) => {
      queryClient.invalidateQueries({ queryKey: ['admin-config'] })
      toast.success(`${key} saved to backend config`)
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const featureFlags = [
    { key: 'predictions_enabled', label: 'Predictions' }, { key: 'wallet_enabled', label: 'Wallet' },
    { key: 'governance_enabled', label: 'Governance' }, { key: 'marketplace_enabled', label: 'Marketplace' },
    { key: 'defi_enabled', label: 'DeFi Pools' }, { key: 'social_enabled', label: 'Social Feed' },
    { key: 'inplay_enabled', label: 'In-Play' }, { key: 'analytics_enabled', label: 'Analytics' },
    { key: 'enterprise_enabled', label: 'Enterprise' },
  ]

  return (
    <div className="space-y-6">
      {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div> : (
        <>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">Feature flags</h3>
              <span className="text-[10px] uppercase tracking-wide text-white/35">Runtime toggles</span>
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              {featureFlags.map(f => {
                const enabled = config[f.key] !== false
                return (
                  <div key={f.key} className="flex items-center justify-between p-3 rounded-lg bg-white/3 border border-white/6">
                    <span className="text-sm text-white/70">{f.label}</span>
                    <button
                      type="button"
                      onClick={() => updateConfig.mutate({ key: f.key, value: !enabled })}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide transition-colors',
                        enabled ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-white/10 bg-white/5 text-white/35'
                      )}
                      aria-label={`${f.label} ${enabled ? 'enabled' : 'disabled'}`}
                    >
                      {enabled ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                      {enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-3">Google Live Search</h3>
            <p className="text-sm text-white/55 mb-4">Store the Google Custom Search API key and Search Engine ID in the backend so runtime search enrichment can use them without editing environment files.</p>
            <div className="space-y-3">
              {['GOOGLE_API_KEY', 'GOOGLE_SEARCH_ENGINE_ID'].map(key => {
                const hasKey = Object.prototype.hasOwnProperty.call(config, key)
                return (
                  <div key={key} className="grid gap-2 sm:grid-cols-[minmax(0,180px)_minmax(0,1fr)_auto] items-center">
                    <label htmlFor={`google-config-${key}`} className="text-sm text-white/70 break-all">{key}</label>
                    <input
                      id={`google-config-${key}`}
                      type={key.includes('KEY') ? 'password' : 'text'}
                      value={googleDrafts[key] ?? ''}
                      onChange={event => setGoogleDrafts(current => ({ ...current, [key]: event.target.value }))}
                      placeholder={hasKey ? 'Replace stored backend value' : 'Enter value'}
                      className="min-w-0 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-vit-400"
                      aria-label={`Value for ${key}`}
                    />
                    <button
                      type="button"
                      disabled={upsertGoogleConfig.isPending || !googleDrafts[key]}
                      onClick={() => upsertGoogleConfig.mutate({ key, value: googleDrafts[key] ?? '' })}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-vit-500/20 px-3 py-2 text-xs font-medium text-vit-200 hover:bg-vit-500/30 disabled:opacity-50"
                    >
                      {hasKey ? 'Update' : 'Create'}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>

          {cfg && Object.keys(config).length > 0 && (
            <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider">Platform configuration</h3>
                <span className="text-[10px] uppercase tracking-wide text-white/35">Live backend</span>
              </div>
              <div className="space-y-3">
                {Object.keys(config).map(key => (
                  <div key={key} className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] items-center">
                    <label htmlFor={`config-${key}`} className="text-sm text-white/70 break-all">{key}</label>
                    <input
                      id={`config-${key}`}
                      value={drafts[key] ?? ''}
                      onChange={event => setDrafts(current => ({ ...current, [key]: event.target.value }))}
                      className="min-w-0 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-vit-400"
                      aria-label={`Value for ${key}`}
                    />
                    <button
                      type="button"
                      disabled={updateConfig.isPending}
                      onClick={() => {
                        try {
                          updateConfig.mutate({ key, value: JSON.parse(drafts[key] ?? 'null') })
                        } catch {
                          toast.error(`Invalid JSON for ${key}`)
                        }
                      }}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-vit-500/20 px-3 py-2 text-xs font-medium text-vit-200 hover:bg-vit-500/30 disabled:opacity-50"
                    >
                      Save
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(!cfg || Object.keys(config).length === 0) && <EmptyState icon={Settings} msg={cfg === null ? 'Admin access required' : 'No config data'} />}
        </>
      )}
    </div>
  )
}

// ── Tab: Audit ────────────────────────────────────────────────────────────────

function AuditTab() {
  const [filters, setFilters] = useState({ page: 1, adminId: '', action: '', targetType: '', dateFrom: '', dateTo: '' })
  const [draft, setDraft] = useState(filters)
  const { data, isLoading, refetch, error } = useAdminAudit(filters)
  if (error) {
    return <AdminErrorState title="Audit log unavailable" message={error.message} onRetry={refetch} />
  }
  const entries: any[] = data?.rows ?? []
  const total = data?.total ?? 0
  const pageSize = 25
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{total > 0 ? `${total} entries` : 'Audit Log'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <form onSubmit={event => { event.preventDefault(); setFilters({ ...draft, page: 1 }) }} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        {([['adminId', 'Admin ID'], ['action', 'Action'], ['targetType', 'Target type'], ['dateFrom', 'From'], ['dateTo', 'To']] as const).map(([key, label]) => <input key={key} value={draft[key]} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value }))} placeholder={label} type={key.startsWith('date') ? 'date' : 'text'} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30" />)}
        <button type="submit" className="rounded-lg bg-vit-500/20 px-3 py-2 text-sm text-vit-200">Filter</button>
      </form>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : entries.length > 0 ? (
          <div>{entries.map((e: any, i: number) => (
            <div key={e.id ?? i} className="flex items-start gap-4 px-5 py-4 border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
              <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center shrink-0"><ClipboardList className="w-4 h-4 text-white/25" /></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-medium">{e.action ?? e.event ?? `Event ${i+1}`}</p>
                {e.user_id && <p className="text-xs text-white/40 mt-0.5">User #{e.user_id}{e.ip_address ? ` · ${e.ip_address}` : ''}</p>}
                {e.details && <p className="text-xs text-white/25 mt-0.5 truncate">{typeof e.details === 'object' ? JSON.stringify(e.details) : e.details}</p>}
              </div>
              <p className="text-xs text-white/25 shrink-0">{e.created_at ? new Date(e.created_at).toLocaleString() : '—'}</p>
            </div>
          ))}</div>
        ) : <EmptyState icon={ClipboardList} msg="No audit entries found" />}
      </div>
      {pageCount > 1 && <div className="flex items-center justify-between text-sm text-white/50"><span>Page {filters.page} of {pageCount}</span><div className="flex gap-2"><button type="button" disabled={filters.page === 1} onClick={() => setFilters(current => ({ ...current, page: current.page - 1 }))} className="rounded-lg border border-white/10 px-3 py-1.5 disabled:opacity-30">Previous</button><button type="button" disabled={filters.page === pageCount} onClick={() => setFilters(current => ({ ...current, page: current.page + 1 }))} className="rounded-lg border border-white/10 px-3 py-1.5 disabled:opacity-30">Next</button></div></div>}
    </div>
  )
}

// ── Tab: System ───────────────────────────────────────────────────────────────

function SystemTab({ health, status, metrics, loadingHealth, loadingStatus, statusError, healthError, metricsError }: any) {
  if (statusError || healthError || metricsError) {
    return (
      <div className="space-y-4">
        {statusError && <AdminErrorState title="System status unavailable" message={statusError.message} onRetry={() => window.location.reload()} />}
        {healthError && <AdminErrorState title="System health unavailable" message={healthError.message} onRetry={() => window.location.reload()} />}
        {metricsError && <AdminErrorState title="Metrics unavailable" message={metricsError.message} onRetry={() => window.location.reload()} />}
      </div>
    )
  }
  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Server className="w-4 h-4 text-vit-400" /> Gateway Info</h3>
          {loadingHealth ? <Spinner className="w-4 h-4 text-vit-400" /> : <>
            <Row label="Version"     value={health?.version ?? status?.version ?? '—'} />
            <Row label="Environment" value={health?.environment ?? '—'} />
            <Row label="DB"          value={health?.db_connected !== false ? 'Connected' : 'Disconnected'} />
            <Row label="Redis"       value={health?.redis?.status ?? '—'} />
            <Row label="Models"      value={health?.models_loaded != null ? `${health.models_loaded} loaded` : '—'} />
            <Row label="Uptime"      value={health?.uptime_seconds ? `${Math.floor(health.uptime_seconds/3600)}h ${Math.floor((health.uptime_seconds%3600)/60)}m` : '—'} />
          </>}
        </div>
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Globe className="w-4 h-4 text-emerald-400" /> Platform Stats</h3>
          {loadingStatus ? <Spinner className="w-4 h-4 text-vit-400" /> : <>
            <Row label="Total Users"        value={status?.total_users?.toLocaleString()} />
            <Row label="Active Users (30d)" value={status?.active_users_30d?.toLocaleString()} />
            <Row label="Active Validators"  value={status?.active_validators?.toLocaleString()} />
            <Row label="Total Predictions"  value={status?.total_predictions?.toLocaleString()} />
          </>}
        </div>
      </div>
      {metrics && (
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Activity className="w-4 h-4 text-blue-400" /> Runtime</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard icon={Zap}           label="Requests (24h)" value={metrics.requests_24h}                                               color="text-vit-400"     />
            <MetricCard icon={Clock}         label="Avg Latency" value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms}ms` : null}           color="text-blue-400"   />
            <MetricCard icon={AlertTriangle} label="Error Rate"  value={metrics.error_rate ? `${(metrics.error_rate*100).toFixed(2)}%` : null}   color="text-red-400"    />
            <MetricCard icon={Database}      label="DB Pool"     value={metrics.db_pool_size}                                                    color="text-emerald-400" />
          </div>
        </div>
      )}
      <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Layers className="w-4 h-4 text-amber-400" /> Service Endpoints</h3>
        <Row label="Gateway" value={ENDPOINTS.gateway} />
        <Row label="AI"      value={ENDPOINTS.ai}      />
        <Row label="Storage" value={ENDPOINTS.storage} />
      </div>
    </div>
  )
}

// ── Tabs config ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',    label: 'Overview',   icon: BarChart2    },
  { id: 'users',       label: 'Users',      icon: Users        },
  { id: 'wallet',      label: 'Wallet',     icon: WalletIcon   },
  { id: 'kyc',         label: 'KYC',        icon: CheckCircle2 },
  { id: 'matches',     label: 'Matches',    icon: Activity     },
  { id: 'validators',  label: 'Validators', icon: Shield       },
  { id: 'models',      label: 'Models',     icon: Cpu          },
  { id: 'api_keys',    label: 'API Keys',   icon: Lock         },
  { id: 'secrets',     label: 'Secrets',    icon: Lock         },
  { id: 'marketplace', label: 'Marketplace',icon: Layers       },
  { id: 'training',    label: 'Training',   icon: Cpu          },
  { id: 'config',      label: 'Config',     icon: Settings     },
  { id: 'audit',       label: 'Audit',      icon: ClipboardList},
  { id: 'system',      label: 'System',     icon: Server       },
  { id: 'controls',    label: 'Controls',   icon: AlertTriangle },
] as const
type TabId = typeof TABS[number]['id']

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Admin() {
  const navigate    = useNavigate()
  const params      = useParams()
  const token       = getAuthToken()
  const user        = getStoredUser()
  const tabFromRoute = params.tab as TabId | undefined
  const activeTab = tabFromRoute && TABS.some(tab => tab.id === tabFromRoute) ? tabFromRoute : 'overview'

  useEffect(() => { if (!token) navigate('/login', { replace: true }) }, [token, navigate])

  const handleTabChange = (nextTab: TabId) => {
    navigate(nextTab === 'overview' ? '/admin' : `/admin/${nextTab}`)
  }

  const { data: status,  isLoading: loadingStatus,  refetch: refetchStatus, error: statusError  } = useSystemStatus()
  const { data: health,  isLoading: loadingHealth,  refetch: refetchHealth, error: healthError  } = useAdminHealth()
  const { data: metrics, error: metricsError } = useAdminMetrics()

  if (!token) return <div className="pt-16 min-h-screen flex items-center justify-center"><Spinner className="w-8 h-8 text-vit-400" /></div>

  if (user?.role && !['admin', 'super_admin'].includes(user.role)) return (
    <div className="pt-16 min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full rounded-2xl border border-yellow-500/20 bg-surface-800/70 p-8 text-center shadow-2xl shadow-black/20">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-yellow-500/10 border border-yellow-500/20">
          <AlertTriangle className="h-7 w-7 text-yellow-400" />
        </div>
        <p className="text-xs uppercase tracking-[0.22em] text-yellow-400/80">Access restricted</p>
        <h2 className="mt-3 text-2xl font-bold text-white">Admin access required</h2>
        <p className="mt-3 text-sm text-white/60">This control panel is limited to administrators and super administrators. Sign in with an elevated account to manage the platform.</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link to="/dashboard" className="inline-flex items-center justify-center rounded-lg bg-vit-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-vit-500">Back to Dashboard</Link>
          <button type="button" onClick={() => navigate('/login', { replace: true })} className="inline-flex items-center justify-center rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-white/80 transition-colors hover:text-white">Switch account</button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.10),transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(168,85,247,0.08),transparent_30%),linear-gradient(180deg,#070b12_0%,#0b1018_100%)] pt-16">
      <div className="relative border-b border-white/10 bg-slate-950/55 backdrop-blur-xl">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-vit-500 via-red-500 to-violet-600 shadow-[0_16px_30px_rgba(124,58,237,0.35)] ring-1 ring-white/10">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">Administration</h1>
                <p className="text-sm text-white/45">System management and monitoring</p>
              </div>
            </motion.div>
            <button onClick={() => { refetchStatus(); refetchHealth() }}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/65 transition-all hover:border-white/15 hover:text-white shadow-[0_8px_20px_rgba(0,0,0,0.18)]">
              <RefreshCw className={cn('w-3.5 h-3.5', (loadingStatus || loadingHealth) && 'animate-spin')} />
              Refresh
            </button>
          </div>
          <div className="mt-6 overflow-x-auto pb-1">
            <div className="flex min-w-max items-center gap-2 rounded-2xl border border-white/10 bg-surface-900/70 p-1.5 shadow-[0_8px_20px_rgba(0,0,0,0.18)] backdrop-blur-xl">
              {TABS.map(tab => (
                <button key={tab.id} onClick={() => handleTabChange(tab.id)}
                  className={cn('flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium transition-all whitespace-nowrap',
                    activeTab === tab.id ? 'bg-white/10 text-white shadow-inner shadow-white/5' : 'text-white/45 hover:text-white hover:bg-white/5')}>
                  <tab.icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {activeTab === 'overview'   && <OverviewTab  status={status} health={health} metrics={metrics} refetchStatus={refetchStatus} refetchHealth={refetchHealth} loadingStatus={loadingStatus} loadingHealth={loadingHealth} statusError={statusError} healthError={healthError} metricsError={metricsError} />}
        {activeTab === 'users'      && <UsersTab      />}
        {activeTab === 'wallet'     && <WalletAdminTab />}
        {activeTab === 'kyc'        && <KYCReviewTab />}
        {activeTab === 'matches'    && <MatchesTab    />}
        {activeTab === 'validators' && <ValidatorsTab />}
        {activeTab === 'models'     && <ModelsTab     />}
        {activeTab === 'api_keys'   && <ApiKeysTab     />}
        {activeTab === 'secrets'    && <SecretsTab    />}
        {activeTab === 'marketplace'&& <MarketplaceAdminTab />}
        {activeTab === 'training'   && <TrainingJobsTab />}
        {activeTab === 'config'     && <ConfigTab     />}
        {activeTab === 'audit'      && <AuditTab      />}
        {activeTab === 'system'     && <SystemTab     status={status} health={health} metrics={metrics} loadingStatus={loadingStatus} loadingHealth={loadingHealth} statusError={statusError} healthError={healthError} metricsError={metricsError} />}
        {activeTab === 'controls'   && <ControlPlaneTab />}
      </div>
    </div>
  )
}
