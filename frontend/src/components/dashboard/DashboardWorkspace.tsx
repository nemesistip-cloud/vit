import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  ArrowRight,
  Bell,
  Brain,
  ChevronRight,
  Clock,
  Cpu,
  Crown,
  GripVertical,
  HardDrive,
  Layers,
  Move,
  RefreshCw,
  Rocket,
  Server,
  Settings2,
  Shield,
  Sparkles,
  Star,
  Trophy,
  Wallet,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, fetchWithAuth } from '@/hooks/useAuth'

const STORAGE_KEY = 'vit:dashboard-workspace:v1'

type WidgetId = 'overview' | 'recommendations' | 'notifications' | 'status' | 'activity' | 'shortcuts'
type WidgetSize = 'compact' | 'default' | 'wide'

interface WidgetPreference {
  id: WidgetId
  size: WidgetSize
}

interface NotificationItem {
  id: number
  title: string
  body: string
  read: boolean
  created_at: string
  url?: string
}

interface DashboardWorkspaceProps {
  summary?: any
  systemStatus?: any
  opportunities?: any[]
  recentActivity?: any[]
  notices?: any[]
  gatewayHealth?: any
  aiHealth?: any
  storageHealth?: any
  chainHealth?: any
  blocks?: any[]
  leaderboard?: any[]
  healthLoading?: boolean
  summaryLoading?: boolean
  user?: any
}

const DEFAULT_LAYOUT: WidgetPreference[] = [
  { id: 'overview', size: 'wide' },
  { id: 'recommendations', size: 'default' },
  { id: 'notifications', size: 'default' },
  { id: 'status', size: 'default' },
  { id: 'activity', size: 'wide' },
  { id: 'shortcuts', size: 'default' },
]

function getInitialLayout() {
  if (typeof window === 'undefined') return DEFAULT_LAYOUT
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_LAYOUT
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return DEFAULT_LAYOUT
    return parsed.filter((item: any) => item && typeof item.id === 'string') as WidgetPreference[]
  } catch {
    return DEFAULT_LAYOUT
  }
}

function getSizeClass(size: WidgetSize) {
  switch (size) {
    case 'wide':
      return 'md:col-span-2 xl:col-span-3'
    case 'compact':
      return 'md:col-span-1'
    default:
      return 'md:col-span-1 xl:col-span-2'
  }
}

