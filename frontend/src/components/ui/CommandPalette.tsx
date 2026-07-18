import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search, X, ArrowRight, LayoutDashboard, Wallet, Brain, Trophy,
  Activity, Shield, Vote, Landmark, Store, Share2, Coins, Radio,
  BarChart3, Building2, Smartphone, Users, Map, Zap, Layers,
  TrendingUp, ArrowLeftRight, Lock,
} from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

interface PaletteItem {
  id: string
  type: 'page' | 'match' | 'user'
  label: string
  sub?: string
  path: string
  icon: React.ElementType
}

const STATIC_PAGES: PaletteItem[] = [
  { id: 'dashboard',        type: 'page', label: 'Dashboard',        sub: 'Your personal hub',         path: '/dashboard',        icon: LayoutDashboard },
  { id: 'wallet',           type: 'page', label: 'Wallet',           sub: 'VIT balance & transactions', path: '/wallet',           icon: Wallet },
  { id: 'predictions',      type: 'page', label: 'Predictions',      sub: 'My prediction history',      path: '/predictions',      icon: Brain },
  { id: 'matches',          type: 'page', label: 'Matches',          sub: 'Browse live & upcoming',     path: '/matches',          icon: Activity },
  { id: 'leaderboard',      type: 'page', label: 'Leaderboard',      sub: 'Top predictors',             path: '/leaderboard',      icon: Trophy },
  { id: 'governance',       type: 'page', label: 'Governance',       sub: 'Proposals & voting',         path: '/governance',       icon: Vote },
  { id: 'treasury',         type: 'page', label: 'Treasury',         sub: 'DAO treasury management',    path: '/treasury',         icon: Landmark },
  { id: 'marketplace',      type: 'page', label: 'Marketplace',      sub: 'Prediction marketplace',     path: '/marketplace',      icon: Store },
  { id: 'referral',         type: 'page', label: 'Referral',         sub: 'Invite & earn',              path: '/referral',         icon: Share2 },
  { id: 'defi',             type: 'page', label: 'DeFi Pools',       sub: 'Yield & liquidity',          path: '/defi',             icon: Coins },
  { id: 'inplay',           type: 'page', label: 'In-Play',          sub: 'Live prediction markets',    path: '/inplay',           icon: Radio },
  { id: 'analytics-studio', type: 'page', label: 'Analytics Studio', sub: 'Performance analytics',      path: '/analytics-studio', icon: BarChart3 },
  { id: 'enterprise',       type: 'page', label: 'Enterprise',       sub: 'API & data licensing',       path: '/enterprise',       icon: Building2 },
  { id: 'ecosystem',        type: 'page', label: 'Ecosystem',        sub: 'Mobile & integrations',      path: '/ecosystem',        icon: Smartphone },
  { id: 'social',           type: 'page', label: 'Social Feed',      sub: 'Prediction community',       path: '/social',           icon: Users },
  { id: 'validators',       type: 'page', label: 'Validators',       sub: 'Network validators',         path: '/validators',       icon: Shield },
  { id: 'chain',            type: 'page', label: 'Chain Explorer',   sub: 'Block & tx browser',         path: '/chain',            icon: Activity },
  { id: 'roadmap',          type: 'page', label: 'Roadmap',          sub: 'Platform development phases',path: '/roadmap',          icon: Map },
  { id: 'accumulator',      type: 'page', label: 'Accumulator',      sub: 'Multi-leg bet builder',      path: '/accumulator',      icon: Layers },
  { id: 'rollover',         type: 'page', label: 'Rollover Engine',  sub: 'Fixture certification',      path: '/rollover',         icon: ArrowRight },
  { id: 'backtest',         type: 'page', label: 'Backtest',         sub: 'Historical simulation',      path: '/backtest',         icon: BarChart3 },
  { id: 'bankroll',         type: 'page', label: 'Bankroll',         sub: 'Kelly Criterion manager',    path: '/bankroll',         icon: TrendingUp },
  { id: 'vitcoin',          type: 'page', label: 'VITCoin',          sub: 'Buy, sell, convert',         path: '/vitcoin',          icon: Zap },
  { id: 'exchange',         type: 'page', label: 'P2P Exchange',     sub: 'Peer-to-peer trading',       path: '/exchange',         icon: ArrowLeftRight },
  { id: 'vaults',           type: 'page', label: 'Vaults',           sub: 'Staking vaults',             path: '/vaults',           icon: Lock },
  { id: 'bridge',           type: 'page', label: 'Bridge',           sub: 'Cross-chain transfers',      path: '/bridge',           icon: ArrowLeftRight },
  { id: 'tasks',            type: 'page', label: 'Tasks & XP',       sub: 'Gamification & rewards',     path: '/tasks',            icon: Trophy },
  { id: 'subscription',     type: 'page', label: 'Subscription',     sub: 'Plans & pricing',            path: '/subscription',     icon: Star as React.ElementType },
  { id: 'settings',         type: 'page', label: 'Settings',         sub: 'Profile & preferences',      path: '/settings',         icon: Shield },
  { id: 'admin',            type: 'page', label: 'Admin Suite',      sub: 'System management',          path: '/admin',            icon: Shield },
]

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Star } from 'lucide-react'

