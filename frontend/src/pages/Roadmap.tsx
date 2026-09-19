import { motion } from 'framer-motion'
import { Map, CheckCircle2, Circle, Clock, Wrench } from 'lucide-react'

const ROADMAP_META = {
  platformVersion: '1.2.0',
  frontendVersion: '2.0.0',
  verifiedOn: '19 September 2026',
}

const PHASES = [
  {
    phase: 'Now',
    title: 'Verified platform foundation',
    status: 'complete',
    items: [
      { label: 'FastAPI gateway, PostgreSQL, Redis and migrations', done: true },
      { label: 'React/Vite application and production Docker deployment', done: true },
      { label: 'Authentication, RBAC, admin diagnostics and health checks', done: true },
      { label: 'VIT Chain ledger, explorer integration and attestations', done: true },
      { label: 'Tachyon storage coordination and provider-backed workflows', done: true },
    ],
  },
  {
    phase: 'Current focus',
    title: 'Prediction integrity and live evidence',
    status: 'active',
    items: [
      { label: 'Provider-backed historical results and team feature samples', done: true },
      { label: 'Match Intelligence Profile with source provenance', done: true },
      { label: 'Fail-closed readiness gate for evidence and freshness', done: true },
      { label: 'Real ensemble path connected in production mode', done: true },
      { label: 'Live odds credentials and provider coverage', done: false },
      { label: 'Sports-provider lineage, calibration and drift verification', done: false },
      { label: 'Genuine data-sufficient production prediction run', done: false },
    ],
  },
  {
    phase: 'Next',
    title: 'Operational verification',
    status: 'active',
    items: [
      { label: 'Verify all live sports providers and current odds sources', done: false },
      { label: 'Publish prediction evidence snapshots and audit trails', done: false },
      { label: 'Verify background worker deployment and scheduled agents', done: false },
      { label: 'Complete browser and deployed endpoint coverage', done: false },
      { label: 'Add adversarial provider, timeout and restart tests', done: false },
    ],
  },
  {
    phase: 'Network next',
    title: 'Decentralization and storage proofs',
    status: 'planned',
    items: [
      { label: 'Onboard a second and third VIT Chain validator', done: false },
      { label: 'Verify quorum, consensus votes and restart synchronization', done: false },
      { label: 'Activate Tachyon-to-chain storage proof reporting', done: false },
      { label: 'Require real storage proofs from active storage validators', done: false },
    ],
  },
  {
    phase: 'Later',
    title: 'Ecosystem expansion',
    status: 'planned',
    items: [
      { label: 'Complete DID and Academic Passport flows', done: false },
      { label: 'Ship a public TypeScript SDK and developer documentation', done: false },
      { label: 'Harden durable exchange settlement and withdrawals', done: false },
      { label: 'Evaluate Render-to-GCP migration after production verification', done: false },
      { label: 'Define any future cross-chain settlement only after VIT Chain validation', done: false },
    ],
  },
]

const STATUS_STYLES = {
  complete:    { dot: 'bg-emerald-500',                         pill: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400', label: 'Complete'     },
  active:      { dot: 'bg-vit-500 animate-pulse',              pill: 'bg-vit-500/15 border-vit-500/30 text-vit-400',            label: 'Active'       },
  restoration: { dot: 'bg-amber-500',                          pill: 'bg-amber-500/15 border-amber-500/30 text-amber-400',      label: 'Restoration'  },
  planned:     { dot: 'bg-white/20',                           pill: 'bg-white/5 border-white/10 text-white/30',                label: 'Planned'      },
  partial:     { dot: 'bg-amber-500',                          pill: 'bg-amber-500/15 border-amber-500/30 text-amber-400',      label: 'Partially implemented' },
}

export default function Roadmap() {
  const done        = PHASES.filter(p => p.status === 'complete').length
  const active      = PHASES.filter(p => p.status === 'active').length
  const openItems   = PHASES.reduce((total, phase) => total + phase.items.filter(item => !item.done).length, 0)
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
              <h1 className="text-2xl font-bold text-white">VIT Network Roadmap</h1>
              <p className="text-white/50 text-sm">Verified delivery priorities and the next accountable milestones</p>
              <p className="text-white/30 text-xs mt-1">
                Platform v{ROADMAP_META.platformVersion} · Frontend v{ROADMAP_META.frontendVersion} · Verified {ROADMAP_META.verifiedOn}
              </p>
            </div>
          </motion.div>

          {/* Progress summary */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-4 gap-4">
            {[
              { label: 'Complete',    value: done,        color: 'text-emerald-400' },
              { label: 'Active',      value: active,      color: 'text-vit-400'     },
              { label: 'Open items',  value: openItems,  color: 'text-amber-400'   },
              { label: 'Planned',     value: planned,     color: 'text-white/30'    },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-white/40 mt-1">{label}</p>
              </div>
            ))}
          </motion.div>

          {/* Verification notice */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="mt-6 flex items-start gap-3 px-4 py-3.5 rounded-xl border border-amber-500/25 bg-amber-500/8">
            <Wrench className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-amber-300/80 leading-relaxed">
              <span className="font-semibold text-amber-300">Verified {ROADMAP_META.verifiedOn}.</span> Roadmap status reflects repository evidence and live service checks. A completed code path is not marked production-ready until its provider, runtime, and deployed behavior are verified.
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
               const isRestoration = phase.status === 'restoration' || phase.status === 'partial'

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
                         {phase.status === 'partial'     && <Wrench className="w-3 h-3" />}
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
