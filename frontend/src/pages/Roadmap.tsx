import { motion } from 'framer-motion'
import { Map, CheckCircle2, Circle, Clock, Wrench } from 'lucide-react'

const PHASES = [
  {
    phase: 'Phase I',
    title: 'Core Platform',
    status: 'complete',
    items: [
      { label: 'VIT Gateway (vitnetwork)',         done: true },
      { label: 'vit-ai inference engine',          done: true },
      { label: 'vit-storage object layer',         done: true },
      { label: 'PostgreSQL 16 integration',        done: true },
      { label: 'Valkey (Redis) caching',           done: true },
      { label: 'Health monitoring endpoints',      done: true },
      { label: 'Docker production deployment',     done: true },
      { label: 'Render environment groups',        done: true },
    ],
  },
  {
    phase: 'Phase II',
    title: 'Frontend & Intelligence Layer',
    status: 'complete',
    items: [
      { label: 'React + Vite + TypeScript frontend', done: true },
      { label: 'TailwindCSS design system',          done: true },
      { label: 'Live service health dashboard',      done: true },
      { label: 'AI model registry UI',               done: true },
      { label: 'Storage object browser',             done: true },
      { label: 'Matches & fixture system',           done: true },
      { label: 'AI-powered prediction engine',       done: true },
      { label: 'Leaderboard & scoring system',       done: true },
    ],
  },
  {
    phase: 'Phase III',
    title: 'Wallet, Identity & Rewards',
    status: 'complete',
    items: [
      { label: 'VIT token wallet & balance',          done: true },
      { label: 'JWT auth with refresh tokens',        done: true },
      { label: 'Role-based access control (RBAC)',    done: true },
      { label: 'TOTP two-factor authentication',      done: true },
      { label: 'Reward accumulator & payouts',        done: true },
      { label: 'CLV tier system (Viewer → Elite)',    done: true },
      { label: 'KYC screening pipeline',              done: true },
      { label: 'Withdrawal gatekeeper agent',         done: true },
    ],
  },
  {
    phase: 'Phase IV',
    title: 'Blockchain & On-Chain Verification',
    status: 'complete',
    items: [
      { label: 'VIT chain ledger (vit_chain)',         done: true },
      { label: 'Block explorer UI',                   done: true },
      { label: 'Transaction indexing',                done: true },
      { label: 'Node map & network stats',            done: true },
      { label: 'On-chain prediction attestation',     done: true },
      { label: 'Smart contract module (SimpleVM)',     done: true },
      { label: 'Trustless payout verification',       done: true },
      { label: 'Multi-chain routing in gateway',      done: true },
    ],
  },
  {
    phase: 'Phase V',
    title: 'Governance & DAO',
    status: 'complete',
    items: [
      { label: 'Proposal creation & voting',          done: true },
      { label: 'On-chain governance execution',       done: true },
      { label: 'Validator staking & slashing',        done: true },
      { label: 'Treasury management module',          done: true },
    ],
  },
  {
    phase: 'Phase VI',
    title: 'Commerce & Marketplace',
    status: 'complete',
    items: [
      { label: 'Decentralised prediction marketplace', done: true },
      { label: 'Peer-to-peer tip trading',             done: true },
      { label: 'Affiliate & referral engine',          done: true },
      { label: 'Commerce API surface',                 done: true },
    ],
  },
  {
    phase: 'Phase VII',
    title: 'Mobile & Ecosystem Expansion',
    status: 'complete',
    items: [
      { label: 'vit-mobile React Native app',          done: true },
      { label: 'Push notifications (Firebase)',        done: true },
      { label: 'Telegram bot integration',             done: true },
      { label: 'SDK & third-party developer API',      done: true },
      { label: 'Asset CDN via vit-storage',            done: true },
    ],
  },
  {
    phase: 'Phase VIII',
    title: 'DeFi, Social & Enterprise',
    status: 'active',
    items: [
      { label: 'Social prediction feed (follow, react, comment)', done: true },
      { label: 'DeFi yield & liquidity pools',                    done: true },
      { label: 'Live in-play prediction markets',                 done: true },
      { label: 'Analytics Studio (personal + model comparison)',  done: true },
      { label: 'Enterprise API, data licensing & webhooks',       done: true },
    ],
  },
  {
    phase: 'Phase IX',
    title: 'Platform Integrity & Auth Restoration',
    status: 'restoration',
    items: [
      { label: 'Global error boundary (no blank-screen crashes)',  done: false },
      { label: 'Real 404 Not Found page (replace silent redirect)', done: false },
      { label: 'Toast notification system across all mutations',   done: false },
      { label: 'Footer rebuilt with all 30+ pages linked',         done: false },
      { label: 'Forgot password / reset password flows',           done: false },
      { label: 'Email verification flow',                          done: false },
      { label: 'User settings (profile, notifications, 2FA)',      done: false },
      { label: 'Subscription & pricing page (Free → Elite tiers)', done: false },
      { label: 'Governance & Marketplace added to public nav',     done: false },
      { label: 'Dashboard quick actions expanded (4 → 8 tiles)',   done: false },
    ],
  },
  {
    phase: 'Phase X',
    title: 'Predictions, Analytics & Tools Restoration',
    status: 'restoration',
    items: [
      { label: 'Match Detail with intelligence panels (ConsensusPanel, TacticalRadar, ModelBreakdown)', done: false },
      { label: 'Network Intelligence analytics dashboard (Recharts)',        done: false },
      { label: 'Live odds comparison (multi-bookmaker, 2-min refresh)',      done: false },
      { label: 'Validators management UI (apply, stake, slashing history)', done: false },
      { label: 'AI Assistant chat page (streaming, suggested prompts)',      done: false },
      { label: 'Accumulator builder (multi-leg, EV, conflict detection)',    done: false },
      { label: 'Rollover engine (fixture certification, conflict severity)', done: false },
      { label: 'Backtest (historical simulation with P&L curve chart)',      done: false },
      { label: 'Bankroll manager (Kelly Criterion, drawdown tracker)',       done: false },
      { label: 'Tasks & gamification (XP, level, claim rewards)',           done: false },
    ],
  },
  {
    phase: 'Phase XI',
    title: 'Financial Flows & Admin Suite Restoration',
    status: 'restoration',
    items: [
      { label: 'Wallet deposit — Paystack, Mobile Money, Crypto',            done: false },
      { label: 'Wallet withdraw with KYC gating',                            done: false },
      { label: 'Wallet sub-flows — P2P exchange, Bridge, Staking, Vaults',  done: false },
      { label: 'VITCoin buy/sell with price chart, Currency convert',        done: false },
      { label: 'Real-time notification bell (predictions, wallet, votes)',   done: false },
      { label: 'Global search — ⌘K across matches, predictions, users',     done: false },
      { label: 'Admin multi-page suite (Users, Wallet, Matches, Validators, Models, Config, Audit, System)', done: false },
      { label: 'shadcn/ui component library adopted across all pages',       done: false },
      { label: 'Subscription freemium gating via /config/public',           done: false },
      { label: 'PWA restoration (service worker, install prompt)',           done: false },
    ],
  },
  {
    phase: 'Phase XII',
    title: 'Cross-Chain & Institutional Scale',
    status: 'planned',
    items: [
      { label: 'Cross-chain liquidity bridges (ETH, BNB, Polygon)', done: false },
      { label: 'Institutional oracle SLA (99.9% uptime guarantee)', done: false },
      { label: 'On-chain DeFi settlement via vit-contracts',         done: false },
      { label: 'AI model marketplace (buy/sell model access)',        done: false },
      { label: 'ZK-proof prediction attestation',                    done: false },
      { label: 'Navbar category flyouts (Earn / Predict / Govern)',  done: false },
      { label: 'KYC compliance gating on all financial flows',       done: false },
    ],
  },
]

