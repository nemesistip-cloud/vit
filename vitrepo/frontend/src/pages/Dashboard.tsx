import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard, Trophy, Brain, Wallet, Users, TrendingUp,
  Activity, ChevronRight, LogOut, Shield, Star, Zap, Target,
  BarChart3, Bell, Clock,
} from 'lucide-react'
import { getAuthToken, getStoredUser, clearAuth, authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { cn } from '@/lib/utils'

function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/status`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 60_000,
  })
}

function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/me`, {
        signal,
        headers: authHeaders(),
      })
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
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/summary`, {
        signal,
        headers: authHeaders(),
      })
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
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/top-opportunities`, {
        signal,
        headers: authHeaders(),
      })
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
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/leaderboard?limit=5`, {
        signal,
        headers: authHeaders(),
      })
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
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/recent-activity`, {
        signal,
        headers: authHeaders(),
      })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.activities ?? d.items ?? []
    },
    retry: false,
    staleTime: 60_000,
  })
}

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

export default function Dashboard() {
  const navigate = useNavigate()
  const token    = getAuthToken()
  const stored   = getStoredUser()

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const { data: systemStatus }     = useSystemStatus()
  const { data: me }               = useMe()
  const { data: summary }          = useDashboardSummary()
  const { data: opportunities }    = useTopOpportunities()
  const { data: leaderboard }      = useLeaderboardPreview()
  const { data: recentActivity }   = useRecentActivity()

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
        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Brain} label="Predictions Made" value={summary?.predictions_made ?? summary?.total_predictions} sub="All time" color="bg-vit-500/20" />
          <StatCard icon={Target} label="Win Rate" value={summary?.win_rate ? `${(summary.win_rate * 100).toFixed(1)}%` : null} sub="Overall accuracy" color="bg-emerald-500/20" />
          <StatCard icon={Wallet} label="VIT Balance" value={summary?.vit_balance ?? summary?.balance} sub="In wallet" color="bg-amber-500/20" />
          <StatCard icon={Star} label="CLV Score" value={summary?.clv_score ?? summary?.clv_tier} sub="Your tier" color="bg-purple-500/20" />
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
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Trophy className="w-10 h-10 text-white/10 mb-3" />
                <p className="text-white/40 text-sm">No opportunities right now</p>
                <p className="text-white/25 text-xs mt-1">Check back when matches are scheduled</p>
              </div>
            ) : (
              <div className="space-y-3">
                {opportunities.slice(0, 5).map((opp: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/3 hover:bg-white/6 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-vit-500/15 flex items-center justify-center text-xs font-bold text-vit-400">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{opp.home_team} vs {opp.away_team}</p>
                      <p className="text-xs text-white/40">{opp.league}</p>
                    </div>
                    {opp.confidence != null && (
                      <div className="text-right shrink-0">
                        <span className="text-sm font-bold text-vit-400">{Math.round(opp.confidence * 100)}%</span>
                        <p className="text-xs text-white/30">conf</p>
                      </div>
                    )}
                    {opp.final_ev != null && (
                      <div className="text-right shrink-0">
                        <span className={cn('text-sm font-bold', opp.final_ev > 0 ? 'text-emerald-400' : 'text-red-400')}>
                          {opp.final_ev > 0 ? '+' : ''}{opp.final_ev.toFixed(2)}
                        </span>
                        <p className="text-xs text-white/30">EV</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Leaderboard preview */}
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4 text-amber-400" />
                <h2 className="font-semibold text-white">Leaderboard</h2>
              </div>
              <Link to="/leaderboard" className="text-xs text-vit-400 hover:text-vit-300 flex items-center gap-1">
                Full <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
            {!leaderboard || leaderboard.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Users className="w-10 h-10 text-white/10 mb-3" />
                <p className="text-white/40 text-sm">No rankings yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {leaderboard.slice(0, 5).map((u: any, i: number) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className={cn('w-6 text-center text-sm font-bold', i === 0 ? 'text-amber-400' : i === 1 ? 'text-white/60' : i === 2 ? 'text-amber-700' : 'text-white/30')}>
                      {i + 1}
                    </span>
                    <div className="w-7 h-7 rounded-full bg-vit-500/20 flex items-center justify-center text-xs font-bold text-vit-400">
                      {(u.username || u.email || 'U')[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{u.username || u.email}</p>
                    </div>
                    <span className="text-xs text-emerald-400 font-medium">{u.win_rate ? `${(u.win_rate * 100).toFixed(0)}%` : u.score ?? ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick actions */}
        <div>
          <h2 className="font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <QuickCard icon={Trophy}   label="Browse Matches"    sub="View fixtures & AI picks" href="/matches"     color="bg-vit-500/20" />
            <QuickCard icon={BarChart3} label="Leaderboard"      sub="See top predictors"       href="/leaderboard" color="bg-amber-500/20" />
            <QuickCard icon={Wallet}   label="Wallet"            sub="VIT balance & transfers"  href="/wallet"      color="bg-emerald-500/20" />
            <QuickCard icon={Brain}    label="AI Intelligence"   sub="Model insights & signals" href="/ai"          color="bg-purple-500/20" />
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
