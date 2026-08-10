/**
 * Sidebar — persistent left-rail navigation for the authenticated app shell.
 * Complements the Navbar top bar and collapses to a rail on mobile.
 */
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Wallet, Vote, Landmark, Store,
  Share2, Coins, Radio, BarChart3, Shield, Settings,
  ChevronLeft, ChevronRight, Activity, Cpu, HardDrive,
  Layers, Trophy, Star, Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getAuthToken, getStoredUser } from '@/hooks/useAuth'
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'

interface NavItem {
  label: string
  path: string
  icon: React.ElementType
  badge?: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Workspace',
    items: [
      { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { label: 'Predictions', path: '/predictions', icon: Sparkles },
      { label: 'Matches', path: '/matches', icon: Trophy },
      { label: 'In-Play', path: '/inplay', icon: Radio, badge: 'LIVE' },
      { label: 'Wallet', path: '/wallet', icon: Wallet },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { label: 'AI Assistant', path: '/assistant', icon: Cpu },
      { label: 'Analytics Studio', path: '/analytics-studio', icon: BarChart3 },
      { label: 'Odds Compare', path: '/odds', icon: Star },
      { label: 'Backtest', path: '/backtest', icon: Layers },
    ],
  },
  {
    label: 'Ecosystem',
    items: [
      { label: 'Marketplace', path: '/marketplace', icon: Store },
      { label: 'Treasury', path: '/treasury', icon: Landmark },
      { label: 'DeFi', path: '/defi', icon: Coins },
      { label: 'Referral', path: '/referral', icon: Share2 },
      { label: 'Ecosystem', path: '/ecosystem', icon: Sparkles },
    ],
  },
  {
    label: 'Network',
    items: [
      { label: 'Chain Explorer', path: '/chain', icon: Layers },
      { label: 'Storage', path: '/storage', icon: HardDrive },
      { label: 'Validators', path: '/validators', icon: Shield },
      { label: 'Governance', path: '/governance', icon: Vote },
      { label: 'Status', path: '/status', icon: Activity },
    ],
  },
  {
    label: 'Account',
    items: [
      { label: 'Settings', path: '/settings', icon: Settings },
    ],
  },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const workspaceState = useWorkspaceStore()
  const { pathname } = useLocation()
  const isLoggedIn = !!getAuthToken()
  const user = getStoredUser()
  const collapsed = workspaceState.sidebar.collapsed

  if (!isLoggedIn) return null

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 56 : 220 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className={cn(
        'fixed left-0 top-16 bottom-0 z-30 flex flex-col border-r border-white/8 bg-surface-900/95 backdrop-blur-xl overflow-hidden hidden lg:flex',
        className,
      )}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => workspaceStoreInstance.setSidebarState({ collapsed: !workspaceState.sidebar.collapsed })}
        className="absolute top-3 right-0 translate-x-1/2 z-10 w-5 h-5 rounded-full bg-surface-800 border border-white/10 flex items-center justify-center text-white/40 hover:text-white hover:border-white/20 transition-colors"
      >
        {collapsed
          ? <ChevronRight className="w-3 h-3" />
          : <ChevronLeft  className="w-3 h-3" />}
      </button>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-4 space-y-4 scrollbar-thin">
        {NAV_GROUPS.map(group => (
          <div key={group.label}>
            {!collapsed && (
              <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-white/25 truncate">
                {group.label}
              </p>
            )}
            <ul className="space-y-0.5 px-2">
              {group.items.map(item => {
                const active = pathname === item.path || pathname.startsWith(item.path + '/')
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      onClick={() => workspaceStoreInstance.setSidebarState({ selectedPath: item.path })}
                      title={collapsed ? item.label : undefined}
                      className={cn(
                        'flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm font-medium transition-colors group relative',
                        active
                          ? 'bg-vit-500/15 text-vit-400'
                          : 'text-white/45 hover:text-white hover:bg-white/5',
                        collapsed && 'justify-center',
                      )}
                    >
                      <item.icon className="w-4 h-4 shrink-0" />
                      <AnimatePresence>
                        {!collapsed && (
                          <motion.span
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: 'auto' }}
                            exit={{ opacity: 0, width: 0 }}
                            transition={{ duration: 0.15 }}
                            className="truncate"
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                      {item.badge && !collapsed && (
                        <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 shrink-0">
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* User footer */}
      {!collapsed && user && (
        <div className="border-t border-white/8 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-vit-500/20 flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-vit-400">
                {(user.username || '?')[0].toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white/70 truncate">{user.username}</p>
              <p className="text-[10px] text-white/30 capitalize">{user.role ?? 'member'}</p>
            </div>
          </div>
        </div>
      )}
    </motion.aside>
  )
}
