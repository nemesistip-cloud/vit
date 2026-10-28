import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Activity,
  ChevronDown,
  LogIn,
  LogOut,
  Menu,
  Search,
  Settings,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useGatewayHealth } from '@/hooks/useHealth'
import { clearAuth, getAuthToken, getStoredUser } from '@/hooks/useAuth'
import { NotificationBell } from '@/components/ui/NotificationBell'
import { ActivityFeedPanel } from '@/components/shell/ActivityFeed'
import { ApplicationSwitcher } from '@/components/shell/ApplicationSwitcher'
import { PUBLIC_NAVIGATION_GROUPS } from '@/lib/navigation'

interface NavbarProps {
  onOpenSearch: () => void
  navigationOpen: boolean
  onToggleNavigation: () => void
  showPublicNavigation?: boolean
}

export function Navbar({
  onOpenSearch,
  navigationOpen,
  onToggleNavigation,
  showPublicNavigation = false,
}: NavbarProps) {
  const [scrolled, setScrolled] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [storedUser, setStoredUser] = useState(getStoredUser)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [activityOpen, setActivityOpen] = useState(false)
  const accountMenuRef = useRef<HTMLDivElement>(null)
  const accountTriggerRef = useRef<HTMLButtonElement>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const { data: health } = useGatewayHealth()

  useEffect(() => {
    function syncAuthState() {
      setIsLoggedIn(Boolean(getAuthToken()))
      setStoredUser(getStoredUser())
    }

    function onStorage(event: StorageEvent) {
      if (event.key === 'vit_token' || event.key === 'vit_user' || event.key === null) {
        syncAuthState()
      }
    }

    syncAuthState()
    window.addEventListener('storage', onStorage)
    window.addEventListener('vit-auth-change', syncAuthState)
    return () => {
      window.removeEventListener('storage', onStorage)
      window.removeEventListener('vit-auth-change', syncAuthState)
    }
  }, [location.pathname])

  useEffect(() => {
    function handler() {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  useEffect(() => {
    setUserMenuOpen(false)
    setActivityOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!userMenuOpen) return

    function handlePointerDown(event: PointerEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setUserMenuOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setUserMenuOpen(false)
        accountTriggerRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [userMenuOpen])

  function logout() {
    clearAuth()
    setIsLoggedIn(false)
    setUserMenuOpen(false)
    navigate('/')
  }

  const initials = storedUser?.username?.slice(0, 2).toUpperCase() ?? 'VT'
  const isOnline = health?.status === 'ok' || health?.status === 'healthy'
  const isDegraded = health?.status === 'degraded'

  return (
    <>
      <ActivityFeedPanel open={activityOpen} onClose={() => setActivityOpen(false)} />

      <header
        className={cn(
          'fixed left-0 right-0 top-0 z-50 transition-colors duration-200',
          scrolled
            ? 'border-b border-white/10 bg-surface-900/95 shadow-lg shadow-black/20 backdrop-blur-xl'
            : 'bg-surface-900/70 backdrop-blur-md',
        )}
      >
        <nav
          aria-label="Primary navigation"
          className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6"
        >
          <Link
            to="/"
            aria-label="VIT Network home"
            className="group flex shrink-0 items-center gap-2.5 rounded-xl border border-white/8 bg-white/5 px-2 py-1.5 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
          >
            <img
              src="/logo.png"
              alt=""
              className="h-8 w-8 rounded-lg object-cover"
            />
            <span className="hidden text-sm font-semibold tracking-tight text-white sm:block">
              VIT <span className="text-white/70">Network</span>
            </span>
          </Link>

          {showPublicNavigation && (
            <div className="hidden min-w-0 flex-1 items-center justify-center gap-1 xl:flex">
              {PUBLIC_NAVIGATION_GROUPS.flatMap((group) => group.items).map((item) => {
                const active = location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)
                return (
                  <Link
                    key={item.id}
                    to={item.path}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400',
                      active ? 'bg-white/10 text-white' : 'text-white/60 hover:bg-white/5 hover:text-white',
                    )}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </div>
          )}

          {isLoggedIn && (
            <div className="hidden shrink-0 md:block">
              <ApplicationSwitcher />
            </div>
          )}

          <div className="flex-1" />

          <div
            role="status"
            aria-live="polite"
            className={cn(
              'hidden whitespace-nowrap rounded-full border px-3 py-1.5 text-[10px] font-medium xl:inline-flex xl:items-center xl:gap-2',
              isOnline
                ? 'border-emerald-500/25 bg-emerald-500/8 text-emerald-300/90'
                : isDegraded
                  ? 'border-amber-500/25 bg-amber-500/8 text-amber-300/90'
                  : 'border-white/10 bg-white/5 text-white/50',
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                isOnline ? 'animate-pulse bg-emerald-400' : isDegraded ? 'bg-amber-400' : 'bg-white/35',
              )}
            />
            {isOnline
              ? 'All systems operational'
              : isDegraded
                ? 'Network degraded'
                : health
                  ? 'Network status unavailable'
                  : 'Checking network status'}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={onOpenSearch}
              aria-label="Search navigation"
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/8 bg-white/5 text-white/60 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400 sm:w-auto sm:gap-2 sm:px-3"
            >
              <Search aria-hidden="true" className="h-4 w-4" />
              <span className="hidden text-xs md:inline">Search</span>
              <kbd className="hidden rounded bg-white/8 px-1.5 py-0.5 font-mono text-[10px] text-white/30 md:inline">⌘K</kbd>
            </button>

            {isLoggedIn && (
              <>
                <button
                  type="button"
                  onClick={() => setActivityOpen((value) => !value)}
                  aria-label={activityOpen ? 'Close activity feed' : 'Open activity feed'}
                  aria-expanded={activityOpen}
                  className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400',
                    activityOpen ? 'bg-white/10 text-white' : 'text-white/55 hover:bg-white/8 hover:text-white',
                  )}
                >
                  <Activity aria-hidden="true" className="h-4 w-4" />
                </button>
                <NotificationBell />

                <div ref={accountMenuRef} className="relative">
                  <button
                    ref={accountTriggerRef}
                    type="button"
                    onClick={() => setUserMenuOpen((value) => !value)}
                    aria-label="Open account menu"
                    aria-expanded={userMenuOpen}
                    aria-controls="account-menu"
                    className="flex h-10 items-center gap-2 rounded-xl border border-white/8 bg-white/5 px-1.5 pr-2.5 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
                  >
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-vit-500/30 bg-vit-600/30 text-[10px] font-bold text-vit-200">
                      {initials}
                    </span>
                    <span className="hidden max-w-24 truncate text-sm font-medium text-white/75 sm:block">
                      {storedUser?.username ?? 'Account'}
                    </span>
                    <ChevronDown
                      aria-hidden="true"
                      className={cn('h-3.5 w-3.5 text-white/40 transition-transform', userMenuOpen && 'rotate-180')}
                    />
                  </button>

                  <AnimatePresence>
                    {userMenuOpen && (
                      <motion.div
                        id="account-menu"
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 4 }}
                        transition={{ duration: 0.12 }}
                        className="absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-xl border border-white/10 bg-surface-800 shadow-2xl shadow-black/40"
                      >
                        <div className="border-b border-white/8 px-4 py-3">
                          <p className="truncate text-sm font-semibold text-white">{storedUser?.username ?? 'Account'}</p>
                          <p className="mt-1 text-xs capitalize text-white/45">
                            {storedUser?.role ? `${storedUser.role} account` : 'Signed in'}
                          </p>
                        </div>
                        <Link
                          to="/settings"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex min-h-11 items-center gap-3 px-4 text-sm text-white/70 transition-colors hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
                        >
                          <Settings aria-hidden="true" className="h-4 w-4" />
                          Personal settings
                        </Link>
                        <button
                          type="button"
                          onClick={logout}
                          className="flex min-h-11 w-full items-center gap-3 border-t border-white/8 px-4 text-left text-sm text-red-300 transition-colors hover:bg-red-500/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                        >
                          <LogOut aria-hidden="true" className="h-4 w-4" />
                          Sign out
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </>
            )}

            {!isLoggedIn && (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="hidden min-h-10 items-center gap-1.5 rounded-xl border border-white/10 px-3 text-sm font-medium text-white/65 transition-colors hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400 lg:inline-flex"
                >
                  <LogIn aria-hidden="true" className="h-3.5 w-3.5" />
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="inline-flex min-h-10 items-center rounded-xl bg-vit-500 px-3 text-sm font-semibold text-white transition-colors hover:bg-vit-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-300"
                >
                  Get started
                </Link>
              </div>
            )}

            {(showPublicNavigation || !isLoggedIn) && (
              <button
                id="mobile-navigation-trigger"
                type="button"
                onClick={onToggleNavigation}
                aria-label={navigationOpen ? 'Close navigation menu' : 'Open navigation menu'}
                aria-expanded={navigationOpen}
                aria-controls="mobile-navigation"
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-xl text-white/65 transition-colors hover:bg-white/8 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400',
                  showPublicNavigation ? 'xl:hidden' : 'lg:hidden',
                )}
              >
                {navigationOpen
                  ? <X aria-hidden="true" className="h-5 w-5" />
                  : <Menu aria-hidden="true" className="h-5 w-5" />}
              </button>
            )}

            {isLoggedIn && !showPublicNavigation && (
              <button
                id="mobile-navigation-trigger"
                type="button"
                onClick={onToggleNavigation}
                aria-label={navigationOpen ? 'Close navigation menu' : 'Open navigation menu'}
                aria-expanded={navigationOpen}
                aria-controls="mobile-navigation"
                className="flex h-10 w-10 items-center justify-center rounded-xl text-white/65 transition-colors hover:bg-white/8 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400 lg:hidden"
              >
                {navigationOpen
                  ? <X aria-hidden="true" className="h-5 w-5" />
                  : <Menu aria-hidden="true" className="h-5 w-5" />}
              </button>
            )}
          </div>
        </nav>
      </header>
    </>
  )
}
