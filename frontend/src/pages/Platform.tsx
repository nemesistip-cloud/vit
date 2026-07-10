import { motion } from 'framer-motion'
import { Server, Cpu, Globe, GitBranch, Shield, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAllHealth } from '@/hooks/useHealth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Spinner } from '@/components/ui/Spinner'
import { StatCard } from '@/components/StatCard'
import { formatUptime } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'

const ARCHITECTURE = [
  {
    layer: 'Gateway',
    name: 'vitnetwork',
    description: 'The single entry point. Routes requests to owning services, aggregates health, and exposes the unified API surface.',
    icon: Globe,
  },
  {
    layer: 'Core Platform',
    name: 'vit-ai + vit-storage',
    description: 'Owned services that hold business data. Each service exposes its own API and health endpoint consumed by the gateway.',
    icon: Cpu,
  },
  {
    layer: 'Infrastructure',
    name: 'PostgreSQL 16 + Valkey',
    description: 'Persistent storage (PostgreSQL 16) and ephemeral caching (Valkey/Redis). Shared across platform services.',
    icon: Server,
  },
  {
    layer: 'Future Modules',
    name: 'Blockchain · Wallet · Identity · Commerce',
    description: 'Each future service will register with the gateway and own its data. The gateway never duplicates — it aggregates.',
    icon: GitBranch,
  },
]

export default function Platform() {
  const { gateway, ai, storage, isLoading } = useAllHealth()

  return (
    <div className="pt-24 pb-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Hero */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-16">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Server className="w-5 h-5 text-vit-400" />
            <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">Platform</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4">
            Production Infrastructure
          </h1>
          <p className="text-white/50 max-w-xl mx-auto leading-relaxed">
            The VIT platform is deployed on Render with Docker-backed services, PostgreSQL 16, and Valkey caching. The gateway aggregates — it never duplicates.
          </p>
        </motion.div>

        {/* Live stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          {[
            { label: 'Gateway',     value: gateway.data?.status ?? '—', icon: Globe },
            { label: 'vit-ai',      value: ai.data?.status ?? '—',      icon: Cpu },
            { label: 'vit-storage', value: storage.data?.status ?? '—', icon: Shield },
            { label: 'Uptime',      value: gateway.data?.uptime ? formatUptime(gateway.data.uptime) : '—', icon: Server },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Live service table */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-10"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-white">Production Services</h2>
            {isLoading && <Spinner className="w-4 h-4" />}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  {['Service', 'Status', 'Version', 'Latency', 'Endpoint'].map(h => (
                    <th key={h} className="text-left text-white/40 font-medium pb-3 pr-6">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { name: 'vitnetwork (Gateway)', data: gateway.data, url: ENDPOINTS.gateway },
                  { name: 'vit-ai',               data: ai.data,      url: ENDPOINTS.ai },
                  { name: 'vit-storage',           data: storage.data, url: ENDPOINTS.storage },
                ].map(row => (
                  <tr key={row.name} className="border-b border-white/5 last:border-0">
                    <td className="py-3 pr-6 font-medium text-white">{row.name}</td>
                    <td className="py-3 pr-6">
                      {isLoading ? <Spinner className="w-3.5 h-3.5" /> : <StatusBadge status={row.data?.status} size="sm" pulse />}
                    </td>
                    <td className="py-3 pr-6 font-mono text-white/60 text-xs">{row.data?.version ?? '—'}</td>
                    <td className="py-3 pr-6 font-mono text-vit-400 text-xs">{row.data?._latency != null ? `${row.data._latency}ms` : '—'}</td>
                    <td className="py-3 pr-6">
                      <a href={`${row.url}/health`} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-vit-400 hover:text-vit-300 font-mono truncate block max-w-[180px]">
                        {row.url}/health
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Architecture */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6">Architecture</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {ARCHITECTURE.map((a, i) => (
              <motion.div
                key={a.layer}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.07 }}
                className="rounded-xl border border-white/10 bg-white/5 p-5"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
                    <a.icon className="w-4.5 h-4.5 text-vit-400" />
                  </div>
                  <div>
                    <p className="text-xs text-vit-400 uppercase tracking-wider font-medium">{a.layer}</p>
                    <p className="font-semibold text-white text-sm">{a.name}</p>
                  </div>
                </div>
                <p className="text-sm text-white/50 leading-relaxed">{a.description}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="flex gap-4 flex-wrap">
          <Link to="/status" className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-vit-600 hover:bg-vit-500 text-white font-medium transition-colors">
            Live Status <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/docs" className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 text-white font-medium transition-colors">
            API Documentation
          </Link>
        </div>
      </div>
    </div>
  )
}