function WidgetCard({
  title,
  subtitle,
  children,
  id,
  size,
  onResize,
  onDragStart,
  onDrop,
  dragging,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  id: WidgetId
  size: WidgetSize
  onResize: (next: WidgetSize) => void
  onDragStart: (id: WidgetId) => void
  onDrop: (id: WidgetId) => void
  dragging: boolean
}) {
  return (
    <motion.div
      layout
      draggable
      onDragStart={() => onDragStart(id)}
      onDragOver={(e) => e.preventDefault()}
      onDrop={() => onDrop(id)}
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-white/8 bg-surface-800/70 p-4 shadow-lg shadow-black/25 backdrop-blur-xl',
        dragging ? 'opacity-70 ring-1 ring-vit-400/40' : 'opacity-100',
        getSizeClass(size),
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GripVertical className="h-4 w-4 text-white/20" />
            <h3 className="text-sm font-semibold text-white">{title}</h3>
          </div>
          {subtitle && <p className="mt-1 text-xs text-white/35">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-1.5">
          {(['compact', 'default', 'wide'] as WidgetSize[]).map(option => (
            <button
              key={option}
              type="button"
              onClick={() => onResize(option)}
              className={cn(
                'rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors',
                size === option ? 'bg-vit-500/20 text-vit-300' : 'bg-white/5 text-white/35 hover:text-white/70',
              )}
            >
              {option === 'default' ? 'std' : option}
            </button>
          ))}
        </div>
      </div>
      {children}
    </motion.div>
  )
}

function useNotifications() {
  const [items, setItems] = useState<NotificationItem[]>([])
  useEffect(() => {
    let active = true
    async function load() {
      try {
        const base = ENDPOINTS.gateway ? ENDPOINTS.gateway.replace(/\/$/, '') : ''
        const res = await fetchWithAuth(`${base}/api/notifications?limit=4`)
        if (!res.ok) return
        const payload = await res.json()
        const next = Array.isArray(payload) ? payload : payload.items ?? []
        if (active) setItems(next.slice(0, 4))
      } catch {
        if (active) setItems([])
      }
    }
    load()
    return () => { active = false }
  }, [])
  return items
}

export function DashboardWorkspace({
  summary,
  opportunities = [],
  recentActivity = [],
  gatewayHealth,
  aiHealth,
  storageHealth,
  chainHealth,
  blocks = [],
  leaderboard = [],
  healthLoading = false,
  summaryLoading = false,
  user,
}: DashboardWorkspaceProps) {
  const [layout, setLayout] = useState<WidgetPreference[]>(getInitialLayout)
  const [dragging, setDragging] = useState<WidgetId | null>(null)
  const notifications = useNotifications()

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
  }, [layout])

  const recommendations = useMemo(() => {
    const base = [
      {
        id: 'earn',
        title: 'Complete your profile',
        reason: 'A fuller profile unlocks higher trust and better recommendations.',
        benefit: 'Better access to premium opportunities',
        reward: 'Boosted eligibility',
        difficulty: 'Low',
        action: '/settings',
      },
      {
        id: 'stake',
        title: 'Review wallet actions',
        reason: 'Your wallet activity is active and ready for follow-up actions.',
        benefit: 'Keep balances and rewards moving',
        reward: 'Higher engagement',
        difficulty: 'Low',
        action: '/wallet',
      },
      {
        id: 'storage',
        title: 'Upload or verify storage',
        reason: 'Storage usage and proofs improve your platform credibility.',
        benefit: 'Stronger storage footprint',
        reward: 'More utility',
        difficulty: 'Medium',
        action: '/storage',
      },
      {
        id: 'ai',
        title: 'Explore AI workspace',
        reason: 'The AI layer is already connected to the platform shell.',
        benefit: 'Faster model and insight workflows',
        reward: 'Higher productivity',
        difficulty: 'Low',
        action: '/ai',
      },
    ]

    if (opportunities.length > 0) {
      return [
        {
          id: 'opportunity',
          title: 'Act on live opportunities',
          reason: 'There are fresh prediction opportunities available now.',
          benefit: 'Capitalise on active signals',
          reward: 'Potential upside',
          difficulty: 'Low',
          action: '/matches',
        },
        ...base,
      ]
    }

    return base
  }, [opportunities.length])

  const reorderWidget = (targetId: WidgetId) => {
    if (!dragging || dragging === targetId) return
    setLayout(current => {
      const next = [...current]
      const fromIndex = next.findIndex(item => item.id === dragging)
      const toIndex = next.findIndex(item => item.id === targetId)
      if (fromIndex < 0 || toIndex < 0) return current
      const [moved] = next.splice(fromIndex, 1)
      next.splice(toIndex, 0, moved)
      return next
    })
    setDragging(null)
  }

  const resizeWidget = (widgetId: WidgetId, size: WidgetSize) => {
    setLayout(current => current.map(item => (item.id === widgetId ? { ...item, size } : item)))
  }

  // Extract display values with fallback chaining
  const balanceDisplay = summary?.wallet_balance ?? summary?.vit_balance ?? summary?.balance ?? '0.00'
  const winRateDisplay = summary?.accuracy_rate != null
    ? `${(summary.accuracy_rate * 100).toFixed(1)}%`
    : summary?.win_rate != null
      ? `${(summary.win_rate * 100).toFixed(1)}%`
      : '0.0%'
  const predictionsDisplay = summary?.total_predictions ?? summary?.predictions_made ?? 0

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/8 bg-surface-900/70 p-4 backdrop-blur-xl">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-vit-300">Personal workspace</p>
            <h2 className="text-xl font-semibold text-white">Your OS, tailored for action</h2>
            <p className="mt-1 text-sm text-white/45">
              Drag widgets to reorder them, resize them, and keep your most useful workspace actions in view.
            </p>
          </div>
          <div className="rounded-full border border-white/8 bg-white/5 px-3 py-1.5 text-xs font-medium text-white/50">
            {layout.length} widgets • saved to this browser
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {layout.map(widget => {
          const widgetId = widget.id
          const size = widget.size

          if (widgetId === 'overview') {
            return (
              <WidgetCard
                key={widgetId}
                id={widgetId}
                title="Workspace overview"
                subtitle="A concise snapshot of your current state"
                size={size}
                onResize={(next) => resizeWidget(widgetId, next)}
                onDragStart={setDragging}
                onDrop={reorderWidget}
                dragging={dragging === widgetId}
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <p className="text-xs uppercase tracking-wide text-white/30">Balance</p>
                    <p className="mt-2 text-2xl font-semibold text-white">{balanceDisplay}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <p className="text-xs uppercase tracking-wide text-white/30">Win rate</p>
                    <p className="mt-2 text-2xl font-semibold text-white">{winRateDisplay}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <p className="text-xs uppercase tracking-wide text-white/30">Predictions</p>
                    <p className="mt-2 text-2xl font-semibold text-white">{predictionsDisplay}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <p className="text-xs uppercase tracking-wide text-white/30">Role</p>
                    <p className="mt-2 text-lg font-semibold text-white">{user?.role ?? 'member'}</p>
                  </div>
                </div>
              </WidgetCard>
            )
          }

          if (widgetId === 'recommendations') {
            return (
              <WidgetCard
                key={widgetId}
                id={widgetId}
                title="AI recommendations"
                subtitle="Suggested next actions aligned to your activity"
                size={size}
                onResize={(next) => resizeWidget(widgetId, next)}
                onDragStart={setDragging}
                onDrop={reorderWidget}
                dragging={dragging === widgetId}
              >
                <div className="space-y-2">
                  {recommendations.map(item => (
                    <Link key={item.id} to={item.action} className="flex items-start gap-3 rounded-xl border border-white/8 bg-surface-900/50 p-3 transition-colors hover:border-vit-500/30 hover:bg-vit-500/10">
                      <div className="mt-0.5 rounded-lg bg-vit-500/15 p-2 text-vit-300">
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-white">{item.title}</p>
                          <span className="text-[10px] uppercase tracking-wide text-white/35">{item.difficulty}</span>
                        </div>
                        <p className="mt-1 text-xs text-white/45">{item.reason}</p>
                        <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-white/35">
                          <span className="rounded-full bg-white/5 px-2 py-1">Benefit: {item.benefit}</span>
                          <span className="rounded-full bg-white/5 px-2 py-1">Reward: {item.reward}</span>
                        </div>
                      </div>
                      <ChevronRight className="mt-1 h-4 w-4 text-white/20" />
                    </Link>
                  ))}
                </div>
              </WidgetCard>
            )
          }

          if (widgetId === 'notifications') {
            return (
              <WidgetCard
                key={widgetId}
                id={widgetId}
                title="Notification stream"
                subtitle="Latest updates and alerts"
                size={size}
                onResize={(next) => resizeWidget(widgetId, next)}
                onDragStart={setDragging}
                onDrop={reorderWidget}
                dragging={dragging === widgetId}
              >
                <div className="space-y-2">
                  {notifications.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-white/8 bg-surface-900/40 p-3 text-sm text-white/40">
                      No new notifications yet.
                    </div>
                  ) : notifications.map(item => (
                    <div key={item.id} className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-white">{item.title}</p>
                          <p className="mt-1 text-xs text-white/40">{item.body}</p>
                        </div>
                        {!item.read && <span className="mt-1 h-2.5 w-2.5 rounded-full bg-vit-400" />}
                      </div>
                    </div>
                  ))}
                </div>
              </WidgetCard>
            )
          }

          if (widgetId === 'status') {
            return (
              <WidgetCard
                key={widgetId}
                id={widgetId}
                title="System status"
                subtitle="Service health and availability"
                size={size}
                onResize={(next) => resizeWidget(widgetId, next)}
                onDragStart={setDragging}
                onDrop={reorderWidget}
                dragging={dragging === widgetId}
              >
                <div className="space-y-3">
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-white">
                      <Activity className="h-4 w-4 text-vit-400" />
                      Gateway
                    </div>
                    <p className="mt-2 text-xs text-white/40">{gatewayHealth?.status ?? 'Checking…'}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-white">
                      <Cpu className="h-4 w-4 text-purple-400" />
                      AI
                    </div>
                    <p className="mt-2 text-xs text-white/40">{aiHealth?.status ?? 'Checking…'}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-surface-900/50 p-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-white">
                      <HardDrive className="h-4 w-4 text-emerald-400" />
                      Storage
                    </div>
                    <p className="mt-2 text-xs text-white/40">{storageHealth?.status ?? 'Checking…'}</p>
                  </div>
                </div>
              </WidgetCard>
            )
          }

          if (widgetId === 'activity') {
            return (
              <WidgetCard
                key={widgetId}
                id={widgetId}
                title="Recent activity"
                subtitle="Your latest actions and platform events"
                size={size}
                onResize={(next) => resizeWidget(widgetId, next)}
                onDragStart={setDragging}
                onDrop={reorderWidget}
                dragging={dragging === widgetId}
              >
                <div className="space-y-2">
                  {recentActivity.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-white/8 bg-surface-900/40 p-3 text-sm text-white/40">No recent activity yet.</div>
                  ) : recentActivity.slice(0, 6).map((item: any, index: number) => (
                    <div key={index} className="flex items-start gap-3 rounded-xl border border-white/8 bg-surface-900/50 p-3">
                      <div className="mt-1 h-2.5 w-2.5 rounded-full bg-vit-400" />
                      <div className="flex-1">
                        <p className="text-sm text-white">{item.description || item.action || item.type || 'Activity'}</p>
                        {item.created_at && <p className="mt-1 text-xs text-white/35">{new Date(item.created_at).toLocaleString()}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </WidgetCard>
            )
          }

          return (
            <WidgetCard
              key={widgetId}
              id={widgetId}
              title="Workspace shortcuts"
              subtitle="Jump directly to your most-used workspaces"
              size={size}
              onResize={(next) => resizeWidget(widgetId, next)}
              onDragStart={setDragging}
              onDrop={reorderWidget}
              dragging={dragging === widgetId}
            >
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  { label: 'AI', path: '/ai', icon: Brain },
                  { label: 'Wallet', path: '/wallet', icon: Wallet },
                  { label: 'Storage', path: '/storage', icon: HardDrive },
                  { label: 'Chain', path: '/chain', icon: Layers },
                ].map(link => (
                  <Link key={link.path} to={link.path} className="flex items-center gap-2 rounded-xl border border-white/8 bg-surface-900/50 p-3 text-sm text-white/70 transition-colors hover:border-vit-500/30 hover:text-white">
                    <link.icon className="h-4 w-4 text-vit-400" />
                    {link.label}
                  </Link>
                ))}
              </div>
            </WidgetCard>
          )
        })}
      </div>

      <div className="rounded-2xl border border-white/8 bg-surface-900/70 p-4 backdrop-blur-xl">
        <div className="flex items-center gap-2 text-sm font-medium text-white/70">
          <Rocket className="h-4 w-4 text-vit-400" />
          The shell now behaves like an operating environment with reusable workspace widgets, saved preferences, and rapid access paths.
        </div>
      </div>
    </div>
  )
}
