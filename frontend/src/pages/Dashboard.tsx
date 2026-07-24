import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, Brain, Wallet, TrendingUp,
  Activity, ChevronRight, LogOut, Shield, Star, Zap, Target,
  BarChart3, Clock, Vote, Coins, Store, Share2,
  Server, Cpu, Layers, AlertCircle,
  RefreshCw, HardDrive,
} from 'lucide-react'
import { getAuthToken, getStoredUser, clearAuth, authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS, chainApi, aiApi, storageApi, gatewayApi } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { SkeletonDashboard, Skeleton } from '@/components/ui/Skeleton'
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
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/me`, { signal, headers: authHeaders() })
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
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <p className="text-white/40 text-sm mb-1">Welcome back</p>
              <h1 className="text-2xl font-bold text-white">
                {user?.username || 'Predictor'}
              </h1>
              <div className="flex items-center gap-2 mt-2">
                {user?.role === 'admin' && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-vit-500/20 text-vit-400 text-xs font-medium">
                    <Shield className="w-3 h-3" /> Admin
                  </span>
                )}
                <StatusBadge status={systemStatus?.overall_status ?? 'loading'} size="sm" />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/predictions" className="px-4 py-2 rounded-xl bg-vit-500/20 border border-vit-500/30 text-vit-400 text-sm font-medium hover:bg-vit-500/30 transition-colors flex items-center gap-2">
                <Brain className="w-4 h-4" /> My Predictions
              </Link>
              <button onClick={logout} className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white/50 text-sm hover:text-white hover:bg-white/10 transition-colors flex items-center gap-2">
                <LogOut className="w-4 h-4" /> Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* System Notices */}
        {notices && notices.length > 0 && (
          <div className="space-y-2">
            {notices.slice(0, 3).map((notice: any, i: number) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-xl border text-sm',
                  notice.severity === 'critical' ? 'bg-red-500/10 border-red-500/30 text-red-300' :
                  notice.severity === 'warning'  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300' :
                  'bg-blue-500/10 border-blue-500/30 text-blue-300',
                )}
              >
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{notice.message || notice.title || notice.body}</span>
              </motion.div>
            ))}
          </div>
        )}

        {summaryLoading ? <SkeletonDashboard /> : (
          <>
            {/* Stats row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={Brain}    label="Predictions Made" value={summary?.predictions_made ?? summary?.total_predictions} sub="All time"         color="bg-vit-500/20"     />
              <StatCard icon={Target}   label="Win Rate"         value={summary?.win_rate ? `${(summary.win_rate * 100).toFixed(1)}%` : null}           sub="Overall accuracy"   color="bg-emerald-500/20" />
              <StatCard icon={Wallet}   label="VIT Balance"      value={summary?.vit_balance ?? summary?.balance}                                        sub="In wallet"          color="bg-amber-500/20"   />
              <StatCard icon={Star}     label="CLV Score"        value={summary?.clv_score ?? summary?.clv_tier}                                         sub="Your tier"          color="bg-purple-500/20"  />
            </div>
          </>
        )}

        {/* Platform Health */}
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-vit-400" />
              <h2 className="font-semibold text-white">Platform Health</h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-white/30">
              <RefreshCw className="w-3 h-3" />
              <span>Auto-refresh every 30s</span>
            </div>
          </div>

          {healthLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="space-y-3 p-4 bg-surface-900/50 border border-white/6 rounded-xl">
                  <Skeleton className="h-8 w-8 rounded-lg" />
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-2.5 w-16" />
                  <Skeleton className="h-2.5 w-12" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <ServiceHealthCard
                name="Gateway"
                icon={Server}
                color="bg-vit-500/20"
                status={gatewayHealth?.status}
                version={gatewayHealth?.version}
                latency={gatewayHealth?._latency}
                link="/status"
                extra={
                  gatewayHealth?.environment && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/40">Env</span>
                      <span className="text-white/50">{gatewayHealth.environment}</span>
                    </div>
                  )
                }
              />
              <ServiceHealthCard
                name="AI Oracle"
                icon={Cpu}
                color="bg-purple-500/20"
                status={aiHealth?.status}
                version={aiHealth?.version}
                latency={aiHealth?._latency}
                link="/ai"
                extra={
                  aiHealth?.models_loaded != null && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/40">Models</span>
                      <span className="text-vit-400 font-medium">{aiHealth.models_loaded}</span>
                    </div>
                  )
                }
              />
              <ServiceHealthCard
                name="Storage"
                icon={HardDrive}
                color="bg-emerald-500/20"
                status={storageHealth?.status}
                version={storageHealth?.version}
                latency={storageHealth?._latency}
                link="/storage"
                extra={
                  storageHealth?.providers?.active != null && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/40">Providers</span>
                      <span className="text-emerald-400 font-medium">{storageHealth.providers!.active} active</span>
                    </div>
                  )
                }
              />
              <ServiceHealthCard
                name="VIT Chain"
                icon={Layers}
                color="bg-cyan-500/20"
                status={chainHealth?.status === 'ok' ? 'healthy' : chainHealth?.status}
                version={chainHealth?.version}
                latency={chainHealth?._latency}
                link="/chain"
                extra={
                  chainHealth?.chain_id != null && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/40">Chain ID</span>
                      <span className="text-cyan-400 font-medium">{chainHealth.chain_id}</span>
                    </div>
                  )
                }
              />
            </div>
          )}
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Top Opportunities */}
          <div className="lg:col-span-2 bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-vit-400" />
                <h2 className="font-semibold text-white">Top Opportunities</h2>
              </div>
              <Link to="/matches" className="text-xs text-vit-400 hover:text-vit-300 flex items-center gap-1">
                View all <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            {!opportunities || opportunities.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Trophy className="w-10 h-10 text-white/10 mb-3" />
                <p className="text-white/40 text-sm">No opportunities right now</p>
                <Link to="/matches" className="mt-3 text-xs text-vit-400 hover:text-vit-300">Browse matches →</Link>
              </div>
            ) : (
              <div className="space-y-2">
                {opportunities.slice(0, 6).map((opp: any, i: number) => (
                  <Link key={i} to={`/matches/${opp.match_id ?? opp.id ?? ''}`}
                    className="flex items-center gap-4 p-3 rounded-lg hover:bg-white/5 transition-colors group">
                    <div className="w-8 h-8 rounded-lg bg-vit-500/15 flex items-center justify-center shrink-0">
                      <TrendingUp className="w-4 h-4 text-vit-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {opp.home_team ?? opp.title ?? opp.name ?? 'Match'}
                        {opp.away_team ? ` vs ${opp.away_team}` : ''}
                      </p>
                      <p className="text-xs text-white/40">{opp.competition ?? opp.league ?? opp.sport ?? ''}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold text-vit-400">
                        {opp.confidence ? `${(opp.confidence * 100).toFixed(0)}%` : opp.predicted_outcome ?? ''}
                      </p>
                      <p className="text-xs text-white/30">{opp.market ?? ''}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors shrink-0" />
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Leaderboard preview */}
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-amber-400" />
                <h2 className="font-semibold text-white">Top Predictors</h2>
              </div>
              <Link to="/leaderboard" className="text-xs text-vit-400 hover:text-vit-300 flex items-center gap-1">
                Full board <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            {!leaderboard || leaderboard.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Users className="w-8 h-8 text-white/10 mb-2" />
                <p className="text-white/40 text-sm">No data yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {leaderboard.slice(0, 5).map((u: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
                    <span className="text-xs font-bold text-white/30 w-4 text-right">{i + 1}</span>
                    <div className="w-6 h-6 rounded-full bg-vit-500/20 flex items-center justify-center shrink-0">
                      <span className="text-xs font-bold text-vit-400">{(u.username || u.name || '?')[0].toUpperCase()}</span>
                    </div>
                    <p className="text-sm text-white/80 flex-1 truncate">{u.username || u.name}</p>
                    <span className="text-xs text-emerald-400 font-medium">{u.win_rate ? `${(u.win_rate * 100).toFixed(0)}%` : u.score ?? ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Latest Blocks + AI Usage + Storage Usage */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Latest Blocks */}
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <h2 className="font-semibold text-white">Latest Blocks</h2>
              </div>
              <Link to="/chain" className="text-xs text-vit-400 hover:text-vit-300 flex items-center gap-1">
                Explorer <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            {blocks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Layers className="w-8 h-8 text-white/10 mb-2" />
                <p className="text-white/40 text-sm">Chain connecting…</p>
              </div>
            ) : (
              <div className="space-y-2">
                {blocks.slice(0, 5).map((block: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
                    <div className="w-7 h-7 rounded-lg bg-cyan-500/15 flex items-center justify-center shrink-0">
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">#{block.index ?? block.height ?? block.number}</p>
                      <p className="text-xs text-white/30 truncate">{block.hash ? `${block.hash.substring(0, 12)}…` : ''}</p>
                    </div>
                    <span className="text-xs text-white/40 shrink-0">
                      {block.tx_count != null ? `${block.tx_count} tx` : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI Usage */}
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                <h2 className="font-semibold text-white">AI Oracle</h2>
              </div>
              <Link to="/ai" className="text-xs text-vit-400 hover:text-vit-300 flex items-center gap-1">
                Details <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Status</span>
                <span className={cn(
                  'text-sm font-medium',
                  aiHealth?.status?.toLowerCase() === 'healthy' ? 'text-emerald-400' : 'text-amber-400',
                )}>
                  {aiHealth?.status ?? '—'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Models Loaded</span>
                <span className="text-sm font-medium text-vit-400">{aiHealth?.models_loaded ?? '—'}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Response Time</span>
                <span className={cn(
                  'text-sm font-medium',
                  aiHealth?._latency == null ? 'text-white/40' :
                  aiHealth._latency < 300 ? 'text-emerald-400' :
                  aiHealth._latency < 1000 ? 'text-amber-400' : 'text-red-400',
                )}>
                  {aiHealth?._latency != null ? `${aiHealth._latency} ms` : '—'}
                </span>
              </div>
              {summary?.predictions_today != null && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                  <span className="text-sm text-white/60">Predictions Today</span>
                  <span className="text-sm font-medium text-white">{summary.predictions_today}</span>
                </div>
              )}
            </div>
          </div>

          {/* Storage Usage */}
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-emerald-400" />
                <h2 className="font-semibold text-white">Storage</h2>
              </div>
              <Link to="/storage" className="text-xs text-vit-400 hover:text-vit-300 flex items-center gap-1">
                Details <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Status</span>
                <span className="text-sm font-medium text-emerald-400">
                  {storageHealth?.status?.replace(/_/g, ' ') ?? '—'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Providers</span>
                <span className="text-sm font-medium text-vit-400">
                  {storageHealth?.providers ? `${storageHealth.providers.active}/${storageHealth.providers.available}` : '—'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Plane</span>
                <span className="text-sm font-medium text-white/60 capitalize">
                  {storageHealth?.plane ?? '—'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface-900/50">
                <span className="text-sm text-white/60">Database</span>
                <span className={cn(
                  'text-sm font-medium',
                  storageHealth?.database === 'connected' ? 'text-emerald-400' : 'text-amber-400',
                )}>
                  {storageHealth?.database ?? '—'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div>
          <h2 className="font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <QuickCard icon={Trophy}    label="Browse Matches"    sub="Fixtures & AI picks"       href="/matches"          color="bg-vit-500/20"     />
            <QuickCard icon={Brain}     label="Predictions"       sub="My picks & AI signals"     href="/predictions"      color="bg-purple-500/20"  />
            <QuickCard icon={Wallet}    label="Wallet"            sub="VIT balance & transfers"   href="/wallet"           color="bg-emerald-500/20" />
            <QuickCard icon={Vote}      label="Governance"        sub="Vote on proposals"         href="/governance"       color="bg-cyan-500/20"    />
            <QuickCard icon={BarChart3} label="Leaderboard"       sub="See top predictors"        href="/leaderboard"      color="bg-amber-500/20"   />
            <QuickCard icon={Coins}     label="DeFi Pools"        sub="Yield & liquidity"         href="/defi"             color="bg-teal-500/20"    />
            <QuickCard icon={Store}     label="Marketplace"       sub="Buy & sell signals"        href="/marketplace"      color="bg-rose-500/20"    />
            <QuickCard icon={Share2}    label="Referral"          sub="Earn from your network"    href="/referral"         color="bg-orange-500/20"  />
          </div>
        </div>

        {/* Recent activity */}
        {recentActivity && recentActivity.length > 0 && (
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-white/50" />
                <h2 className="font-semibold text-white">Recent Activity</h2>
              </div>
            </div>
            <div className="space-y-3">
              {recentActivity.slice(0, 8).map((act: any, i: number) => (
                <div key={i} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
                  <div className="w-2 h-2 rounded-full bg-vit-400 shrink-0 mt-1" />
                  <div className="flex-1">
                    <p className="text-sm text-white/70">{act.description || act.action || act.type}</p>
                    {act.created_at && <p className="text-xs text-white/30 mt-0.5">{new Date(act.created_at).toLocaleString()}</p>}
                  </div>
                  {act.amount && <span className="text-sm font-medium text-emerald-400">{act.amount}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
