import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, Brain, Wallet, TrendingUp,
  Activity, ChevronRight, LogOut, Shield, Star, Zap, Target,
  BarChart3, Clock, Vote, Coins, Store, Share2,
  Server, Cpu, Layers, AlertCircle,
  RefreshCw, HardDrive, Users,
} from 'lucide-react'
import { getAuthToken, getStoredUser, clearAuth, authHeaders, fetchWithAuth } from '@/hooks/useAuth'
import { ENDPOINTS, chainApi, aiApi, storageApi, gatewayApi } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { SkeletonDashboard, Skeleton } from '@/components/ui/Skeleton'
import { DashboardWorkspace } from '@/components/dashboard/DashboardWorkspace'
import { cn } from '@/lib/utils'

// ── Data hooks ────────────────────────────────────────────────────────────────

function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/status`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 60_000,
    retry: 1,
  })
}

function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async ({ signal }) => {
      // fetchWithAuth automatically clears auth and redirects to /login on 401,
      // ensuring an expired token is detected immediately on the dashboard.
      const r = await fetchWithAuth(`${ENDPOINTS.gateway}/api/auth/me`, { signal })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 300_000,
  })
}

function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/summary`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 120_000,
  })
}

function useTopOpportunities() {
  return useQuery({
    queryKey: ['top-opportunities'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/top-opportunities`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.opportunities ?? d.matches ?? []
    },
    retry: false,
    staleTime: 120_000,
  })
}

function useLeaderboardPreview() {
  return useQuery({
    queryKey: ['leaderboard-preview'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/leaderboard?limit=5`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.leaderboard ?? d.items ?? []
    },
    retry: false,
    staleTime: 300_000,
  })
}

function useRecentActivity() {
  return useQuery({
    queryKey: ['recent-activity'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/recent-activity`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.activities ?? d.items ?? []
    },
    retry: false,
    staleTime: 60_000,
  })
}

function useGatewayHealth() {
  return useQuery({
    queryKey: ['health', 'gateway'],
    queryFn: ({ signal }) => gatewayApi.health(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

function useAIHealthDash() {
  return useQuery({
    queryKey: ['health', 'ai'],
    queryFn: ({ signal }) => aiApi.health(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

function useStorageHealthDash() {
  return useQuery({
    queryKey: ['health', 'storage'],
    queryFn: ({ signal }) => storageApi.health(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

function useChainHealthDash() {
  return useQuery({
    queryKey: ['health', 'chain'],
    queryFn: ({ signal }) => chainApi.ping(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

function useLatestBlocks() {
  return useQuery({
    queryKey: ['latest-blocks'],
    queryFn: ({ signal }) => chainApi.blocks(signal),
    refetchInterval: 30_000,
    retry: 1,
  })
}

function useSystemNotices() {
  return useQuery({
    queryKey: ['system-notices'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/notices`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.notices ?? []
    },
    staleTime: 300_000,
    retry: 1,
  })
}

// ── Subcomponents ─────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value?: string | number | null; sub?: string; color: string
}) {
  return (
    <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-white/40 font-medium uppercase tracking-wide">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
      {sub && <div className="text-xs text-white/40 mt-1">{sub}</div>}
    </div>
  )
}

function QuickCard({ icon: Icon, label, sub, href, color }: {
  icon: React.ElementType; label: string; sub: string; href: string; color: string
}) {
  return (
    <Link to={href} className="group flex flex-col gap-3 p-5 bg-surface-800/60 border border-white/8 rounded-xl hover:border-white/20 hover:bg-surface-800/80 transition-all">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
        <Icon className="w-4 h-4 text-white" />
      </div>
      <div>
        <p className="font-medium text-white text-sm">{label}</p>
        <p className="text-white/40 text-xs mt-0.5">{sub}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors self-end" />
    </Link>
  )
}

