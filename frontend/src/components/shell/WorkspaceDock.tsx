import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Brain, Home, MoreHorizontal, Settings, Shield, Sparkles, Trophy, Wallet, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getStoredUser } from '@/hooks/useAuth'
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'
import { getPinnedApps } from '@/lib/appRegistry'

export function WorkspaceDock() {
  const { pathname } = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  const workspaceState = useWorkspaceStore()
  const user = getStoredUser()
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const registryItems = getPinnedApps().map((app) => ({
    label: app.name,
    path: app.route,
    icon: app.icon,
    hint: app.description,
  }))
  const orderedItems = [...registryItems].sort((a, b) => {
    const order = workspaceState.dock.order
    const indexA = order.indexOf(a.path)
    const indexB = order.indexOf(b.path)
    if (indexA === -1 && indexB === -1) return 0
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-40 flex justify-center px-4">
      <motion.nav
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="pointer-events-auto hidden flex-wrap items-center justify-center gap-2 rounded-full border border-white/10 bg-surface-900/85 px-2 py-2 shadow-2xl shadow-black/40 backdrop-blur-xl lg:flex"
      >
        {orderedItems.map(({ label, path, icon: Icon, hint }) => {
          const active = pathname === path || pathname.startsWith(`${path}/`)
          return (
            <Link
              key={path}
              to={path}
              onClick={() => {
                const nextOrder = [path, ...workspaceState.dock.order.filter(item => item !== path)]
                workspaceStoreInstance.setDockState({
                  order: nextOrder,
                  pinned: [...new Set([...workspaceState.dock.pinned, path])],
                  favorites: [...new Set([path, ...workspaceState.dock.favorites])],
                })
              }}
              className={cn(
                'group flex items-center gap-2 rounded-full px-3 py-2 text-sm transition-all',
                active
                  ? 'bg-vit-500/15 text-vit-300 shadow-[0_0_0_1px_rgba(255,255,255,0.08)]'
                  : 'text-white/60 hover:bg-white/5 hover:text-white',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">{label}</span>
              <span className="hidden rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-white/40 sm:inline">
                {hint}
              </span>
            </Link>
          )
        })}
        <Link
          to="/assistant"
          className="ml-1 flex items-center gap-2 rounded-full border border-vit-500/20 bg-vit-500/10 px-3 py-2 text-sm font-medium text-vit-300 transition-colors hover:bg-vit-500/20"
        >
          <Sparkles className="h-4 w-4" />
          <span className="hidden sm:inline">Ask AI</span>
        </Link>
      </motion.nav>
      <motion.nav
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="pointer-events-auto relative flex w-full max-w-md items-center justify-around rounded-2xl border border-white/10 bg-surface-900/95 px-2 py-2 shadow-2xl shadow-black/50 backdrop-blur-xl lg:hidden"
      >
        {[
          { label: 'Home', path: '/dashboard', icon: Home },
          { label: 'Matches', path: '/matches', icon: Trophy },
          { label: 'AI', path: '/assistant', icon: Brain },
          { label: 'Wallet', path: '/wallet', icon: Wallet },
        ].map(({ label, path, icon: Icon }) => {
          const active = pathname === path || pathname.startsWith(`${path}/`)
          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-medium transition-colors',
                active ? 'bg-vit-500/15 text-vit-300' : 'text-white/45 hover:bg-white/5 hover:text-white',
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          )
        })}
        <button
          type="button"
          onClick={() => setMoreOpen(value => !value)}
          className={cn(
            'flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-medium transition-colors',
            moreOpen ? 'bg-white/10 text-white' : 'text-white/45 hover:bg-white/5 hover:text-white',
          )}
          aria-label="Open more navigation"
        >
          {moreOpen ? <X className="h-4 w-4" /> : <MoreHorizontal className="h-4 w-4" />}
          More
        </button>
        {moreOpen && (
          <div className="absolute bottom-full right-0 mb-2 w-52 rounded-2xl border border-white/10 bg-surface-800/98 p-2 shadow-2xl shadow-black/50">
            {[
              { label: 'Explorer', path: '/chain', icon: Sparkles },
              { label: 'Governance', path: '/governance', icon: Shield },
              { label: 'Settings', path: '/settings', icon: Settings },
              ...(isAdmin ? [{ label: 'Admin Control', path: '/admin', icon: Shield }] : []),
            ].map(({ label, path, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                onClick={() => setMoreOpen(false)}
                className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/60 transition-colors hover:bg-white/5 hover:text-white"
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </div>
        )}
      </motion.nav>
    </div>
  )
}
