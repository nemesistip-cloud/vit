import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard, Trophy, HardDrive, Brain, Wallet,
  Users, TrendingUp, Activity, ChevronRight, LogOut,
  Shield, Star,
} from 'lucide-react'
import { getAuthToken, getStoredUser, clearAuth, authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'

// ── Hooks ─────────────────────────────────────────────────────────────────────

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
      const r = await fetch(`${ENDPOINTS.gateway}/api/auth/auth/me`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 300_000,
  })
}

function useWalletInfo() {
  return useQuery({
    queryKey: ['wallet-me'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/me`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 120_000,
  })
}

// ── Sub-components ────────────────────────────────────────────────────────────

function QuickCard({
  icon: Icon, label, sub, href, color,
}: {
  icon: React.ElementType
  label: string
  sub: string
  href: string
  color: string
}) {
  return (
    <Link
      to={href}
      className="group flex flex-col gap-3 p-5 bg-surface-800/60 border border-white/8 rounded-xl hover:border-white/20 hover:bg-surface-800/80 transition-all"
    >
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

function StatRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/6 last:border-0">
      <span className="text-sm text-white/40">{label}</span>
      <span className="text-sm font-medium text-white">{value ?? '—'}</span>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const token    = getAuthToken()
  const stored   = getStoredUser()

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const { data: systemStatus } = useSystemStatus()
  const { data: me }           = useMe()
  const { data: wallet }       = useWalletInfo()

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
        <div className="absolute inset-0 section-grid opacity-25" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-start justify-between">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <div className="flex items-center gap-3 mb-1">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-vit-500 to-vit-700 flex items-center justify-center shadow-lg shadow-vit-500/30">
                  <span className="text-white font-bold text-base">
                    {user?.username?.[0]?.toUpperCase() ?? 'U'}
                  </span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">
                    Welcome back, {user?.username ?? 'User'}
                  </h1>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-white/40 text-xs">{user?.role ?? 'user'}</span>
                    {user?.role === 'admin' && (
                      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/15 text-yellow-400 border border-yellow-500/20">
                        <Shield className="w-2.5 h-2.5" /> Admin
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
            <button
              onClick={logout}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800/60 border border-white/10 text-white/50 hover:text-white hover:border-white/20 text-sm transition-all"
            >
              <LogOut className="w-3.5 h-3.5" /> Sign out
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Platform stats */}
        {systemStatus && (
          <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Platform Overview</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { icon: Users,     label: 'Total Users',      value: systemStatus.total_users?.toLocaleString() ?? '—',       color: 'text-vit-400' },
                { icon: Activity,  label: 'Active (30d)',      value: systemStatus.active_users_30d?.toLocaleString() ?? '—', color: 'text-emerald-400' },
                { icon: Star,      label: 'Validators',        value: systemStatus.active_validators?.toLocaleString() ?? '—', color: 'text-yellow-400' },
                { icon: TrendingUp,label: 'Predictions',       value: systemStatus.total_predictions?.toLocaleString() ?? '—', color: 'text-purple-400' },
              ].map(({ icon: Icon, label, value, color }, i) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-5 bg-surface-800/60 border border-white/8 rounded-xl"
                >
                  <Icon className={`w-4 h-4 mb-3 ${color}`} />
                  <p className="text-xl font-bold text-white">{value}</p>
                  <p className="text-white/40 text-xs mt-0.5">{label}</p>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Quick actions */}
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Quick Access</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <QuickCard icon={Trophy}    label="Matches"  sub="Sports predictions"      href="/matches"  color="bg-gradient-to-br from-vit-600 to-vit-800" />
              <QuickCard icon={HardDrive} label="Storage"  sub="Files & shared links"    href="/storage"  color="bg-gradient-to-br from-emerald-600 to-emerald-800" />
              <QuickCard icon={Brain}     label="AI"       sub="Inference & models"      href="/ai"       color="bg-gradient-to-br from-purple-600 to-purple-800" />
              <QuickCard icon={Wallet}    label="Wallet"   sub="Balance & transactions"  href="/wallet"   color="bg-gradient-to-br from-yellow-600 to-yellow-800" />
              <QuickCard icon={Activity}  label="Status"   sub="System health"           href="/status"   color="bg-gradient-to-br from-blue-600 to-blue-800" />
              {user?.role === 'admin' && (
                <QuickCard icon={Shield} label="Admin"    sub="System management"        href="/admin"    color="bg-gradient-to-br from-red-600 to-red-800" />
              )}
            </div>
          </motion.section>

          {/* Wallet / account info */}
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Account</h2>
            <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
              {wallet ? (
                <>
                  <div className="mb-4 p-4 rounded-lg bg-gradient-to-br from-vit-900/60 to-surface-900/60 border border-vit-500/20">
                    <p className="text-white/40 text-xs mb-1">VIT Balance</p>
                    <p className="text-2xl font-bold text-white">
                      {wallet.vitcoin_balance?.toLocaleString(undefined, { minimumFractionDigits: 2 }) ?? '0.00'}
                      <span className="text-vit-400 text-sm ml-1.5 font-medium">VIT</span>
                    </p>
                  </div>
                  <div className="space-y-0">
                    <StatRow label="Plan" value={wallet.plan} />
                    <StatRow label="Staked" value={wallet.staked_vit != null ? `${wallet.staked_vit} VIT` : null} />
                    <StatRow label="Storage Credits" value={wallet.storage_credits != null ? `${wallet.storage_credits} GB` : null} />
                  </div>
                </>
              ) : (
                <>
                  <StatRow label="Username" value={user?.username} />
                  <StatRow label="Role" value={user?.role} />
                  <StatRow label="User ID" value={user?.id} />
                </>
              )}

              <Link
                to="/storage"
                className="mt-4 flex items-center justify-center gap-2 w-full py-2 rounded-lg border border-white/10 text-white/50 hover:text-white hover:border-white/25 text-sm transition-all"
              >
                <HardDrive className="w-3.5 h-3.5" /> Open Storage
              </Link>
            </div>
          </motion.section>
        </div>

        {/* Status summary */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Service Status</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { label: 'VIT Gateway',  href: ENDPOINTS.gateway + '/health',  icon: Activity },
              { label: 'VIT AI',       href: ENDPOINTS.ai + '/health',        icon: Brain },
              { label: 'VIT Storage',  href: ENDPOINTS.storage + '/health',   icon: HardDrive },
            ].map(({ label, icon: Icon }) => (
              <div key={label} className="flex items-center gap-3 p-4 bg-surface-800/60 border border-white/8 rounded-xl">
                <Icon className="w-4 h-4 text-white/30" />
                <span className="text-white/60 text-sm flex-1">{label}</span>
                <StatusBadge status="operational" size="sm" pulse />
              </div>
            ))}
          </div>
        </motion.section>
      </div>
    </div>
  )
}
