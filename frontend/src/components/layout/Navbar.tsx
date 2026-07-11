import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, Activity, LogIn, LogOut, LayoutDashboard, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useGatewayHealth } from '@/hooks/useHealth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { getAuthToken, getStoredUser, clearAuth } from '@/hooks/useAuth'

const NAV_LINKS = [
  { label: 'Platform',   path: '/platform' },
  { label: 'AI',         path: '/ai' },
  { label: 'Storage',    path: '/storage' },
  { label: 'Matches',    path: '/matches' },
  { label: 'Status',     path: '/status' },
  { label: 'Developers', path: '/developers' },
  { label: 'Docs',       path: '/docs' },
]

export function Navbar() {
  const [open, setOpen]       = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isAdmin, setIsAdmin]   = useState(false)
  const location              = useLocation()
  const navigate              = useNavigate()
  const { data: health }      = useGatewayHealth()

  // Sync auth state on every navigation
  useEffect(() => {
    const token = getAuthToken()
    const user  = getStoredUser()
    setIsLoggedIn(!!token)
    setIsAdmin(user?.role === 'admin')
  }, [location.pathname])

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handler)
    return () => window.removeEventListener('scroll', handler)
  }, [])

  useEffect(() => setOpen(false), [location.pathname])

  function logout() {
    clearAuth()
    setIsLoggedIn(false)
    setIsAdmin(false)
    navigate('/')
  }

  const visibleLinks = isAdmin
    ? [...NAV_LINKS, { label: 'Admin', path: '/admin' }]
    : NAV_LINKS

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-surface-900/90 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/20'
          : 'bg-transparent',
      )}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-vit-500 to-vit-700 flex items-center justify-center shadow-lg shadow-vit-500/30 group-hover:shadow-vit-500/50 transition-shadow">
            <span className="text-white font-bold text-sm">V</span>
          </div>
          <span className="font-bold text-lg tracking-tight text-white">
            VIT <span className="text-vit-400">Network</span>
          </span>
        </Link>

        {/* Desktop nav links */}
        <div className="hidden lg:flex items-center gap-0.5">
          {visibleLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                location.pathname === link.path
                  ? 'text-white bg-white/10'
                  : 'text-white/60 hover:text-white hover:bg-white/5',
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Right side */}
        <div className="hidden md:flex items-center gap-3 shrink-0">
          {/* Status badge */}
          <Link
            to="/status"
            className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors"
          >
            <Activity className="w-3.5 h-3.5" />
            <StatusBadge status={health?.status} size="sm" pulse />
          </Link>

          {isLoggedIn ? (
            <div className="flex items-center gap-2">
              {isAdmin && (
                <Link
                  to="/admin"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 text-sm font-medium border border-yellow-500/20 transition-colors"
                >
                  <Shield className="w-3.5 h-3.5" />
                  Admin
                </Link>
              )}
              <Link
                to="/dashboard"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 border border-white/10 text-white text-sm font-medium transition-colors"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                Dashboard
              </Link>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 hover:border-white/25 text-white/70 hover:text-white text-sm font-medium transition-colors"
              >
                <LogIn className="w-3.5 h-3.5" />
                Sign In
              </Link>
              <Link
                to="/login"
                className="px-4 py-1.5 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors shadow-lg shadow-vit-600/25"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setOpen(!open)}
          className="md:hidden p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-surface-800/95 backdrop-blur-xl border-b border-white/10"
          >
            <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-1">
              {visibleLinks.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={cn(
                    'px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    location.pathname === link.path
                      ? 'text-white bg-white/10'
                      : 'text-white/60 hover:text-white hover:bg-white/5',
                  )}
                >
                  {link.label}
                </Link>
              ))}
              <div className="mt-3 pt-3 border-t border-white/10 flex flex-col gap-2">
                {isLoggedIn ? (
                  <>
                    <Link to="/dashboard" className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-700 text-white text-sm font-medium">
                      <LayoutDashboard className="w-4 h-4" /> Dashboard
                    </Link>
                    <button onClick={logout} className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-white/50 text-sm">
                      <LogOut className="w-4 h-4" /> Sign out
                    </button>
                  </>
                ) : (
                  <Link to="/login" className="block w-full px-4 py-2.5 rounded-lg bg-vit-600 text-white text-sm font-medium text-center">
                    Get Started
                  </Link>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
