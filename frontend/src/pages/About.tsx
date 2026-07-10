import { motion } from 'framer-motion'
import { Info, Globe, Shield, Cpu, Github } from 'lucide-react'

const PRINCIPLES = [
  {
    icon: Globe,
    title: 'Gateway Philosophy',
    body: 'VIT Network owns no business data. Every feature displayed must originate from the service that owns it. The gateway aggregates — it never duplicates.',
  },
  {
    icon: Shield,
    title: 'No Local Persistence',
    body: 'The frontend introduces zero local persistence. All data flows live from vit-ai, vit-storage, and future services through the gateway.',
  },
  {
    icon: Cpu,
    title: 'Service-First Architecture',
    body: 'Each service in the ecosystem is independently deployable and owns its data. The gateway exposes a unified API surface while preserving service autonomy.',
  },
]

export default function About() {
  return (
    <div className="pt-24 pb-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <div className="flex items-center gap-2 mb-3">
            <Info className="w-5 h-5 text-vit-400" />
            <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">About</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">VIT Network</h1>
          <p className="text-white/60 text-lg leading-relaxed max-w-2xl">
            VIT Network is an AI-powered decentralized platform gateway. It aggregates AI inference, object storage, blockchain, identity, wallet, and commerce services into a single unified interface.
          </p>
        </motion.div>

        {/* Mission */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/10 bg-white/5 p-8 mb-8"
        >
          <h2 className="text-xl font-bold text-white mb-3">Mission</h2>
          <p className="text-white/60 leading-relaxed">
            To provide a production-grade, service-oriented platform where each module owns its data and the gateway serves as the aggregation layer. VIT Network is built for reliability, transparency, and extensibility.
          </p>
        </motion.div>

        {/* Principles */}
        <div className="grid sm:grid-cols-3 gap-4 mb-10">
          {PRINCIPLES.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="rounded-xl border border-white/10 bg-white/5 p-5"
            >
              <div className="w-9 h-9 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center mb-4">
                <p.icon className="w-4.5 h-4.5 text-vit-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">{p.title}</h3>
              <p className="text-sm text-white/50 leading-relaxed">{p.body}</p>
            </motion.div>
          ))}
        </div>

        {/* Production info */}
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
        >
          <h2 className="text-lg font-bold text-white mb-4">Production Infrastructure</h2>
          <div className="grid sm:grid-cols-2 gap-3 text-sm">
            {[
              { label: 'Gateway',       value: 'vitnetwork (Docker / Render)' },
              { label: 'AI Service',    value: 'vit-ai (Docker / Render)' },
              { label: 'Storage',       value: 'vit-storage (Docker / Render)' },
              { label: 'Database',      value: 'PostgreSQL 16' },
              { label: 'Cache',         value: 'Valkey (Redis-compatible)' },
              { label: 'Environments',  value: 'Render Environment Groups' },
            ].map(row => (
              <div key={row.label} className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
                <span className="text-white/40 w-24 flex-shrink-0">{row.label}</span>
                <span className="text-white/80 font-medium">{row.value}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* GitHub */}
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="flex items-center gap-4 p-5 rounded-xl border border-white/10 bg-white/5"
        >
          <Github className="w-8 h-8 text-white/60" />
          <div className="flex-1">
            <p className="font-medium text-white">Open Source</p>
            <p className="text-sm text-white/50">nemesistip-cloud/vit</p>
          </div>
          <a
            href="https://github.com/nemesistip-cloud/vit"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white text-sm font-medium transition-colors"
          >
            View Repository
          </a>
        </motion.div>
      </div>
    </div>
  )
}
