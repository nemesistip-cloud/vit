import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useGatewayHealth } from '@/hooks/useHealth'
import { StatusBadge } from '@/components/ui/StatusBadge'

const NAV_LINKS = [
  { label: 'Platform',      path: '/platform' },
  { label: 'AI',            path: '/ai' },
  { label: 'Storage',       path: '/storage' },
  { label: 'Status',        path: '/status' },
  { label: 'Developers',    path: '/developers' },
  { label: 'Docs',          path: '/docs' },
  { label: 'Roadmap',       path: '/roadmap' },
]

export function Navbar() {
  const [open, setOpen]       = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const location              = useLocation()
  const { data: health }      = useGatewayHealth()

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handler)
    return () => window.removeEventListener('scroll', handler)
  }, [])

  useEffect(() => setOpen(false), [location.pathname])

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled ? 'bg-surface-900/90 backdrop-blur-xl border-b border-white/10 shadow-lg shadow-black/20' : 'bg-transparent',
      )}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-vit-500 to-vit-700 flex items-center justify-center shadow-lg shadow-vit-500/30 group-hover:shadow-vit-500/50 transition-shadow">
            <span className="text-white font-bold text-sm">V</span>
          </div>
          <span className="font-bold text-lg tracking-tight text-white">
            VIT <span className="text-vit-400">Network</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(link => (
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
        <div className="hidden md:flex items-center gap-3">
          <a
            href="/status"
            className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors"
          >
            <Activity className="w-3.5 h-3.5" />
            <StatusBadge status={health?.status} size="sm" pulse />
          </a>
          <Link
            to="/developers"
            className="px-4 py-1.5 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors shadow-lg shadow-vit-600/25"
          >
            Get Started
          </Link>
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
              {NAV_LINKS.map(link => (
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
              <div className="mt-3 pt-3 border-t border-white/10">
                <Link
                  to="/developers"
                  className="block w-full px-4 py-2.5 rounded-lg bg-vit-600 text-white text-sm font-medium text-center"
                >
                  Get Started
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
