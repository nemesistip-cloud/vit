import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Menu, X, LogIn, LogOut, LayoutDashboard, Shield, Wallet,
  Brain, ChevronDown, Vote, Landmark, Store, Share2, Users,
  Coins, Radio, BarChart3, Building2, Search, Smartphone, Activity,
  Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useGatewayHealth } from '@/hooks/useHealth'
import { getAuthToken, getStoredUser, clearAuth } from '@/hooks/useAuth'
import { NotificationBell } from '@/components/ui/NotificationBell'
import { WorkspaceSwitcher } from '@/components/shell/WorkspaceSwitcher'
import { ActivityFeedPanel } from '@/components/shell/ActivityFeed'

const PUBLIC_LINKS = [
  { label: 'Matches',     path: '/matches'     },
  { label: 'AI',          path: '/ai'          },
  { label: 'Governance',  path: '/governance'  },
  { label: 'Marketplace', path: '/marketplace' },
  { label: 'Leaderboard', path: '/leaderboard' },
  { label: 'Explorer',    path: '/chain'       },
  { label: 'Docs',        path: '/docs'        },
]

const AUTH_LINKS = [
  { label: 'Dashboard',   path: '/dashboard',        icon: LayoutDashboard },
  { label: 'Predictions', path: '/predictions',      icon: Brain           },
  { label: 'Wallet',      path: '/wallet',           icon: Wallet          },
  { label: 'Governance',  path: '/governance',       icon: Vote            },
  { label: 'Treasury',    path: '/treasury',         icon: Landmark        },
  { label: 'Marketplace', path: '/marketplace',      icon: Store           },
  { label: 'Referral',    path: '/referral',         icon: Share2          },
  { label: 'Ecosystem',   path: '/ecosystem',        icon: Smartphone      },
  { label: 'Social',      path: '/social',           icon: Users           },
  { label: 'DeFi',        path: '/defi',             icon: Coins           },
  { label: 'In-Play',     path: '/inplay',           icon: Radio           },
  { label: 'Analytics',   path: '/analytics-studio', icon: BarChart3       },
  { label: 'Enterprise',  path: '/enterprise',       icon: Building2       },
]

