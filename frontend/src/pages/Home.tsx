import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, Brain, HardDrive, Layers, Zap, Users, TrendingUp,
  ArrowRight, ChevronRight, Activity, Shield, BarChart3,
  Wallet, Star,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { StatusBadge } from '@/components/ui/StatusBadge'

function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status-home'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/health/summary`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 30_000, refetchInterval: 60_000,
  })
}

function usePlatformStats() {
  return useQuery({
    queryKey: ['platform-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/system/status`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 60_000,
  })
}

function useTopMatches() {
  return useQuery({
    queryKey: ['top-matches-home'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/matches/upcoming?limit=3`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d.slice(0, 3) : []
    },
    staleTime: 300_000,
  })
}

function useLeaderboardPreview() {
  return useQuery({
    queryKey: ['leaderboard-home'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/analytics/leaderboard/users?limit=5`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d.slice(0, 5) : (d.leaderboard ?? d.items ?? []).slice(0, 5)
    },
    staleTime: 300_000,
  })
}

const FEATURES = [
  {
    icon: Brain,
    color: 'from-vit-500 to-vit-700',
    glow: 'shadow-vit-500/20',
    title: 'AI Predictions',
    desc: '13+ ML models analyze fixtures across 50+ leagues — real-time probability scores and EV-optimized picks.',
    href: '/ai',
    tag: 'Live',
  },
  {
    icon: Trophy,
    color: 'from-amber-500 to-orange-600',
    glow: 'shadow-amber-500/20',
    title: 'Matches & Odds',
    desc: 'Upcoming, live, and completed fixtures with AI confidence chips, odds movement, and H2H form guides.',
    href: '/matches',
    tag: 'Live',
  },
  {
    icon: Layers,
    color: 'from-cyan-500 to-blue-600',
    glow: 'shadow-cyan-500/20',
    title: 'VIT Chain',
    desc: 'A native PoS blockchain (Chain ID 7764) for transparent prediction records, staking, and governance.',
    href: '/chain',
    tag: 'Beta',
  },
  {
    icon: Wallet,
    color: 'from-emerald-500 to-teal-600',
    glow: 'shadow-emerald-500/20',
    title: 'VITCoin Wallet',
    desc: 'Send, receive, and stake VIT. Real-time price feeds in USD and NGN. Cross-chain bridge coming soon.',
    href: '/wallet',
    tag: 'Beta',
  },
  {
    icon: HardDrive,
    color: 'from-purple-500 to-violet-600',
    glow: 'shadow-purple-500/20',
    title: 'Decentralised Storage',
    desc: 'Erasure-coded file storage across Dropbox, OneDrive, and S3 with on-chain proof verification.',
    href: '/storage',
    tag: 'Beta',
  },
  {
    icon: Shield,
    color: 'from-pink-500 to-rose-600',
    glow: 'shadow-pink-500/20',
    title: 'Governance',
    desc: 'Validator-gated proposals, on-chain voting with VIT weight, and automated execution of passed proposals.',
    href: '/platform',
    tag: 'Soon',
  },
]

const HOW_IT_WORKS = [
  { step: 1, title: 'Sign Up', desc: 'Create your account in seconds — no crypto experience needed.' },
  { step: 2, title: 'Browse Matches', desc: 'Explore AI-ranked fixtures with confidence scores and EV estimates.' },
  { step: 3, title: 'Predict & Earn', desc: 'Place predictions, climb the leaderboard, and earn VITCoin rewards.' },
]

export default function Home() {
  const { data: sysStatus }  = useSystemStatus()
  const { data: stats }      = usePlatformStats()
  const { data: matches }    = useTopMatches()
  const { data: leaderboard } = useLeaderboardPreview()

  const overallStatus = sysStatus?.overall_status ?? 'loading'
  const isHealthy     = overallStatus === 'HEALTHY' || overallStatus === 'ok'

  const STAT_ITEMS = [
    { label: 'Models Loaded',    value: stats?.models_loaded ?? '13+' },
    { label: 'Users',            value: stats?.total_users   ?? '—' },
    { label: 'Predictions',      value: stats?.total_predictions ?? '—' },
    { label: 'Platform Status',  value: overallStatus },
  ]

  return (
    <div className="pt-16">
      {/* Hero */}
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
        {/* Hero banner image */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: 'url(/hero-banner.jpg)' }}
        />
        {/* Overlay: darken image so text stays legible */}
        <div className="absolute inset-0 bg-surface-900/70" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-surface-900" />

        {/* Ambient glow */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-vit-500/5 blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
          {/* Status pill */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-8">
            <Link to="/platform" className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5" />
              <span className="text-xs text-white/60">Platform</span>
              <StatusBadge status={overallStatus === 'loading' ? undefined : isHealthy ? 'healthy' : overallStatus} size="sm" pulse />
              <span className="text-xs text-white/30">·</span>
              <span className="text-xs text-vit-400 font-medium">{stats?.version ? `v${String(stats.version).replace(/^v/, '')}` : 'v1.1'}</span>
            </Link>
          </motion.div>

          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight">
            The AI-Powered
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-vit-400 to-vit-300">
              Decentralized Gateway
            </span>
          </motion.h1>

          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="text-xl text-white/60 mb-10 max-w-2xl mx-auto leading-relaxed">
            VIT Network aggregates AI sports intelligence, blockchain, decentralised storage, and a VITCoin economy
            into one unified platform — predict smarter, stake confidently, earn transparently.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register" className="flex items-center gap-2 px-8 py-3.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white font-medium transition-all shadow-xl shadow-vit-500/25 hover:shadow-vit-500/40 text-sm">
              Get Started Free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/matches" className="flex items-center gap-2 px-8 py-3.5 rounded-xl border border-white/15 bg-white/5 hover:bg-white/10 text-white font-medium transition-colors text-sm">
              Browse Matches <ChevronRight className="w-4 h-4" />
            </Link>
          </motion.div>

          {/* Live service pills — driven by /api/system/health/summary */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
            className="flex flex-wrap items-center justify-center gap-3 mt-10 text-xs">
            {([
              { key: 'gateway', label: 'Gateway',    field: (d: any) => d?.details?.kernel ?? d?.details?.platform ?? d?.overall_status },
              { key: 'ai',      label: 'AI Engine',  field: (d: any) => d?.details?.ai },
              { key: 'storage', label: 'Storage',    field: (d: any) => d?.details?.storage },
              { key: 'db',      label: 'Database',   field: (d: any) => d?.details?.database },
            ] as const).map(({ key, label, field }) => {
              const raw = field(sysStatus)
              const ok  = raw === 'healthy' || raw === 'ok' || raw === 'HEALTHY'
              const deg = raw === 'degraded' || raw === 'warning'
              return (
                <span key={key} className={cn(
                  'inline-flex items-center gap-1.5 px-3 py-1 rounded-full border',
                  ok  ? 'border-emerald-500/25 bg-emerald-500/8 text-emerald-400/80' :
                  deg ? 'border-amber-500/25 bg-amber-500/8 text-amber-400/80' :
                  raw ? 'border-red-500/20 bg-red-500/5 text-red-400/60' :
                        'border-white/8 bg-white/3 text-white/30'
                )}>
                  <span className={cn('w-1.5 h-1.5 rounded-full shrink-0',
                    ok  ? 'bg-emerald-400 animate-pulse' :
                    deg ? 'bg-amber-400' :
                    raw ? 'bg-red-400' : 'bg-white/20'
                  )} />
                  {label}
                </span>
              )
            })}
          </motion.div>
        </div>
      </section>

      {/* Live stats strip */}
      <section className="border-y border-white/8 bg-surface-800/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            {STAT_ITEMS.map(({ label, value }, i) => (
              <motion.div key={label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 * i }}
                className="text-center">
                <div className="text-2xl font-bold text-white mb-1">
                  {label === 'Platform Status' ? (
                    <StatusBadge status={isHealthy ? 'healthy' : overallStatus} />
                  ) : value}
                </div>
                <div className="text-xs text-white/40 uppercase tracking-wide">{label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Top picks today */}
      {matches && matches.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-white">Today's AI Top Picks</h2>
              <p className="text-white/50 text-sm mt-1">Highest-confidence fixtures right now</p>
            </div>
            <Link to="/matches" className="text-sm text-vit-400 hover:text-vit-300 flex items-center gap-1">
              All matches <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            {matches.map((m: any, i: number) => (
              <motion.div key={i} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                className="bg-surface-800/60 border border-white/8 rounded-xl p-5 hover:border-vit-500/30 transition-all group">
                <div className="text-xs text-white/40 mb-3">{m.league}</div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="text-sm font-medium text-white">{m.home_team}</span>
                  <span className="text-xs text-white/30">vs</span>
                  <span className="text-sm font-medium text-white">{m.away_team}</span>
                </div>
                {m.confidence != null && (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full bg-vit-500 rounded-full" style={{ width: `${Math.round(m.confidence * 100)}%` }} />
                    </div>
                    <span className="text-xs text-vit-400 font-medium shrink-0">{Math.round(m.confidence * 100)}%</span>
                  </div>
                )}
                {m.bet_side && (
                  <span className="inline-block mt-2 px-2 py-0.5 rounded-full bg-vit-500/15 text-vit-300 text-[10px] font-medium uppercase">{m.bet_side}</span>
                )}
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Feature tiles */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-3">Everything in One Platform</h2>
          <p className="text-white/50 max-w-xl mx-auto">One account. Full access to AI sports intelligence, a native blockchain, decentralised storage, and a community of predictors.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <motion.div key={f.title} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
              <Link to={f.href} className="group flex flex-col h-full p-6 rounded-2xl border border-white/8 bg-surface-800/40 hover:border-white/15 hover:bg-surface-800/60 transition-all">
                <div className="flex items-start justify-between mb-5">
                  <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${f.color} flex items-center justify-center shadow-lg ${f.glow}`}>
                    <f.icon className="w-5 h-5 text-white" />
                  </div>
                  <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full border',
                    f.tag === 'Live' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' :
                    f.tag === 'Beta' ? 'bg-amber-500/15 border-amber-500/30 text-amber-400' :
                    'bg-white/5 border-white/10 text-white/30')}>
                    {f.tag}
                  </span>
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-white/50 flex-1 leading-relaxed">{f.desc}</p>
                <div className="flex items-center gap-1 mt-4 text-xs text-vit-400 group-hover:text-vit-300 transition-colors">
                  Explore <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-white/8 bg-surface-800/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-3">How It Works</h2>
            <p className="text-white/50">Start earning in three simple steps</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-8 relative">
            <div className="hidden sm:block absolute top-8 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-vit-500/30 to-transparent" />
            {HOW_IT_WORKS.map((step, i) => (
              <motion.div key={step.step} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.15 }}
                className="flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center mb-4 relative z-10">
                  <span className="text-2xl font-bold text-vit-400">{step.step}</span>
                </div>
                <h3 className="font-semibold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Leaderboard preview */}
      {leaderboard && leaderboard.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-white">Top Predictors</h2>
              <p className="text-white/50 text-sm mt-1">This week's leaderboard</p>
            </div>
            <Link to="/leaderboard" className="text-sm text-vit-400 hover:text-vit-300 flex items-center gap-1">
              Full leaderboard <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="bg-surface-800/60 border border-white/8 rounded-2xl overflow-hidden">
            {leaderboard.map((u: any, i: number) => (
              <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                <span className={cn('w-8 text-center font-bold text-sm', i === 0 ? 'text-amber-400' : i === 1 ? 'text-white/60' : i === 2 ? 'text-amber-700' : 'text-white/25')}>
                  #{i + 1}
                </span>
                <div className="w-9 h-9 rounded-full bg-vit-500/20 flex items-center justify-center text-sm font-bold text-vit-400">
                  {(u.username || u.email || 'U')[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{u.username || u.email || 'Anonymous'}</p>
                  {u.clv_tier && <p className="text-xs text-white/30">{u.clv_tier}</p>}
                </div>
                <span className="text-sm font-bold text-emerald-400">
                  {u.win_rate ? `${(u.win_rate * 100).toFixed(1)}%` : u.score ?? ''}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="relative rounded-3xl border border-vit-500/20 bg-gradient-to-br from-vit-500/10 via-surface-800/60 to-surface-800/40 p-12 text-center overflow-hidden">
          <div className="absolute inset-0 section-grid opacity-15" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-vit-500/8 blur-3xl" />
          <div className="relative">
            <Zap className="w-10 h-10 text-vit-400 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-white mb-3">Ready to start predicting?</h2>
            <p className="text-white/50 max-w-md mx-auto mb-8">Join VIT Network and access AI-powered sports intelligence across 50+ competitions.</p>
            <Link to="/register" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white font-medium transition-all shadow-xl shadow-vit-500/25">
              Create Free Account <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
