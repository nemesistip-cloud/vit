import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, Activity, LogIn, LogOut, LayoutDashboard, Shield, Trophy, Wallet, Brain, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useGatewayHealth } from '@/hooks/useHealth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { getAuthToken, getStoredUser, clearAuth } from '@/hooks/useAuth'

// Public nav links
const PUBLIC_LINKS = [
  { label: 'Matches',    path: '/matches' },
  { label: 'AI',         path: '/ai' },
  { label: 'Leaderboard', path: '/leaderboard' },
  { label: 'Explorer',   path: '/chain' },
  { label: 'Platform',   path: '/platform' },
  { label: 'Docs',       path: '/docs' },
]

// Auth-only links
const AUTH_LINKS = [
  { label: 'Dashboard',   path: '/dashboard',   icon: LayoutDashboard },
  { label: 'Predictions', path: '/predictions', icon: Brain },
  { label: 'Wallet',      path: '/wallet',       icon: Wallet },
]

export function Navbar() {
  const [open, setOpen]         = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isAdmin, setIsAdmin]   = useState(false)
  const [userDropOpen, setUserDropOpen] = useState(false)
  const location                = useLocation()
  const navigate                = useNavigate()
  const { data: health }        = useGatewayHealth()

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

  useEffect(() => { setOpen(false); setUserDropOpen(false) }, [location.pathname])

  function logout() {
    clearAuth()
    setIsLoggedIn(false)
    setIsAdmin(false)
    navigate('/')
  }

  const storedUser = getStoredUser()

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
          <img
            src="/logo.png"
            alt="VIT Network"
            className="w-8 h-8 rounded-lg object-cover shadow-lg shadow-vit-500/20 group-hover:shadow-vit-500/40 transition-shadow"
          />
          <span className="font-bold text-lg tracking-tight text-white">
            VIT <span className="text-vit-400">Network</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden lg:flex items-center gap-0.5">
          {isLoggedIn && AUTH_LINKS.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                location.pathname === link.path
                  ? 'text-white bg-white/10'
                  : 'text-white/60 hover:text-white hover:bg-white/5',
              )}
            >
              <link.icon className="w-3.5 h-3.5" />
              {link.label}
            </Link>
          ))}
          <div className="w-px h-5 bg-white/10 mx-1" hidden={!isLoggedIn} />
          {PUBLIC_LINKS.map(link => (
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
          {isAdmin && (
            <Link
              to="/admin"
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                location.pathname === '/admin'
                  ? 'text-white bg-vit-500/20'
                  : 'text-vit-400 hover:text-vit-300 hover:bg-vit-500/10',
              )}
            >
              <Shield className="w-3.5 h-3.5" />
              Admin
            </Link>
          )}
        </div>

        {/* Right side */}
        <div className="hidden md:flex items-center gap-3 shrink-0">
          <Link to="/status" className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors">
            <Activity className="w-3.5 h-3.5" />
            <StatusBadge status={health?.status} size="sm" pulse />
          </Link>

          {isLoggedIn ? (
            <div className="relative">
              <button
                onClick={() => setUserDropOpen(v => !v)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-sm text-white"
              >
                <div className="w-6 h-6 rounded-full bg-vit-500 flex items-center justify-center text-xs font-bold">
                  {(storedUser?.username || 'U')[0].toUpperCase()}
                </div>
                <span className="max-w-[100px] truncate">{storedUser?.username || 'Account'}</span>
                <ChevronDown className="w-3.5 h-3.5 text-white/40" />
              </button>
              <AnimatePresence>
                {userDropOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 8, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 8, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-white/10 bg-surface-900/95 backdrop-blur-xl shadow-2xl py-1"
                  >
                    <Link to="/dashboard" className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-white/70 hover:text-white hover:bg-white/5">
                      <LayoutDashboard className="w-4 h-4" /> Dashboard
                    </Link>
                    <Link to="/predictions" className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-white/70 hover:text-white hover:bg-white/5">
                      <Brain className="w-4 h-4" /> My Predictions
                    </Link>
                    <Link to="/wallet" className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-white/70 hover:text-white hover:bg-white/5">
                      <Wallet className="w-4 h-4" /> Wallet
                    </Link>
                    <div className="h-px bg-white/10 my-1" />
                    <button
                      onClick={logout}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-white/5 w-full text-left"
                    >
                      <LogOut className="w-4 h-4" /> Sign Out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <>
              <Link to="/login" className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-white/70 hover:text-white transition-colors">
                <LogIn className="w-3.5 h-3.5" />
                Sign In
              </Link>
              <Link to="/register" className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-vit-500 hover:bg-vit-400 text-white transition-colors shadow-lg shadow-vit-500/20">
                Get Started
              </Link>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button onClick={() => setOpen(v => !v)} className="md:hidden p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/5 transition-colors">
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
            className="md:hidden border-t border-white/10 bg-surface-900/95 backdrop-blur-xl overflow-hidden"
          >
            <div className="px-4 py-4 space-y-1">
              {isLoggedIn && AUTH_LINKS.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={cn(
                    'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    location.pathname === link.path ? 'text-white bg-white/10' : 'text-white/60 hover:text-white hover:bg-white/5',
                  )}
                >
                  <link.icon className="w-4 h-4" /> {link.label}
                </Link>
              ))}
              {isLoggedIn && <div className="h-px bg-white/10 my-2" />}
              {PUBLIC_LINKS.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={cn(
                    'block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    location.pathname === link.path ? 'text-white bg-white/10' : 'text-white/60 hover:text-white hover:bg-white/5',
                  )}
                >
                  {link.label}
                </Link>
              ))}
              {isAdmin && (
                <Link to="/admin" className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium text-vit-400 hover:bg-vit-500/10 transition-colors">
                  <Shield className="w-4 h-4" /> Admin
                </Link>
              )}
              <div className="pt-3 border-t border-white/10 flex flex-col gap-2">
                {isLoggedIn ? (
                  <button onClick={logout} className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-red-400 hover:bg-white/5 transition-colors w-full">
                    <LogOut className="w-4 h-4" /> Sign Out
                  </button>
                ) : (
                  <>
                    <Link to="/login" className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium text-white/70 border border-white/10 hover:bg-white/5 transition-colors">
                      Sign In
                    </Link>
                    <Link to="/register" className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium bg-vit-500 hover:bg-vit-400 text-white transition-colors">
                      Get Started
                    </Link>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
