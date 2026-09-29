import { motion } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Trophy, Brain, HardDrive, Layers, Zap, Users, TrendingUp,
  ArrowRight, ChevronRight, Activity, Shield, BarChart3,
  Wallet, Star,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'

function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status-home'],
    queryFn: async ({ signal }) => {
      const [healthResponse, summaryResponse] = await Promise.all([
        fetch(`${ENDPOINTS.gateway}/health`, { signal }),
        fetch(`${ENDPOINTS.gateway}/api/system/health/summary`, { signal }),
      ])
      const health = healthResponse.ok ? await healthResponse.json() : null
      const summary = summaryResponse.ok ? await summaryResponse.json() : null
      return { ...summary, gateway_status: health?.status, gateway_health: health }
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
  const isAuthenticated = Boolean(getAuthToken())
  return useQuery({
    queryKey: ['leaderboard-home'],
    enabled: isAuthenticated,
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/analytics/leaderboard/users?limit=5`, {
        signal,
        headers: authHeaders(),
      })
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
    desc: 'Model outputs are ranked in context, paired with record-backed reasoning, and made easier to inspect after kickoff.',
    href: '/ai',
    tag: 'Available',
  },
  {
    icon: Trophy,
    color: 'from-amber-500 to-orange-600',
    glow: 'shadow-amber-500/20',
    title: 'Matches & Odds',
    desc: 'Review upcoming fixtures, live market context, and the confidence view behind each recommendation.',
    href: '/matches',
    tag: 'Available',
  },
  {
    icon: Layers,
    color: 'from-cyan-500 to-blue-600',
    glow: 'shadow-cyan-500/20',
    title: 'VIT Chain',
    desc: 'A public chain view for verification, recordkeeping, governance, and service discovery around the network.',
    href: '/chain',
    tag: 'Beta',
  },
  {
    icon: Wallet,
    color: 'from-emerald-500 to-teal-600',
    glow: 'shadow-emerald-500/20',
    title: 'Wallet',
    desc: 'Track balances and account activity with a clear view of status, limits, and platform interactions.',
    href: '/wallet',
    tag: 'Beta',
  },
  {
    icon: HardDrive,
    color: 'from-purple-500 to-violet-600',
    glow: 'shadow-purple-500/20',
    title: 'Storage',
    desc: 'Evidence, records, and platform artifacts can be anchored in a verifiable storage layer with proof checks.',
    href: '/storage',
    tag: 'Beta',
  },
  {
    icon: Shield,
    color: 'from-pink-500 to-rose-600',
    glow: 'shadow-pink-500/20',
    title: 'Responsible Use',
    desc: 'Operational guardrails, transparency expectations, and clear limits for how predictions should be interpreted.',
    href: '/responsible-use',
    tag: 'Live',
  },
]

const HOW_IT_WORKS = [
  { step: 1, title: 'Review the record', desc: 'Check the live platform status and the sealed pick before the event starts.' },
  { step: 2, title: 'Inspect the signal', desc: 'Compare the fixture, confidence view, and market context in one place.' },
  { step: 3, title: 'Verify the outcome', desc: 'Match the published record against the result after kickoff to confirm what was stated.' },
]

export default function Home() {
  const navigate = useNavigate()
  const { data: sysStatus }  = useSystemStatus()
  const { data: stats }      = usePlatformStats()
  const { data: matches }    = useTopMatches()
  const { data: leaderboard } = useLeaderboardPreview()

  const overallStatus = sysStatus?.gateway_status ?? 'loading'
  const isHealthy     = overallStatus === 'healthy' || overallStatus === 'ok'
  const isAuthenticated = Boolean(getAuthToken())

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
            <Link to="/status-page" className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-vit-300" />
              <span className="text-xs text-white/60">Status</span>
              <StatusBadge status={overallStatus === 'loading' ? undefined : isHealthy ? 'healthy' : overallStatus} size="sm" pulse />
              <span className="text-xs text-white/30">·</span>
              <span className="text-xs text-vit-400 font-medium">{stats?.version ? `v${String(stats.version).replace(/^v/, '')}` : 'Live'}</span>
            </Link>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.24em] text-white/55 mb-6 backdrop-blur-sm">
            Predictions with a public record
          </motion.div>

          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
            className="text-4xl sm:text-5xl lg:text-[4.3rem] font-medium tracking-[-0.07em] text-white/95 mb-5 leading-[0.94] max-w-4xl mx-auto">
            AI-ranked picks. Sealed before kickoff.
          </motion.h1>

          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="text-base sm:text-lg text-white/65 mb-8 max-w-2xl mx-auto leading-relaxed">
            Every prediction is recorded before kickoff so the signal can be checked afterwards — no silent edits, no hidden assumptions.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10">
            <Link to="/verification" className="flex items-center gap-2 px-7 py-3 rounded-2xl bg-vit-500 hover:bg-vit-400 text-white font-medium transition-all shadow-lg shadow-vit-500/20 hover:shadow-vit-500/30 text-sm">
              See live picks <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/verification" className="flex items-center gap-2 px-7 py-3 rounded-2xl border border-white/12 bg-white/5 hover:bg-white/8 text-white/80 hover:text-white font-medium transition-colors text-sm">
              How verification works <ChevronRight className="w-4 h-4" />
            </Link>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            className="mx-auto max-w-xl rounded-2xl border border-white/10 bg-surface-900/75 p-4 shadow-[0_24px_80px_-42px_rgba(59,101,255,0.65)] backdrop-blur-xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] uppercase tracking-[0.22em] text-white/45">Sealed pick</p>
                <h3 className="mt-2 text-xl font-medium tracking-[-0.04em] text-white">Arsenal vs Chelsea</h3>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative flex h-11 w-11 items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-500/10">
                  <div className="absolute inset-1 rounded-full border border-emerald-300/40" />
                  <span className="text-[9px] font-semibold text-emerald-300">Seal</span>
                </div>
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_18px_rgba(74,222,128,0.8)]" />
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-left">
              <div className="rounded-xl border border-white/8 bg-white/3 p-3">
                <div className="text-[10px] uppercase tracking-[0.18em] text-white/40">Pick</div>
                <div className="mt-2 text-sm font-medium text-white">Home win</div>
              </div>
              <div className="rounded-xl border border-white/8 bg-white/3 p-3">
                <div className="text-[10px] uppercase tracking-[0.18em] text-white/40">Prob.</div>
                <div className="mt-2 text-sm font-medium text-vit-300">58%</div>
              </div>
              <div className="rounded-xl border border-white/8 bg-white/3 p-3">
                <div className="text-[10px] uppercase tracking-[0.18em] text-white/40">Kickoff</div>
                <div className="mt-2 text-sm font-medium text-white">19:45</div>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-white/8 bg-black/20 px-3 py-2 text-xs text-white/60">
              <span>seal id</span>
              <span className="font-mono text-[11px] tracking-[0.18em] text-white/80">a7f3…c91b</span>
            </div>
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

      {/* Live intelligence strip */}
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
          <div className="mt-5 flex items-center justify-center text-[11px] text-white/45">
            Last status check: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </section>

      {/* Live intelligence */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-6 items-stretch">
          <div className="rounded-2xl border border-vit-500/20 bg-gradient-to-br from-vit-500/10 via-surface-800/70 to-surface-800/40 p-7">
            <div className="flex items-center gap-2 text-vit-300 text-sm font-medium mb-4">
              <Activity className="w-4 h-4" /> Live intelligence
            </div>
            <h2 className="text-2xl sm:text-3xl font-medium tracking-[-0.04em] text-white/95 mb-3">Signals you can verify.</h2>
            <p className="text-white/60 leading-relaxed mb-6">
              Follow live service health, upcoming fixtures, and model confidence from the same
              network that powers VIT applications.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-white/8 bg-black/15 p-4">
                <p className="text-xs text-white/35 uppercase tracking-wide mb-1">Upcoming fixtures</p>
                <p className="text-xl font-semibold text-white">{matches?.length ? `${matches.length}+` : '—'}</p>
              </div>
              <div className="rounded-xl border border-white/8 bg-black/15 p-4">
                <p className="text-xs text-white/35 uppercase tracking-wide mb-1">Network health</p>
                <p className="text-xl font-semibold text-emerald-400">{isHealthy ? 'Healthy' : overallStatus}</p>
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-white/8 bg-surface-800/50 p-7">
            <p className="text-xs text-vit-400 uppercase tracking-[0.2em] mb-3">Built for builders</p>
            <h2 className="text-2xl font-medium tracking-[-0.04em] text-white/95 mb-3">One network. Many surfaces.</h2>
            <p className="text-white/60 leading-relaxed mb-6">
              Explore the platform, connect to developer APIs, or inspect the chain as the ecosystem evolves.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/developers" className="inline-flex items-center gap-2 rounded-xl bg-white/8 border border-white/10 px-4 py-2.5 text-sm text-white hover:bg-white/12 transition-colors">
                Developer access <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/status-page" className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-sm text-white/65 hover:text-white transition-colors">
                Check status
              </Link>
            </div>
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
                onClick={() => {
                  const targetId = Number(m.id ?? m.match_id)
                  if (Number.isFinite(targetId) && targetId > 0) {
                    navigate(`/matches/${targetId}`)
                  }
                }}
                className="bg-surface-800/60 border border-white/8 rounded-xl p-5 hover:border-vit-500/30 transition-all group cursor-pointer">
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
          <p className="text-xs text-vit-400 uppercase tracking-[0.2em] mb-3">The ecosystem</p>
          <h2 className="text-3xl font-medium tracking-[-0.05em] text-white/95 mb-3">Intelligence, settlement, and access.</h2>
          <p className="text-white/60 max-w-xl mx-auto">Move from signal to action across AI Engine, Matches, VIT Chain, Wallet, Storage, and the developer platform.</p>
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
                    f.tag === 'Available' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' :
                    f.tag === 'Beta' ? 'bg-amber-500/15 border-amber-500/30 text-amber-400' :
                    'bg-white/5 border-white/10 text-white/30')}>
                    {f.tag}
                  </span>
                </div>
                <h3 className="font-medium text-white/95 mb-2">{f.title}</h3>
                <p className="text-sm text-white/60 flex-1 leading-relaxed">{f.desc}</p>
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
            <h2 className="text-3xl font-medium tracking-[-0.05em] text-white/95 mb-3">How it works</h2>
            <p className="text-white/60">A clear three-step verification flow</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-8 relative">
            <div className="hidden sm:block absolute top-8 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-vit-500/30 to-transparent" />
            {HOW_IT_WORKS.map((step, i) => (
              <motion.div key={step.step} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.15 }}
                className="flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center mb-4 relative z-10">
                  <span className="text-2xl font-bold text-vit-400">{step.step}</span>
                </div>
                <h3 className="font-medium text-white/95 mb-2">{step.title}</h3>
                <p className="text-sm text-white/60 leading-relaxed">{step.desc}</p>
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
                  {u.win_rate != null ? `${(u.win_rate * 100).toFixed(1)}%` : u.score ?? ''}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Trust + CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="relative rounded-3xl border border-vit-500/20 bg-gradient-to-br from-vit-500/10 via-surface-800/60 to-surface-800/40 p-12 text-center overflow-hidden">
          <div className="absolute inset-0 section-grid opacity-15" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-vit-500/8 blur-3xl" />
          <div className="relative">
            <Zap className="w-10 h-10 text-vit-400 mx-auto mb-4" />
             <p className="text-xs text-vit-300 uppercase tracking-[0.2em] mb-3">Public record</p>
             <h2 className="text-3xl font-medium tracking-[-0.05em] text-white/95 mb-3">See the signal. Check the record. Verify the outcome.</h2>
             <p className="text-white/60 max-w-md mx-auto mb-8">The platform is best used as a transparent prediction and monitoring layer, with clear status and evidence at every step.</p>
            <Link to="/status-page" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white font-medium transition-all shadow-xl shadow-vit-500/25">
              View live status <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
