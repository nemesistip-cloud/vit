import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, CheckCheck, X, Trophy, Wallet as WalletIcon, Vote, Star } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

type NotifType = 'prediction' | 'wallet' | 'governance' | 'reward' | 'system'

interface Notification {
  id: number
  type: NotifType
  title: string
  body: string
  read: boolean
  created_at: string
  url?: string
}

const TYPE_ICON: Record<NotifType, React.ElementType> = {
  prediction: Trophy,
  wallet:     WalletIcon,
  governance: Vote,
  reward:     Star,
  system:     Bell,
}

const TYPE_COLOR: Record<NotifType, string> = {
  prediction: 'text-vit-400',
  wallet:     'text-emerald-400',
  governance: 'text-blue-400',
  reward:     'text-amber-400',
  system:     'text-white/50',
}

function useNotifications() {
  return useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/notifications?limit=20`, {
        signal,
        headers: authHeaders(),
      })
      return r.ok ? r.json().then((d: unknown) => Array.isArray(d) ? d as Notification[] : []) : []
    },
    retry: false,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref             = useRef<HTMLDivElement>(null)
  const qc              = useQueryClient()

  const { data: notifications = [] } = useNotifications()
  const unread = notifications.filter(n => !n.read).length

  const markAll = useMutation({
    mutationFn: async () => {
      await fetch(`${ENDPOINTS.gateway}/api/notifications/mark-all-read`, {
        method: 'POST',
        headers: authHeaders(),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const markOne = useMutation({
    mutationFn: async (id: number) => {
      await fetch(`${ENDPOINTS.gateway}/api/notifications/${id}/read`, {
        method: 'POST',
        headers: authHeaders(),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="relative p-2 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/5 transition-all"
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-vit-500 text-white text-[9px] font-bold flex items-center justify-center leading-none">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-80 rounded-2xl border border-white/10 bg-surface-900/98 backdrop-blur-xl shadow-2xl overflow-hidden z-50"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/8">
              <p className="text-sm font-semibold text-white">Notifications</p>
              <div className="flex items-center gap-2">
                {unread > 0 && (
                  <button
                    onClick={() => markAll.mutate()}
                    className="flex items-center gap-1 text-xs text-vit-400 hover:text-vit-300 transition-colors"
                  >
                    <CheckCheck className="w-3.5 h-3.5" /> Mark all read
                  </button>
                )}
                <button onClick={() => setOpen(false)} className="p-1 rounded text-white/25 hover:text-white/60 transition-colors">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* List */}
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 gap-2">
                  <Bell className="w-8 h-8 text-white/10" />
                  <p className="text-white/30 text-sm">No notifications yet</p>
                </div>
              ) : (
                notifications.map(n => {
                  const Icon = TYPE_ICON[n.type as NotifType] ?? Bell
                  const color = TYPE_COLOR[n.type as NotifType] ?? 'text-white/50'
                  return (
                    <button
                      key={n.id}
                      onClick={() => { markOne.mutate(n.id); if (n.url) window.location.href = n.url }}
                      className={cn(
                        'w-full flex items-start gap-3 px-4 py-3.5 text-left border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors',
                        !n.read && 'bg-vit-500/5',
                      )}
                    >
                      <div className={cn('w-7 h-7 rounded-full bg-white/5 flex items-center justify-center shrink-0 mt-0.5', !n.read && 'bg-vit-500/10')}>
                        <Icon className={cn('w-3.5 h-3.5', color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={cn('text-sm font-medium leading-snug', n.read ? 'text-white/60' : 'text-white')}>{n.title}</p>
                        <p className="text-xs text-white/30 mt-0.5 leading-snug line-clamp-2">{n.body}</p>
                        <p className="text-[10px] text-white/20 mt-1">{new Date(n.created_at).toLocaleString()}</p>
                      </div>
                      {!n.read && <span className="w-2 h-2 rounded-full bg-vit-400 shrink-0 mt-2" />}
                    </button>
                  )
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