export function Navbar({ onOpenSearch }: { onOpenSearch?: () => void }) {
  const [open, setOpen]                 = useState(false)
  const [scrolled, setScrolled]         = useState(false)
  const [isLoggedIn, setIsLoggedIn]     = useState(false)
  const [isAdmin, setIsAdmin]           = useState(false)
  const [userDropOpen, setUserDropOpen] = useState(false)
  const [activityOpen, setActivityOpen] = useState(false)
  const location                        = useLocation()
  const navigate                        = useNavigate()
  const { data: health }               = useGatewayHealth()

  useEffect(() => {
    const token = getAuthToken()
    const user  = getStoredUser()
    setIsLoggedIn(!!token)
    setIsAdmin(user?.role === 'admin')
  }, [location.pathname])

  // Sync auth state when localStorage changes in another tab (logout/login).
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === 'vit_token' || e.key === 'vit_user' || e.key === null) {
        const token = getAuthToken()
        const user  = getStoredUser()
        setIsLoggedIn(!!token)
        setIsAdmin(user?.role === 'admin')
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  useEffect(() => { setOpen(false); setUserDropOpen(false) }, [location.pathname])

  function logout() {
    clearAuth()
    setIsLoggedIn(false)
    setIsAdmin(false)
    navigate('/')
  }

  const storedUser = getStoredUser()
  const initials   = storedUser?.username?.slice(0, 2).toUpperCase() ?? 'VT'
  const isOnline   = health?.status === 'ok' || health?.status === 'healthy'

  return (
    <>
      <ActivityFeedPanel open={activityOpen} onClose={() => setActivityOpen(false)} />

      <header
        className={cn(
          'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
          scrolled
            ? 'bg-surface-900/92 backdrop-blur-xl border-b border-white/8 shadow-xl shadow-black/25'
            : 'bg-transparent',
        )}
      >
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">

          {/* ── Logo ────────────────────────────────────────────────────── */}
          <Link to="/" className="flex items-center gap-2.5 group shrink-0">
            <div className="relative">
              <img
                src="/logo.png"
                alt="VIT Network"
                className="w-8 h-8 rounded-lg object-cover shadow-lg shadow-vit-500/20 group-hover:shadow-vit-500/40 transition-shadow"
              />
              {isOnline && (
                <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 border-2 border-surface-900" />
              )}
            </div>
            <span className="font-bold text-white text-sm tracking-tight hidden sm:block">
              VIT <span className="text-vit-400">Network</span>
            </span>
          </Link>

          {/* ── Workspace Switcher (authenticated) ──────────────────────── */}
          {isLoggedIn && (
            <div className="hidden md:block">
              <WorkspaceSwitcher />
            </div>
          )}

          {/* ── Desktop nav links ──────────────────────────────────────── */}
          <div className="hidden lg:flex items-center gap-1 flex-1 justify-center">
            {(isLoggedIn ? AUTH_LINKS.slice(0, 4) : PUBLIC_LINKS).map(link => {
              const active = location.pathname === link.path
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={cn(
                    'relative px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    active ? 'text-white' : 'text-white/50 hover:text-white hover:bg-white/5',
                  )}
                >
                  {link.label}
                  {active && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-lg bg-white/8 -z-10"
                      transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                    />
                  )}
                </Link>
              )
            })}
          </div>

          {/* ── Right controls ────────────────────────────────────────── */}
          <div className="flex items-center gap-1.5">

            {/* Search */}
            <button
              onClick={onOpenSearch}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/8 text-white/35 hover:text-white/60 hover:bg-white/8 text-xs transition-all"
            >
              <Search className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Search</span>
              <kbd className="hidden md:inline ml-1 px-1.5 py-0.5 rounded bg-white/8 text-white/25 text-[10px] font-mono">⌘K</kbd>
            </button>

            {/* Activity Feed */}
            {isLoggedIn && (
              <button
                onClick={() => setActivityOpen(v => !v)}
                className={cn(
                  'p-2 rounded-lg transition-colors',
                  activityOpen ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white hover:bg-white/8',
                )}
                title="Activity Feed"
              >
                <Activity className="w-4 h-4" />
              </button>
            )}

            {isLoggedIn && <NotificationBell />}

            {/* Auth */}
            {isLoggedIn ? (
              <div className="relative">
                <button
                  onClick={() => setUserDropOpen(v => !v)}
                  className="flex items-center gap-2 pl-1 pr-2.5 py-1 rounded-xl bg-white/6 border border-white/8 hover:bg-white/10 transition-all"
                >
                  <div className="w-7 h-7 rounded-lg bg-vit-600/30 border border-vit-500/30 flex items-center justify-center">
                    <span className="text-vit-300 text-[10px] font-bold">{initials}</span>
                  </div>
                  <span className="text-white/70 text-sm font-medium hidden sm:block max-w-[80px] truncate">
                    {storedUser?.username}
                  </span>
                  <ChevronDown className={cn('w-3.5 h-3.5 text-white/30 transition-transform', userDropOpen && 'rotate-180')} />
                </button>

                <AnimatePresence>
                  {userDropOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setUserDropOpen(false)} />
                      <motion.div
                        initial={{ opacity: 0, y: 4, scale: 0.97 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 4, scale: 0.97 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 top-full mt-2 w-52 bg-surface-800 border border-white/10 rounded-xl shadow-2xl shadow-black/40 overflow-hidden z-50"
                      >
                        {/* User info */}
                        <div className="px-4 py-3 border-b border-white/8">
                          <p className="text-sm font-semibold text-white truncate">{storedUser?.username}</p>
                          <p className="text-xs text-white/35 capitalize mt-0.5">{storedUser?.role ?? 'viewer'}</p>
                        </div>

                        {[
                          { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
                          { label: 'Wallet',    path: '/wallet',    icon: Wallet          },
                          { label: 'Settings',  path: '/settings',  icon: Settings        },
                          { label: 'Activity',  path: null,         icon: Activity        },
                        ].map(item => (
                          item.path ? (
                            <Link key={item.path} to={item.path}
                              className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors">
                              <item.icon className="w-4 h-4" /> {item.label}
                            </Link>
                          ) : (
                            <button key={item.label}
                              onClick={() => { setUserDropOpen(false); setActivityOpen(v => !v) }}
                              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors">
                              <item.icon className="w-4 h-4" /> {item.label}
                            </button>
                          )
                        ))}

                        {isAdmin && (
                          <Link to="/admin" className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-vit-400 hover:bg-vit-500/8 transition-colors">
                            <Shield className="w-4 h-4" /> Admin Panel
                          </Link>
                        )}

                        <div className="border-t border-white/8">
                          <button onClick={logout}
                            className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/8 transition-colors">
                            <LogOut className="w-4 h-4" /> Sign Out
                          </button>
                        </div>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login"
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white/55 border border-white/10 hover:bg-white/5 transition-colors">
                  <LogIn className="w-3.5 h-3.5" /> Sign In
                </Link>
                <Link to="/login"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold bg-vit-600 hover:bg-vit-500 text-white transition-colors">
                  Get Started
                </Link>
              </div>
            )}

            {/* Mobile menu */}
            <button
              onClick={() => setOpen(o => !o)}
              className="lg:hidden p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/8 transition-colors"
            >
              {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </nav>

        {/* ── Mobile menu ───────────────────────────────────────────────── */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="lg:hidden border-t border-white/8 bg-surface-900/98 backdrop-blur-xl overflow-hidden"
            >
              <div className="px-4 py-4 space-y-1 max-h-[75vh] overflow-y-auto">
                {/* Workspace switcher in mobile */}
                {isLoggedIn && (
                  <div className="pb-3 mb-3 border-b border-white/8">
                    <WorkspaceSwitcher mobile />
                  </div>
                )}

                {(isLoggedIn ? AUTH_LINKS : PUBLIC_LINKS.map(l => ({ ...l, icon: Activity }))).map(link => (
                  <Link key={link.path} to={link.path}
                    className={cn('flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors',
                      location.pathname === link.path ? 'text-white bg-white/8' : 'text-white/55 hover:text-white hover:bg-white/5')}>
                    {'icon' in link && link.icon && <link.icon className="w-4 h-4 shrink-0" />}
                    {link.label}
                  </Link>
                ))}

                {isAdmin && (
                  <Link to="/admin" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-vit-400 hover:bg-vit-500/10 transition-colors">
                    <Shield className="w-4 h-4" /> Admin Panel
                  </Link>
                )}

                <div className="pt-3 border-t border-white/8">
                  {isLoggedIn ? (
                    <button onClick={logout}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/8 transition-colors">
                      <LogOut className="w-4 h-4" /> Sign Out
                    </button>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <Link to="/login"
                        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white/65 border border-white/10 hover:bg-white/5 transition-colors">
                        <LogIn className="w-4 h-4" /> Sign In
                      </Link>
                      <Link to="/login"
                        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-vit-600 hover:bg-vit-500 text-white transition-colors">
                        Get Started
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>
    </>
  )
}
