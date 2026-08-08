import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Brain, Wallet, Vote, Store, BarChart3,
  Cloud, Database, Coins, Radio, ChevronDown, Shield,
  Activity, Building2, Zap, Users, Globe,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export interface Workspace {
  id: string
  label: string
  icon: React.ElementType
  path: string
  color: string
  description: string
  badge?: string
}

const WORKSPACES: Workspace[] = [
  { id: 'dashboard',   label: 'Dashboard',       icon: LayoutDashboard, path: '/dashboard',        color: 'text-violet-400', description: 'Your personal hub' },
  { id: 'sports',      label: 'Sports AI',        icon: Brain,           path: '/matches',           color: 'text-blue-400',   description: 'Predictions & matches' },
  { id: 'wallet',      label: 'Wallet',           icon: Wallet,          path: '/wallet',            color: 'text-emerald-400', description: 'VIT balance & transactions' },
  { id: 'analytics',   label: 'Analytics',        icon: BarChart3,       path: '/analytics-studio',  color: 'text-amber-400',  description: 'Performance studio' },
  { id: 'defi',        label: 'DeFi',             icon: Coins,           path: '/defi',              color: 'text-pink-400',   description: 'Yield & liquidity pools' },
  { id: 'inplay',      label: 'In-Play',          icon: Radio,           path: '/inplay',            color: 'text-red-400',    description: 'Live prediction markets', badge: 'LIVE' },
  { id: 'governance',  label: 'Governance',       icon: Vote,            path: '/governance',        color: 'text-indigo-400', description: 'DAO proposals & voting' },
  { id: 'marketplace', label: 'Marketplace',      icon: Store,           path: '/marketplace',       color: 'text-orange-400', description: 'Prediction marketplace' },
  { id: 'storage',     label: 'Storage',          icon: Database,        path: '/storage',           color: 'text-cyan-400',   description: 'Tachyon decentralised storage' },
  { id: 'cloud',       label: 'Cloud',            icon: Cloud,           path: '/status',            color: 'text-sky-400',    description: 'Infrastructure status' },
  { id: 'validators',  label: 'Validators',       icon: Shield,          path: '/validators',        color: 'text-teal-400',   description: 'Network validators' },
  { id: 'enterprise',  label: 'Enterprise',       icon: Building2,       path: '/enterprise',        color: 'text-slate-300',  description: 'API & data licensing' },
]

function workspaceForPath(path: string): Workspace | undefined {
  return [...WORKSPACES].sort((a, b) => b.path.length - a.path.length)
    .find(w => path.startsWith(w.path))
}

export function WorkspaceSwitcher({ mobile = false }: { mobile?: boolean }) {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()

  const active = workspaceForPath(location.pathname) ?? WORKSPACES[0]
  const Icon = active.icon

  return (
    <div className={cn('relative', mobile && 'w-full')}>
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-xl border transition-all text-sm font-medium',
          mobile && 'w-full justify-between',
          open
            ? 'bg-white/10 border-white/20 text-white'
            : 'bg-white/5 border-white/8 text-white/70 hover:bg-white/8 hover:text-white',
        )}
      >
        <Icon className={cn('w-4 h-4', active.color)} />
        <span className={cn('max-w-[120px] truncate', !mobile && 'hidden sm:block')}>{active.label}</span>
        <ChevronDown className={cn('w-3.5 h-3.5 text-white/40 transition-transform', open && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.97 }}
              transition={{ duration: 0.15 }}
              className={cn(
                'z-50 rounded-2xl border border-white/10 bg-surface-900/95 backdrop-blur-xl shadow-2xl shadow-black/50 overflow-hidden',
                mobile
                  ? 'relative left-auto top-auto mt-2 w-full max-h-[min(65dvh,28rem)]'
                  : 'absolute left-0 top-full mt-2 w-72',
              )}
            >
              <div className="px-3 py-2 border-b border-white/8">
                <p className="text-[10px] font-semibold text-white/30 uppercase tracking-widest">Workspaces</p>
              </div>
              <div className="p-2 grid grid-cols-1 gap-0.5 max-h-80 overflow-y-auto">
                {WORKSPACES.map(ws => {
                  const WIcon = ws.icon
                  const isActive = ws.id === active.id
                  return (
                    <button
                      key={ws.id}
                      onClick={() => { navigate(ws.path); setOpen(false) }}
                      className={cn(
                        'flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-left transition-colors group',
                        isActive
                          ? 'bg-white/10 text-white'
                          : 'text-white/55 hover:bg-white/5 hover:text-white',
                      )}
                    >
                      <div className={cn('w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0 group-hover:bg-white/8', isActive && 'bg-white/10')}>
                        <WIcon className={cn('w-4 h-4', ws.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{ws.label}</span>
                          {ws.badge && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-500/20 text-red-400 tracking-wide">{ws.badge}</span>
                          )}
                        </div>
                        <p className="text-[11px] text-white/30 truncate">{ws.description}</p>
                      </div>
                      {isActive && <div className="w-1.5 h-1.5 rounded-full bg-violet-400 shrink-0" />}
                    </button>
                  )
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
