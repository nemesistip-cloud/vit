import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Brain, Database, Shield, Zap, Globe, ArrowRight,
  Activity, Server, HardDrive, Cpu, Lock, GitBranch,
} from 'lucide-react'
import { useAllHealth } from '@/hooks/useHealth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ServiceCard } from '@/components/ServiceCard'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { formatUptime } from '@/lib/utils'

const ECOSYSTEM = [
  {
    name: 'vit-ai',
    description: 'Multi-provider AI inference engine. Access leading language models with unified latency tracking and model registry.',
    icon: Brain,
    href: '/ai',
  },
  {
    name: 'vit-storage',
    description: 'Decentralized object storage layer. Upload, browse, download, and manage assets at platform scale.',
    icon: HardDrive,
    href: '/storage',
  },
  {
    name: 'Blockchain (coming)',
    description: 'Distributed ledger integration for trustless transactions and on-chain verification.',
    icon: GitBranch,
    href: '/roadmap',
    comingSoon: true,
  },
  {
    name: 'Identity (coming)',
    description: 'Decentralized identity layer with verifiable credentials and privacy-preserving authentication.',
    icon: Lock,
    href: '/roadmap',
    comingSoon: true,
  },
  {
    name: 'Wallet (coming)',
    description: 'Multi-chain wallet integration enabling seamless value transfer across the VIT ecosystem.',
    icon: Shield,
    href: '/roadmap',
    comingSoon: true,
  },
  {
    name: 'Commerce (coming)',
    description: 'Decentralized commerce layer powering peer-to-peer transactions and marketplace primitives.',
    icon: Globe,
    href: '/roadmap',
    comingSoon: true,
  },
]

const FEATURES = [
  { icon: Zap,      label: 'Sub-100ms inference',    sub: 'Optimized AI pipelines' },
  { icon: Shield,   label: 'Zero local persistence',  sub: 'Data owned by services' },
  { icon: Globe,    label: 'Global distribution',     sub: 'Edge-ready architecture' },
  { icon: Activity, label: 'Real-time monitoring',    sub: 'Live health dashboards' },
]