function useApiSearch(q: string) {
  return useQuery<PaletteItem[]>({
    queryKey: ['palette-search', q],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/search?q=${encodeURIComponent(q)}&limit=8`, {
        signal,
        headers: authHeaders(),
      })
      if (!r.ok) return []
      const d = await r.json()
      const items = Array.isArray(d) ? d : d.results ?? d.items ?? []
      return items.map((item: any) => ({
        id: `api-${item.id ?? item.match_id ?? item.username}`,
        type: item.type ?? 'match',
        label: item.label ?? item.title ?? (item.home_team && item.away_team ? `${item.home_team} vs ${item.away_team}` : null) ?? item.username ?? 'Unknown',
        sub: item.sub ?? item.description ?? item.competition,
        path: item.url ?? (item.type === 'user' ? '/leaderboard' : `/matches/${item.id ?? item.match_id}`),
        icon: item.type === 'user' ? Users : TrendingUp,
      }))
    },
    enabled: q.length >= 2,
    retry: false,
    staleTime: 10_000,
  })
}

interface Props {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: Props) {
  const [q, setQ]           = useState('')
  const [cursor, setCursor] = useState(0)
  const inputRef            = useRef<HTMLInputElement>(null)
  const navigate            = useNavigate()

  const { data: apiResults = [] } = useApiSearch(q)

  const staticFiltered = useMemo(() => {
    if (!q) return STATIC_PAGES.slice(0, 8)
    const lq = q.toLowerCase()
    return STATIC_PAGES.filter(p =>
      p.label.toLowerCase().includes(lq) || p.sub?.toLowerCase().includes(lq)
    ).slice(0, 8)
  }, [q])

  const results: PaletteItem[] = q.length >= 2
    ? [...staticFiltered, ...apiResults].slice(0, 10)
    : staticFiltered

  useEffect(() => {
    if (open) { setQ(''); setCursor(0); setTimeout(() => inputRef.current?.focus(), 50) }
  }, [open])

  useEffect(() => { setCursor(0) }, [q])

  function go(item: PaletteItem) {
    navigate(item.path)
    onClose()
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setCursor(c => Math.min(c + 1, results.length - 1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setCursor(c => Math.max(c - 1, 0)) }
    if (e.key === 'Enter' && results[cursor]) go(results[cursor])
    if (e.key === 'Escape') onClose()
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -16 }}
              transition={{ duration: 0.15 }}
              className="w-full max-w-xl bg-surface-900/98 border border-white/12 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto"
            >
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/8">
                <Search className="w-4 h-4 text-white/30 shrink-0" />
                <input
                  ref={inputRef}
                  value={q}
                  onChange={e => setQ(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Search pages, matches, users…"
                  className="flex-1 bg-transparent text-white placeholder-white/25 text-sm outline-none"
                />
                {q && (
                  <button onClick={() => setQ('')} className="text-white/25 hover:text-white/60 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                )}
                <kbd className="px-2 py-0.5 rounded bg-white/6 text-white/20 text-[10px] font-mono">ESC</kbd>
              </div>

              {/* Results */}
              <div className="max-h-80 overflow-y-auto py-2">
                {results.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-10 gap-1.5">
                    <Search className="w-6 h-6 text-white/10" />
                    <p className="text-white/25 text-sm">No results for "{q}"</p>
                  </div>
                )}
                {results.map((item, i) => {
                  const Icon = item.icon
                  return (
                    <button
                      key={item.id}
                      onClick={() => go(item)}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                        i === cursor ? 'bg-white/8' : 'hover:bg-white/5',
                      )}
                    >
                      <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                        <Icon className="w-3.5 h-3.5 text-white/40" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white font-medium">{item.label}</p>
                        {item.sub && <p className="text-xs text-white/35 truncate">{item.sub}</p>}
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-white/15 shrink-0" />
                    </button>
                  )
                })}
              </div>

              {/* Footer hint */}
              <div className="px-4 py-2.5 border-t border-white/6 flex items-center gap-4 text-[10px] text-white/20">
                <span><kbd className="font-mono">↑↓</kbd> navigate</span>
                <span><kbd className="font-mono">↵</kbd> open</span>
                <span><kbd className="font-mono">esc</kbd> close</span>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
