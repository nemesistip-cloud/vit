import { useEffect, useMemo, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getStoredUser } from '@/hooks/useAuth'
import { getNavigationGroups, isNavigationItemActive } from '@/lib/navigation'
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'

interface SidebarProps {
  open: boolean
  onClose: () => void
  isAuthenticated: boolean
}

function NavigationGroups({
  isAuthenticated,
  isAdmin,
  collapsed = false,
  onNavigate,
}: {
  isAuthenticated: boolean
  isAdmin: boolean
  collapsed?: boolean
  onNavigate?: () => void
}) {
  const { pathname } = useLocation()
  const groups = useMemo(() => getNavigationGroups(isAuthenticated, isAdmin), [isAuthenticated, isAdmin])

  return (
    <>
      {groups.map((group) => (
        <section key={group.label} aria-label={group.label}>
          {!collapsed && (
            <h2 className={cn(
              'px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider truncate',
              group.label === 'Administration' ? 'text-vit-400/70' : 'text-white/35',
            )}>
              {group.label}
            </h2>
          )}
          <ul className="space-y-1 px-2">
            {group.items.map((item) => {
              const active = isNavigationItemActive(pathname, item.path)
              const Icon = item.icon
              return (
                <li key={item.id}>
                  <Link
                    to={item.path}
                    onClick={onNavigate}
                    aria-current={active ? 'page' : undefined}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      'flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400',
                      active
                        ? 'bg-vit-500/15 text-vit-300'
                        : item.audience === 'admin'
                          ? 'text-vit-300/75 hover:bg-vit-500/10 hover:text-vit-200'
                          : 'text-white/60 hover:bg-white/5 hover:text-white',
                      collapsed && 'justify-center px-2',
                    )}
                  >
                    <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </>
  )
}

export function Sidebar({ open, onClose, isAuthenticated }: SidebarProps) {
  const pathname = useLocation().pathname
  const workspaceState = useWorkspaceStore()
  const user = isAuthenticated ? getStoredUser() : null
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const collapsed = workspaceState.sidebar.collapsed
  const reducedMotion = useReducedMotion()
  const drawerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!open) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    drawerRef.current?.querySelector<HTMLElement>('a[href]')?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !drawerRef.current) return
      const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled])',
      )
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
      document.getElementById('mobile-navigation-trigger')?.focus()
    }
  }, [open, onClose])

  useEffect(() => {
    onClose()
  }, [pathname, onClose])

  return (
    <>
      {isAuthenticated && (
        <motion.aside
          initial={false}
          animate={{ width: collapsed ? 56 : 220 }}
          transition={reducedMotion ? { duration: 0 } : { duration: 0.2, ease: 'easeInOut' }}
          aria-label="Workspace sidebar"
          className="fixed bottom-0 left-0 top-16 z-30 hidden flex-col overflow-hidden border-r border-white/8 bg-surface-900/95 backdrop-blur-xl lg:flex"
        >
          <button
            type="button"
            onClick={() => workspaceStoreInstance.setSidebarState({ collapsed: !collapsed })}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
            className="absolute right-1 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-surface-800 text-white/55 transition-colors hover:border-white/20 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
          >
            {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
          <nav aria-label="Sidebar navigation" className="flex-1 space-y-5 overflow-y-auto overflow-x-hidden py-5">
            <NavigationGroups
              isAuthenticated
              isAdmin={isAdmin}
              collapsed={collapsed}
            />
          </nav>
        </motion.aside>
      )}

      <AnimatePresence>
        {open && (
          <>
            <motion.button
              type="button"
              aria-label="Close navigation menu"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: reducedMotion ? 0 : 0.15 }}
              onClick={onClose}
              tabIndex={-1}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            />
            <motion.aside
              ref={drawerRef}
              id="mobile-navigation"
              role="dialog"
              aria-modal="true"
              aria-label="Mobile navigation"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ duration: reducedMotion ? 0 : 0.2, ease: 'easeOut' }}
              className="fixed bottom-0 left-0 top-16 z-50 flex w-full max-w-sm flex-col border-r border-white/10 bg-surface-900 shadow-2xl shadow-black/40 lg:hidden"
            >
              <div className="border-b border-white/8 px-5 py-4">
                <p className="text-sm font-semibold text-white">Navigation</p>
                <p className="mt-1 text-xs text-white/40">
                  {isAuthenticated ? 'Network, products, and account' : 'Explore VIT Network'}
                </p>
              </div>
              <nav
                aria-label="Mobile navigation"
                className="flex-1 space-y-5 overflow-y-auto overscroll-contain px-2 py-4"
              >
                <NavigationGroups
                  isAuthenticated={isAuthenticated}
                  isAdmin={isAdmin}
                  onNavigate={onClose}
                />
              </nav>
              {!isAuthenticated && (
                <div className="border-t border-white/8 p-4">
                  <Link
                    to="/login"
                    onClick={onClose}
                    className="flex min-h-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
                  >
                    Sign in
                  </Link>
                </div>
              )}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
