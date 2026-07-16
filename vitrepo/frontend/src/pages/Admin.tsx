import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Shield, Users, Activity, Database, Server,
  TrendingUp, AlertTriangle, RefreshCw, ChevronRight,
  Cpu, Zap, Star, BarChart2,
} from 'lucide-react'
import { getAuthToken, getStoredUser, authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { cn } from '@/lib/utils'

// ── Hooks ─────────────────────────────────────────────────────────────────────

function useSystemStatus() {
  return useQuery({
    queryKey: ['admin-system-status'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/status`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}

function useAdminHealth() {
  return useQuery({
    queryKey: ['admin-health'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/health`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}

function useAdminUsers() {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/admin/users?limit=10`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 60_000,
  })
}

function useAdminMetrics() {
  return useQuery({
    queryKey: ['admin-metrics'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/metrics`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 30_000,
  })
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MetricCard({
  icon: Icon, label, value, sub, color = 'text-white', i = 0,
}: {
  icon: React.ElementType; label: string; value?: string | number | null
  sub?: string; color?: string; i?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.05 }}
      className="p-5 bg-surface-800/60 border border-white/8 rounded-xl"
    >
      <Icon className={`w-4 h-4 mb-3 ${color}`} />
      <p className={cn('text-2xl font-bold', color)}>{value ?? '—'}</p>
      <p className="text-white/50 text-sm mt-0.5">{label}</p>
      {sub && <p className="text-white/25 text-xs mt-1">{sub}</p>}
    </motion.div>
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Admin() {
  const navigate = useNavigate()
  const token    = getAuthToken()
  const user     = getStoredUser()

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const { data: status,  isLoading: loadingStatus,  refetch: refetchStatus  } = useSystemStatus()
  const { data: health,  isLoading: loadingHealth,  refetch: refetchHealth  } = useAdminHealth()
  const { data: users,   isLoading: loadingUsers                             } = useAdminUsers()
  const { data: metrics, isLoading: loadingMetrics                           } = useAdminMetrics()

  const isLoading = loadingStatus && loadingHealth

  if (!token) return (
    <div className="pt-16 min-h-screen flex items-center justify-center">
      <Spinner className="w-8 h-8 text-vit-400" />
    </div>
  )

  // Non-admin notice
  if (user?.role && user.role !== 'admin') {
    return (
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <div className="text-center max-w-sm mx-4">
          <div className="w-14 h-14 rounded-full bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-6 h-6 text-yellow-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Admin Access Required</h2>
          <p className="text-white/40 text-sm mb-6">This page is restricted to administrators.</p>
          <Link to="/dashboard" className="px-5 py-2.5 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-25" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center justify-between">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-lg">
                  <Shield className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">Administration</h1>
                  <p className="text-white/40 text-sm">System management and monitoring</p>
                </div>
              </div>
            </motion.div>

            <button
              onClick={() => { refetchStatus(); refetchHealth() }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800/60 border border-white/10 text-white/50 hover:text-white text-sm transition-all"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', (loadingStatus || loadingHealth) && 'animate-spin')} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner className="w-8 h-8 text-vit-400" />
          </div>
        ) : (
          <>
            {/* System metrics */}
            <section>
              <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Platform Metrics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard icon={Users}      label="Total Users"       value={status?.total_users?.toLocaleString()}          color="text-vit-400"     i={0} />
                <MetricCard icon={Activity}   label="Active (30d)"      value={status?.active_users_30d?.toLocaleString()}     color="text-emerald-400" i={1} />
                <MetricCard icon={Star}       label="Validators"        value={status?.active_validators?.toLocaleString()}    color="text-yellow-400"  i={2} />
                <MetricCard icon={TrendingUp} label="Predictions Made"  value={status?.total_predictions?.toLocaleString()}   color="text-purple-400"  i={3} />
              </div>
            </section>

            {/* System health */}
            <section>
              <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">System Health</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Gateway health card */}
                <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Server className="w-4 h-4 text-vit-400" />
                      <span className="text-white font-medium text-sm">VIT Gateway</span>
                    </div>
                    <StatusBadge status={health?.status ?? status ? 'operational' : 'unknown'} size="sm" pulse />
                  </div>
                  <div className="space-y-0">
                    <Row label="Version"   value={health?.version ?? status?.version ?? '1.1.0'} />
                    <Row label="Database"  value={health?.db_connected !== false ? 'Connected' : 'Disconnected'} />
                    <Row label="Redis"     value={health?.redis?.status ?? 'Not configured'} />
                    <Row label="Models"    value={health?.models_loaded != null ? `${health.models_loaded} loaded` : null} />
                  </div>
                </div>

                {/* AI service */}
                <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-purple-400" />
                      <span className="text-white font-medium text-sm">VIT AI</span>
                    </div>
                    <a
                      href={`${ENDPOINTS.ai}/health`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-white/30 hover:text-white/60 transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </a>
                  </div>
                  <div className="flex flex-col items-center justify-center py-4 gap-2">
                    <Cpu className="w-8 h-8 text-white/15" />
                    <a
                      href={`${ENDPOINTS.ai}/health`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-vit-400 hover:text-vit-300 transition-colors"
                    >
                      View AI health →
                    </a>
                  </div>
                </div>

                {/* Storage */}
                <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-emerald-400" />
                      <span className="text-white font-medium text-sm">VIT Storage</span>
                    </div>
                    <a
                      href={`${ENDPOINTS.storage}/api/v1/admin/overview`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-white/30 hover:text-white/60 transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </a>
                  </div>
                  <div className="flex flex-col items-center justify-center py-4 gap-2">
                    <Database className="w-8 h-8 text-white/15" />
                    <a
                      href={ENDPOINTS.storage}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-vit-400 hover:text-vit-300 transition-colors"
                    >
                      Open Storage Console →
                    </a>
                  </div>
                </div>
              </div>
            </section>

            {/* Users table */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider">Recent Users</h2>
                <Link
                  to="/admin/users"
                  className="text-vit-400 hover:text-vit-300 text-xs flex items-center gap-1 transition-colors"
                >
                  View all <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
                {loadingUsers ? (
                  <div className="flex items-center justify-center py-10">
                    <Spinner className="w-5 h-5 text-vit-400" />
                  </div>
                ) : users && Array.isArray(users?.items ?? users) && (users?.items ?? users).length > 0 ? (
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/8">
                        {['ID', 'Email / Username', 'Role', 'Joined'].map(h => (
                          <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-5 py-3">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(users?.items ?? users).slice(0, 10).map((u: any) => (
                        <tr key={u.id} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                          <td className="px-5 py-3 text-white/40 text-sm font-mono">#{u.id}</td>
                          <td className="px-5 py-3">
                            <p className="text-white text-sm">{u.username}</p>
                            <p className="text-white/35 text-xs">{u.email}</p>
                          </td>
                          <td className="px-5 py-3">
                            <span className={cn(
                              'text-xs px-2 py-0.5 rounded-full border',
                              u.role === 'admin'
                                ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                                : 'bg-white/5 text-white/40 border-white/10'
                            )}>
                              {u.role}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-white/35 text-xs">
                            {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 gap-2">
                    <Users className="w-6 h-6 text-white/15" />
                    <p className="text-white/35 text-sm">
                      {users === null ? 'Admin access required to view users' : 'No users found'}
                    </p>
                  </div>
                )}
              </div>
            </section>

            {/* Metrics / analytics */}
            {metrics && (
              <section>
                <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">System Metrics</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard icon={Zap}      label="Requests/min"  value={metrics.requests_per_minute} color="text-vit-400"     i={0} />
                  <MetricCard icon={BarChart2} label="Avg Latency"   value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms}ms` : null} color="text-blue-400" i={1} />
                  <MetricCard icon={Activity}  label="Error Rate"    value={metrics.error_rate ? `${(metrics.error_rate * 100).toFixed(2)}%` : null} color="text-red-400"  i={2} />
                  <MetricCard icon={Database}  label="DB Pool"       value={metrics.db_pool_size} color="text-emerald-400" i={3} />
                </div>
              </section>
            )}

            {/* Admin quick links */}
            <section>
              <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Admin Actions</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {[
                  { label: 'Audit Log',       href: `${ENDPOINTS.gateway}/api/admin/audit-log`,           icon: Activity },
                  { label: 'Transactions',    href: `${ENDPOINTS.gateway}/api/admin/wallet/transactions`,  icon: TrendingUp },
                  { label: 'Training Jobs',   href: `${ENDPOINTS.gateway}/api/admin/training-jobs`,        icon: Cpu },
                  { label: 'API Docs',        href: `${ENDPOINTS.gateway}/docs`,                           icon: ChevronRight },
                ].map(({ label, href, icon: Icon }) => (
                  <a
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-center gap-3 p-4 bg-surface-800/60 border border-white/8 rounded-xl hover:border-white/20 hover:bg-surface-800/80 transition-all"
                  >
                    <Icon className="w-4 h-4 text-white/30 group-hover:text-white/60 transition-colors" />
                    <span className="text-sm text-white/60 group-hover:text-white transition-colors">{label}</span>
                  </a>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
