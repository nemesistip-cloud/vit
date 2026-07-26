import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Settings, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'
import { getPinnedApps } from '@/lib/appRegistry'

export function WorkspaceDock() {
  const { pathname } = useLocation()
  const workspaceState = useWorkspaceStore()
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
        className="pointer-events-auto flex flex-wrap items-center justify-center gap-2 rounded-full border border-white/10 bg-surface-900/85 px-2 py-2 shadow-2xl shadow-black/40 backdrop-blur-xl"
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
    </div>
  )
}