function ServiceHealthCard({
  name, icon: Icon, color, status, version, latency, extra, link,
}: {
  name: string
  icon: React.ElementType
  color: string
  status?: string | null
  version?: string | null
  latency?: number | null
  extra?: React.ReactNode
  link: string
}) {
  const healthy = ['healthy', 'ok', 'quantum_stable']
  const isUp    = status && healthy.includes(status.toLowerCase())
  const isDown  = !status || status.toLowerCase() === 'unhealthy'

  const dot = isDown
    ? 'bg-red-400'
    : isUp
      ? 'bg-emerald-400 shadow-[0_0_6px_1px_rgba(52,211,153,0.5)]'
      : 'bg-amber-400'

  return (
    <Link to={link} className="group flex flex-col gap-3 p-4 bg-surface-900/50 border border-white/6 rounded-xl hover:border-white/15 transition-all">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
            <Icon className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-medium text-white">{name}</span>
        </div>
        <span className={`w-2 h-2 rounded-full ${dot} shrink-0`} />
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/40">Status</span>
          <span className={cn(
            'font-medium',
            isUp ? 'text-emerald-400' : isDown ? 'text-red-400' : 'text-amber-400',
          )}>
            {status ? status.replace(/_/g, ' ') : 'Unknown'}
          </span>
        </div>
        {version && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/40">Version</span>
            <span className="text-white/60">{version}</span>
          </div>
        )}
        {latency != null && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/40">Latency</span>
            <span className={cn(
              'font-medium',
              latency < 300 ? 'text-emerald-400' : latency < 1000 ? 'text-amber-400' : 'text-red-400',
            )}>
              {latency} ms
            </span>
          </div>
        )}
        {extra}
      </div>
    </Link>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const token    = getAuthToken()
  const stored   = getStoredUser()

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const { data: systemStatus }          = useSystemStatus()
  const { data: me }                    = useMe()
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary()
  const { data: opportunities }         = useTopOpportunities()
  const { data: leaderboard }           = useLeaderboardPreview()
  const { data: recentActivity }        = useRecentActivity()

  // Platform health
  const { data: gatewayHealth, isLoading: gwLoading }  = useGatewayHealth()
  const { data: aiHealth,      isLoading: aiLoading }  = useAIHealthDash()
  const { data: storageHealth, isLoading: stgLoading } = useStorageHealthDash()
  const { data: chainHealth,   isLoading: chnLoading } = useChainHealthDash()
  const { data: blocksData }                           = useLatestBlocks()
  const { data: notices }                              = useSystemNotices()

  const healthLoading = gwLoading || aiLoading || stgLoading || chnLoading
  const user = me ?? stored

  function logout() {
    clearAuth()
    navigate('/')
  }

  if (!token) {
    return (
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <Spinner className="w-8 h-8 text-vit-400" />
      </div>
    )
  }

  const blocks = blocksData?.blocks ?? (Array.isArray(blocksData) ? blocksData : [])

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="mb-1 text-sm text-white/40">Welcome back</p>
              <h1 className="text-2xl font-bold text-white">{user?.username || 'Predictor'}</h1>
              <div className="mt-2 flex items-center gap-2">
                {user?.role === 'admin' && (
                  <span className="flex items-center gap-1 rounded-full bg-vit-500/20 px-2 py-0.5 text-xs font-medium text-vit-400">
                    <Shield className="h-3 w-3" /> Admin
                  </span>
                )}
                <StatusBadge status={systemStatus?.overall_status ?? 'loading'} size="sm" />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/predictions" className="flex items-center gap-2 rounded-xl border border-vit-500/30 bg-vit-500/20 px-4 py-2 text-sm font-medium text-vit-400 transition-colors hover:bg-vit-500/30">
                <Brain className="h-4 w-4" /> My Predictions
              </Link>
              <button onClick={logout} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/50 transition-colors hover:bg-white/10 hover:text-white">
                <LogOut className="h-4 w-4" /> Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
        {notices && notices.length > 0 && (
          <div className="space-y-2">
            {notices.slice(0, 3).map((notice: any, i: number) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  'flex items-center gap-3 rounded-xl border px-4 py-3 text-sm',
                  notice.severity === 'critical' ? 'border-red-500/30 bg-red-500/10 text-red-300' :
                  notice.severity === 'warning'  ? 'border-amber-500/30 bg-amber-500/10 text-amber-300' :
                  'border-blue-500/30 bg-blue-500/10 text-blue-300',
                )}
              >
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{notice.message || notice.title || notice.body}</span>
              </motion.div>
            ))}
          </div>
        )}

        {summaryLoading ? <SkeletonDashboard /> : (
          <DashboardWorkspace
            summary={summary}
            opportunities={opportunities ?? []}
            recentActivity={recentActivity ?? []}
            gatewayHealth={gatewayHealth}
            aiHealth={aiHealth}
            storageHealth={storageHealth}
            chainHealth={chainHealth}
            blocks={blocks}
            leaderboard={leaderboard ?? []}
            healthLoading={healthLoading}
            summaryLoading={summaryLoading}
            user={user}
          />
        )}
      </div>
    </div>
  )
}
