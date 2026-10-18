import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Boxes, Home, MoreHorizontal, Settings, Shield, Sparkles, Wallet, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getStoredUser } from '@/hooks/useAuth'
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'
import { getPinnedApps } from '@/lib/appRegistry'

export function WorkspaceDock() {
  const { pathname } = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
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

  // Close popup menu on click outside
  useEffect(() => {
    if (!moreOpen) return
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMoreOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [moreOpen])

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center pb-3 px-3 sm:pb-4 sm:px-4 max-w-full overflow-x-hidden">
      {/* Desktop Navigation Dock */}
      <motion.nav
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        aria-label="Desktop workspace dock"
        className="pointer-events-auto hidden flex-wrap items-center justify-center gap-2 rounded-full border border-white/10 bg-surface-900/90 px-3 py-2 shadow-2xl shadow-black/50 backdrop-blur-xl lg:flex"
      >
        {orderedItems.map(({ label, path, icon: Icon, hint }) => {
          const active = pathname === path || (path !== '/' && pathname.startsWith(`${path}/`))
          return (
            <Link
              key={path}
              to={path}
              onClick={() => {
                const nextOrder = [path, ...workspaceState.dock.order.filter((item) => item !== path)]
                workspaceStoreInstance.setDockState({
                  order: nextOrder,
                  pinned: [...new Set([...workspaceState.dock.pinned, path])],
                  favorites: [...new Set([path, ...workspaceState.dock.favorites])],
                })
              }}
              className={cn(
                'group flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-all',
                active
                  ? 'bg-vit-500/20 text-vit-300 ring-1 ring-vit-500/40 shadow-sm'
                  : 'text-white/60 hover:bg-white/5 hover:text-white'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{label}</span>
              {hint && (
                <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] text-white/40 font-normal">
                  {hint}
                </span>
              )}
            </Link>
          )
        })}
        <Link
          to="/assistant"
          className="ml-1 flex items-center gap-2 rounded-full border border-vit-500/30 bg-vit-500/15 px-3.5 py-2 text-sm font-medium text-vit-300 transition-colors hover:bg-vit-500/25"
        >
          <Sparkles className="h-4 w-4" />
          <span>Ask AI</span>
        </Link>
      </motion.nav>

      {/* Mobile Navigation Dock */}
      <motion.nav
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        aria-label="Mobile bottom navigation"
        className="pointer-events-auto relative flex w-full max-w-sm sm:max-w-md items-center justify-around rounded-2xl border border-white/10 bg-surface-900/95 px-2 py-1.5 shadow-2xl shadow-black/60 backdrop-blur-xl lg:hidden"
      >
        {[
          { label: 'Network', path: '/dashboard', icon: Home },
          { label: 'Apps', path: '/applications', icon: Boxes },
          { label: 'AI', path: '/assistant', icon: Brain },
          { label: 'Wallet', path: '/wallet', icon: Wallet },
        ].map(({ label, path, icon: Icon }) => {
          const active = pathname === path || (path !== '/' && pathname.startsWith(`${path}/`))
          return (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex min-w-[56px] flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-medium transition-colors',
                active ? 'bg-vit-500/20 text-vit-300' : 'text-white/50 hover:bg-white/5 hover:text-white'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{label}</span>
            </Link>
          )
        })}
        <div ref={menuRef} className="relative">
          <button
            type="button"
            onClick={() => setMoreOpen((value) => !value)}
            className={cn(
              'flex min-w-[56px] flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-medium transition-colors',
              moreOpen ? 'bg-white/10 text-white' : 'text-white/50 hover:bg-white/5 hover:text-white'
            )}
            aria-label="Open more navigation links"
            aria-expanded={moreOpen}
          >
            {moreOpen ? <X className="h-4 w-4 shrink-0" /> : <MoreHorizontal className="h-4 w-4 shrink-0" />}
            <span>More</span>
          </button>
          <AnimatePresence>
            {moreOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 8 }}
                className="absolute bottom-full right-0 mb-3 w-52 rounded-2xl border border-white/10 bg-surface-800/98 p-2 shadow-2xl shadow-black/60 backdrop-blur-xl z-50"
              >
                {[
                  { label: 'Workspace', path: '/workspace', icon: Home },
                  { label: 'Explorer', path: '/chain', icon: Sparkles },
                  { label: 'Governance', path: '/governance', icon: Shield },
                  { label: 'Settings', path: '/settings', icon: Settings },
                  ...(isAdmin ? [{ label: 'Admin Control', path: '/admin', icon: Shield }] : []),
                ].map(({ label, path, icon: Icon }) => (
                  <Link
                    key={path}
                    to={path}
                    onClick={() => setMoreOpen(false)}
                    className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-white/70 transition-colors hover:bg-white/10 hover:text-white"
                  >
                    <Icon className="h-4 w-4 shrink-0 text-vit-400" />
                    <span>{label}</span>
                  </Link>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.nav>
    </div>
  )
}
