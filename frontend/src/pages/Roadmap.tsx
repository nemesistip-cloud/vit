import { motion } from 'framer-motion'
import { Map, CheckCircle2, Circle, Clock } from 'lucide-react'

const PHASES = [
  {
    phase: 'Phase I',
    title: 'Core Platform',
    status: 'complete',
    items: [
      { label: 'VIT Gateway (vitnetwork)', done: true },
      { label: 'vit-ai inference engine',   done: true },
      { label: 'vit-storage object layer',  done: true },
      { label: 'PostgreSQL 16 integration', done: true },
      { label: 'Valkey (Redis) caching',    done: true },
      { label: 'Health monitoring endpoints', done: true },
      { label: 'Docker production deployment', done: true },
      { label: 'Render environment groups',  done: true },
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
    status: 'active',
    items: [
      { label: 'VIT token wallet & balance',         done: true },
      { label: 'JWT auth with refresh tokens',       done: true },
      { label: 'Role-based access control (RBAC)',   done: true },
      { label: 'TOTP two-factor authentication',     done: true },
      { label: 'Reward accumulator & payouts',       done: false },
      { label: 'CLV tier system (Free → Pro → VIP)', done: false },
      { label: 'KYC screening pipeline',             done: false },
      { label: 'Withdrawal gatekeeper agent',        done: false },
    ],
  },
  {
    phase: 'Phase IV',
    title: 'Blockchain & On-Chain Verification',
    status: 'active',
    items: [
      { label: 'VIT chain ledger (vit_chain)',        done: true },
      { label: 'Block explorer UI',                  done: true },
      { label: 'Transaction indexing',               done: true },
      { label: 'Node map & network stats',           done: true },
      { label: 'On-chain prediction attestation',    done: false },
      { label: 'Trustless payout verification',      done: false },
      { label: 'Smart contract integration layer',   done: false },
      { label: 'Multi-chain routing in gateway',     done: false },
    ],
  },
  {
    phase: 'Phase V',
    title: 'Governance & DAO',
    status: 'planned',
    items: [
      { label: 'Proposal creation & voting',         done: false },
      { label: 'On-chain governance execution',      done: false },
      { label: 'Validator staking & slashing',       done: false },
      { label: 'Treasury management module',         done: false },
    ],
  },
  {
    phase: 'Phase VI',
    title: 'Commerce & Marketplace',
    status: 'planned',
    items: [
      { label: 'Decentralised prediction marketplace', done: false },
      { label: 'Peer-to-peer tip trading',             done: false },
      { label: 'Affiliate & referral engine',          done: false },
      { label: 'Commerce API surface',                 done: false },
    ],
  },
  {
    phase: 'Phase VII',
    title: 'Mobile & Ecosystem Expansion',
    status: 'planned',
    items: [
      { label: 'vit-mobile React Native app',        done: false },
      { label: 'Push notifications (Firebase)',      done: false },
      { label: 'Telegram bot integration',           done: false },
      { label: 'SDK & third-party developer API',    done: false },
      { label: 'Asset CDN via vit-storage',          done: false },
      { label: 'Service discovery integration',      done: false },
    ],
  },
]

const STATUS_STYLES = {
  complete: { pill: 'bg-emerald-400/15 text-emerald-400 border-emerald-400/30', dot: 'bg-emerald-400', label: 'Complete' },
  active:   { pill: 'bg-vit-400/15 text-vit-400 border-vit-400/30',            dot: 'bg-vit-400 animate-pulse', label: 'In Progress' },
  planned:  { pill: 'bg-white/10 text-white/50 border-white/10',                dot: 'bg-white/30', label: 'Planned' },
}

export default function Roadmap() {
  return (
    <div className="pt-24 pb-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-16">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Map className="w-5 h-5 text-vit-400" />
            <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">Roadmap</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">Platform Roadmap</h1>
          <p className="text-white/50 max-w-lg mx-auto">
            From a healthy backend to a full decentralised prediction & intelligence ecosystem. Each phase adds owned services to the gateway.
          </p>
        </motion.div>

        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[22px] top-6 bottom-6 w-0.5 bg-gradient-to-b from-emerald-400 via-vit-500 to-white/10" />

          <div className="space-y-8">
            {PHASES.map((phase, i) => {
              const style = STATUS_STYLES[phase.status as keyof typeof STATUS_STYLES]
              return (
                <motion.div
                  key={phase.phase}
                  initial={{ opacity: 0, x: -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06 }}
                  className="flex gap-6"
                >
                  {/* Dot */}
                  <div className="flex-shrink-0 mt-1 flex items-start justify-center w-11">
                    <div className={`w-4 h-4 rounded-full border-2 border-surface-900 ${style.dot}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 rounded-xl border border-white/10 bg-white/5 p-5 mb-2">
                    <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
                      <div>
                        <span className="text-xs text-white/40 font-mono">{phase.phase}</span>
                        <h3 className="text-lg font-bold text-white">{phase.title}</h3>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${style.pill}`}>
                        {phase.status === 'complete' && <CheckCircle2 className="w-3 h-3" />}
                        {phase.status === 'active'   && <Clock className="w-3 h-3" />}
                        {phase.status === 'planned'  && <Circle className="w-3 h-3" />}
                        {style.label}
                      </span>
                    </div>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {phase.items.map(item => (
                        <div key={item.label} className="flex items-center gap-2.5 text-sm">
                          {item.done ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          ) : (
                            <Circle className="w-4 h-4 text-white/20 flex-shrink-0" />
                          )}
                          <span className={item.done ? 'text-white/70' : 'text-white/30'}>{item.label}</span>
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
