import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity, LogIn, LogOut, Shield, Wallet, Brain, Vote,
  Bell, User, AlertTriangle, CheckCircle2, RefreshCw, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'

interface FeedItem {
  id: number
  action: string
  details: Record<string, any>
  created_at: string
}

const ACTION_META: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  login:            { icon: LogIn,        color: 'text-emerald-400', label: 'Signed in' },
  login_success:    { icon: LogIn,        color: 'text-emerald-400', label: 'Signed in' },
  login_failed:     { icon: AlertTriangle,color: 'text-red-400',     label: 'Failed login attempt' },
  logout:           { icon: LogOut,       color: 'text-white/40',    label: 'Signed out' },
  password_reset:   { icon: Shield,       color: 'text-amber-400',   label: 'Password reset' },
  '2fa_enabled':    { icon: Shield,       color: 'text-violet-400',  label: '2FA enabled' },
  '2fa_disabled':   { icon: Shield,       color: 'text-orange-400',  label: '2FA disabled' },
  email_verified:   { icon: CheckCircle2, color: 'text-emerald-400', label: 'Email verified' },
  wallet_linked:    { icon: Wallet,       color: 'text-cyan-400',    label: 'Wallet linked' },
  profile_update:   { icon: User,         color: 'text-blue-400',    label: 'Profile updated' },
  prediction:       { icon: Brain,        color: 'text-indigo-400',  label: 'Prediction placed' },
  vote:             { icon: Vote,         color: 'text-pink-400',    label: 'Vote cast' },
}

function getFallback(action: string) {
  return { icon: Activity, color: 'text-white/30', label: action.replace(/_/g, ' ') }
}

interface ActivityFeedProps {
  open: boolean
  onClose: () => void
}

export function ActivityFeedPanel({ open, onClose }: ActivityFeedProps) {
  const { data, isLoading, refetch } = useQuery<FeedItem[]>({
    queryKey: ['activity-feed'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/identity/me/login-history?limit=30`, {
        signal,
        headers: authHeaders(),
      })
      if (!r.ok) return []
      return r.json()
    },
    enabled: open,
    staleTime: 30_000,
    refetchInterval: open ? 60_000 : false,
  })

  return (
    <AnimatePresence>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed right-4 top-20 z-50 w-80 rounded-2xl border border-white/10 bg-surface-900/97 backdrop-blur-xl shadow-2xl shadow-black/60 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/8">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-violet-400" />
                <span className="text-sm font-semibold text-white">Activity</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => refetch()}
                  className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Feed */}
            <div className="max-h-96 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-10">
                  <div className="w-5 h-5 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : !data || data.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 gap-2">
                  <Activity className="w-8 h-8 text-white/10" />
                  <p className="text-white/30 text-sm">No recent activity</p>
                </div>
              ) : (
                <div className="p-2 space-y-0.5">
                  {data.map((item, i) => {
                    const meta = ACTION_META[item.action] ?? getFallback(item.action)
                    const Icon = meta.icon
                    return (
                      <motion.div
                        key={item.id}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className="flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/3 transition-colors"
                      >
                        <div className={cn('w-7 h-7 rounded-full bg-white/5 flex items-center justify-center shrink-0 mt-0.5')}>
                          <Icon className={cn('w-3.5 h-3.5', meta.color)} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white/80 font-medium leading-snug">{meta.label}</p>
                          {item.details?.provider && (
                            <p className="text-xs text-white/30 mt-0.5">via {item.details.provider}</p>
                          )}
                          {item.details?.ip && (
                            <p className="text-xs text-white/20 mt-0.5">IP: {item.details.ip}</p>
                          )}
                          <p className="text-[10px] text-white/20 mt-1">{timeAgo(item.created_at)}</p>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
