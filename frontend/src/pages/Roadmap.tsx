import { motion } from 'framer-motion'
import { Map, CheckCircle2, Circle, Clock } from 'lucide-react'

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
    status: 'active',
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
    status: 'active',
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
    status: 'planned',
    items: [
      { label: 'vit-mobile React Native app',          done: false },
      { label: 'Push notifications (Firebase)',        done: false },
      { label: 'Telegram bot integration',             done: false },
      { label: 'SDK & third-party developer API',      done: false },
      { label: 'Asset CDN via vit-storage',            done: false },
    ],
  },
]

const STATUS_STYLES = {
  complete: { dot: 'bg-emerald-500',  pill: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400', label: 'Complete'  },
  active:   { dot: 'bg-vit-500 animate-pulse', pill: 'bg-vit-500/15 border-vit-500/30 text-vit-400', label: 'Active'    },
  planned:  { dot: 'bg-white/20',     pill: 'bg-white/5 border-white/10 text-white/30',               label: 'Planned'   },
}

export default function Roadmap() {
  const done    = PHASES.filter(p => p.status === 'complete').length
  const active  = PHASES.filter(p => p.status === 'active').length
  const planned = PHASES.filter(p => p.status === 'planned').length

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
            className="grid grid-cols-3 gap-4">
            {[
              { label: 'Phases Complete', value: done,    color: 'text-emerald-400' },
              { label: 'In Progress',     value: active,  color: 'text-vit-400'    },
              { label: 'Planned',         value: planned, color: 'text-white/30'   },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-white/40 mt-1">{label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-5 top-2 bottom-2 w-px bg-gradient-to-b from-emerald-500/40 via-vit-500/30 to-white/5" />

          <div className="space-y-6">
            {PHASES.map((phase, i) => {
              const style = STATUS_STYLES[phase.status as keyof typeof STATUS_STYLES] ?? STATUS_STYLES.planned
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