export default function Home() {
  const { gateway, ai, storage, isLoading, overallStatus } = useAllHealth()

  return (
    <div className="pt-16">
      {/* ── Hero ── */}
      <section className="relative overflow-hidden min-h-[90vh] flex items-center">
        {/* Grid background */}
        <div className="absolute inset-0 section-grid opacity-60" />
        {/* Radial glow */}
        <div className="absolute inset-0 bg-radial-vit" />
        {/* Gradient fade bottom */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-surface-900 to-transparent" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-24 text-center">
          {/* Live status pill */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm text-sm mb-8"
          >
            {isLoading ? (
              <Spinner className="w-3.5 h-3.5" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_theme(colors.emerald.400)]" />
            )}
            <span className="text-white/70">Platform</span>
            <StatusBadge status={overallStatus === 'loading' ? undefined : overallStatus} size="sm" />
            <span className="text-white/40">·</span>
            <span className="text-white/50 text-xs font-mono">v{gateway.data?.version ?? '—'}</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight text-white mb-6"
          >
            The AI-Powered
            <br />
            <span className="bg-gradient-to-r from-vit-300 via-vit-400 to-vit-600 bg-clip-text text-transparent">
              Decentralized Gateway
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-lg sm:text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            VIT Network aggregates AI inference, decentralized storage, blockchain, identity,
            and commerce services into a single unified gateway. Every feature originates from
            the service that owns it.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link
              to="/developers"
              className="px-6 py-3 rounded-xl bg-vit-600 hover:bg-vit-500 text-white font-semibold transition-all shadow-lg shadow-vit-600/30 hover:shadow-vit-500/40 flex items-center gap-2"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/platform"
              className="px-6 py-3 rounded-xl border border-white/20 hover:border-white/30 bg-white/5 hover:bg-white/10 text-white font-semibold transition-all"
            >
              View Platform
            </Link>
          </motion.div>

          {/* Live service indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-6 mt-14 text-sm"
          >
            {[
              { label: 'Gateway',  status: gateway.data?.status,  latency: gateway.data?._latency },
              { label: 'AI',       status: ai.data?.status,       latency: ai.data?._latency },
              { label: 'Storage',  status: storage.data?.status,  latency: storage.data?._latency },
            ].map(svc => (
              <div key={svc.label} className="flex items-center gap-2 text-white/50">
                <span
                  className={`w-2 h-2 rounded-full ${svc.status?.toLowerCase() === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-white/20'}`}
                />
                <span>{svc.label}</span>
                {svc.latency !== undefined && (
                  <span className="font-mono text-xs text-vit-400">{svc.latency}ms</span>
                )}
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Platform Stats ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Platform Status',   value: gateway.data?.status ?? '—', icon: Activity },
            { label: 'Environment',        value: gateway.data?.environment ?? '—', icon: Globe },
            { label: 'Gateway Latency',    value: gateway.data?._latency != null ? `${gateway.data._latency}ms` : '—', icon: Zap },
            { label: 'Uptime',             value: gateway.data?.uptime ? formatUptime(gateway.data.uptime) : '—', icon: Server },
          ].map((s, i) => (
            <StatCard key={s.label} {...s} index={i} />
          ))}
        </div>
      </section>

      {/* ── Ecosystem ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="text-center mb-12">
          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl sm:text-4xl font-bold text-white mb-4"
          >
            Ecosystem Overview
          </motion.h2>
          <p className="text-white/50 max-w-xl mx-auto">
            Every service in the VIT ecosystem owns its data. The gateway aggregates — it never duplicates.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {ECOSYSTEM.map((svc, i) => {
            const health = svc.name === 'vit-ai' ? ai.data : svc.name === 'vit-storage' ? storage.data : undefined
            return (
              <ServiceCard
                key={svc.name}
                name={svc.name}
                description={svc.description}
                icon={svc.icon}
                status={svc.comingSoon ? 'coming soon' : health?.status}
                version={health?.version}
                latency={health?._latency}
                isLoading={isLoading && !svc.comingSoon}
                href={svc.href}
                index={i}
              />
            )
          })}
        </div>
      </section>

      {/* ── Service Health ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">Service Health</h2>
              <p className="text-sm text-white/50">Live data from production</p>
            </div>
            <Link to="/status" className="text-sm text-vit-400 hover:text-vit-300 flex items-center gap-1">
              Full status <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'VIT Gateway',   status: gateway.data?.status,           latency: gateway.data?._latency },
              { label: 'vit-ai',        status: ai.data?.status,                latency: ai.data?._latency },
              { label: 'vit-storage',   status: storage.data?.status,           latency: storage.data?._latency },
              { label: 'PostgreSQL',    status: (gateway.data as any)?.postgres?.status ?? gateway.data?.status },
            ].map(row => (
              <div key={row.label} className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10">
                <div>
                  <p className="text-sm font-medium text-white">{row.label}</p>
                  {row.latency !== undefined && (
                    <p className="text-xs font-mono text-vit-400 mt-0.5">{row.latency}ms</p>
                  )}
                </div>
                {isLoading ? <Spinner className="w-3.5 h-3.5" /> : <StatusBadge status={row.status} size="sm" pulse />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="p-6 rounded-xl border border-white/10 bg-white/5 text-center"
            >
              <div className="w-12 h-12 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center mx-auto mb-4">
                <f.icon className="w-6 h-6 text-vit-400" />
              </div>
              <h3 className="font-semibold text-white mb-1">{f.label}</h3>
              <p className="text-sm text-white/50">{f.sub}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Developer CTA ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative rounded-2xl overflow-hidden border border-vit-500/30 bg-gradient-to-br from-vit-900/60 to-vit-950/80 p-10 text-center"
        >
          <div className="absolute inset-0 section-grid opacity-30" />
          <div className="relative">
            <Cpu className="w-10 h-10 text-vit-400 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-white mb-3">Build on VIT Network</h2>
            <p className="text-white/60 max-w-md mx-auto mb-8">
              Integrate AI inference, storage, and future services through a single gateway API.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/docs"
                className="px-6 py-3 rounded-xl bg-vit-600 hover:bg-vit-500 text-white font-semibold transition-all shadow-lg shadow-vit-600/30"
              >
                View Documentation
              </Link>
              <Link
                to="/developers"
                className="px-6 py-3 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 text-white font-semibold transition-all"
              >
                Developer Hub
              </Link>
            </div>
          </div>
        </motion.div>
      </section>
    </div>
  )
}