const STATUS_STYLES = {
  complete:    { dot: 'bg-emerald-500',                         pill: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400', label: 'Complete'     },
  active:      { dot: 'bg-vit-500 animate-pulse',              pill: 'bg-vit-500/15 border-vit-500/30 text-vit-400',            label: 'Active'       },
  restoration: { dot: 'bg-amber-500',                          pill: 'bg-amber-500/15 border-amber-500/30 text-amber-400',      label: 'Restoration'  },
  planned:     { dot: 'bg-white/20',                           pill: 'bg-white/5 border-white/10 text-white/30',                label: 'Planned'      },
}

export default function Roadmap() {
  const done        = PHASES.filter(p => p.status === 'complete').length
  const active      = PHASES.filter(p => p.status === 'active').length
  const restoration = PHASES.filter(p => p.status === 'restoration').length
  const planned     = PHASES.filter(p => p.status === 'planned').length

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Map className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Platform Roadmap</h1>
              <p className="text-white/50 text-sm">Live development progress across all VIT Network phases</p>
            </div>
          </motion.div>

          {/* Progress summary */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-4 gap-4">
            {[
              { label: 'Complete',    value: done,        color: 'text-emerald-400' },
              { label: 'Active',      value: active,      color: 'text-vit-400'     },
              { label: 'Restoration', value: restoration, color: 'text-amber-400'   },
              { label: 'Planned',     value: planned,     color: 'text-white/30'    },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-white/40 mt-1">{label}</p>
              </div>
            ))}
          </motion.div>

          {/* Restoration notice */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="mt-6 flex items-start gap-3 px-4 py-3.5 rounded-xl border border-amber-500/25 bg-amber-500/8">
            <Wrench className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-amber-300/80 leading-relaxed">
              <span className="font-semibold text-amber-300">Restoration phases (IX–XI)</span> integrate 52 pages and 172 components from the institutional-grade frontend that pre-dated the Phase II gateway rebuild — including match intelligence panels, full wallet flows, admin suite, analytics with charts, and gamification.
            </p>
          </motion.div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-5 top-2 bottom-2 w-px bg-gradient-to-b from-emerald-500/40 via-vit-500/30 via-amber-500/20 to-white/5" />

          <div className="space-y-6">
            {PHASES.map((phase, i) => {
              const style = STATUS_STYLES[phase.status as keyof typeof STATUS_STYLES] ?? STATUS_STYLES.planned
              const isRestoration = phase.status === 'restoration'

              return (
                <motion.div
                  key={phase.phase}
                  initial={{ opacity: 0, x: -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                  className="flex gap-6"
                >
                  {/* Dot */}
                  <div className="flex-shrink-0 mt-1 flex items-start justify-center w-11">
                    <div className={`w-4 h-4 rounded-full border-2 border-surface-900 ${style.dot}`} />
                  </div>

                  {/* Content */}
                  <div className={`flex-1 rounded-xl border p-5 mb-2 ${
                    isRestoration
                      ? 'border-amber-500/20 bg-amber-500/5'
                      : 'border-white/10 bg-white/5'
                  }`}>
                    <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
                      <div>
                        <span className="text-xs text-white/40 font-mono">{phase.phase}</span>
                        <h3 className="text-lg font-bold text-white">{phase.title}</h3>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${style.pill}`}>
                        {phase.status === 'complete'    && <CheckCircle2 className="w-3 h-3" />}
                        {phase.status === 'active'      && <Clock className="w-3 h-3" />}
                        {phase.status === 'restoration' && <Wrench className="w-3 h-3" />}
                        {phase.status === 'planned'     && <Circle className="w-3 h-3" />}
                        {style.label}
                      </span>
                    </div>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {phase.items.map(item => (
                        <div key={item.label} className="flex items-start gap-2.5 text-sm">
                          {item.done ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                          ) : isRestoration ? (
                            <Wrench className="w-4 h-4 text-amber-500/50 flex-shrink-0 mt-0.5" />
                          ) : (
                            <Circle className="w-4 h-4 text-white/20 flex-shrink-0 mt-0.5" />
                          )}
                          <span className={item.done ? 'text-white/70' : isRestoration ? 'text-amber-200/50' : 'text-white/30'}>
                            {item.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
