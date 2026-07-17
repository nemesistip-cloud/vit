import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, ArrowLeft, Map, Trophy, Brain, Wallet, Vote, Store } from 'lucide-react'

const QUICK_LINKS = [
  { label: 'Home',        path: '/',           icon: Home   },
  { label: 'Matches',     path: '/matches',    icon: Trophy },
  { label: 'Predictions', path: '/predictions', icon: Brain  },
  { label: 'Wallet',      path: '/wallet',     icon: Wallet },
  { label: 'Governance',  path: '/governance', icon: Vote   },
  { label: 'Marketplace', path: '/marketplace', icon: Store  },
  { label: 'Roadmap',     path: '/roadmap',    icon: Map    },
]

export default function NotFound() {
  const { pathname } = useLocation()

  return (
    <div className="pt-16 min-h-screen flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          {/* Glowing 404 */}
          <div className="relative inline-block mb-8">
            <div className="absolute inset-0 blur-3xl bg-vit-500/20 rounded-full" />
            <p className="relative text-[120px] font-black text-white/5 leading-none select-none">
              404
            </p>
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-b from-vit-400 to-vit-700 leading-none">
                404
              </p>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-white mb-3">Page not found</h1>
          <p className="text-white/50 text-sm mb-2 leading-relaxed">
            <code className="px-2 py-0.5 rounded bg-white/8 text-vit-300 text-xs font-mono">{pathname}</code>
            {' '}doesn't exist on this platform.
          </p>
          <p className="text-white/30 text-sm mb-10">
            It may have moved, been removed, or you may have mistyped the address.
          </p>

          {/* Action buttons */}
          <div className="flex items-center justify-center gap-3 mb-10">
            <button
              onClick={() => window.history.back()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm font-medium transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Go Back
            </button>
            <Link
              to="/"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white text-sm font-medium transition-colors shadow-lg shadow-vit-500/20"
            >
              <Home className="w-4 h-4" /> Home
            </Link>
          </div>

          {/* Quick links */}
          <div className="border border-white/8 rounded-xl bg-white/3 p-5">
            <p className="text-xs text-white/30 uppercase tracking-wider mb-4">Quick links</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {QUICK_LINKS.map(({ label, path, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white text-sm transition-colors"
                >
                  <Icon className="w-3.5 h-3.5 text-vit-400 shrink-0" />
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
