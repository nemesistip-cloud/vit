import { motion } from 'framer-motion'
import { BookOpen, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ENDPOINTS } from '@/lib/api'

const SECTIONS = [
  {
    title: 'Getting Started',
    items: [
      { title: 'Platform Overview',        anchor: '#overview',   desc: 'Architecture, services, and gateway philosophy.' },
      { title: 'Quick Start',              anchor: '#quickstart', desc: 'Your first API call in under 60 seconds.' },
      { title: 'Production Endpoints',     anchor: '#endpoints',  desc: 'Base URLs for all production services.' },
    ],
  },
  {
    title: 'API Reference',
    items: [
      { title: 'Gateway Health',     anchor: '#api', desc: 'GET /health — platform status and version.' },
      { title: 'AI Service',         anchor: '#api', desc: 'GET /health · /api/models — inference engine.' },
      { title: 'Storage Service',    anchor: '#api', desc: 'GET /health · /api/objects — object browser.' },
    ],
  },
  {
    title: 'Platform Guides',
    items: [
      { title: 'Service Discovery',  anchor: '#discovery',  desc: 'Automatic discovery of registered platform services.' },
      { title: 'Health Monitoring',  anchor: '#monitoring', desc: 'Integrating with the /health endpoints.' },
      { title: 'Frontend Integration', anchor: '#frontend', desc: 'Using TanStack Query against VIT services.' },
    ],
  },
]

const API_REFS = [
  { method: 'GET', path: '/health',          service: 'Gateway',     desc: 'Platform health, version, environment' },
  { method: 'GET', path: '/api/status',      service: 'Gateway',     desc: 'Detailed service status' },
  { method: 'GET', path: '/api/services',    service: 'Gateway',     desc: 'Registered service list' },
  { method: 'GET', path: '/health',          service: 'vit-ai',      desc: 'AI service health, model list, providers' },
  { method: 'GET', path: '/api/models',      service: 'vit-ai',      desc: 'Model registry' },
  { method: 'GET', path: '/api/status',      service: 'vit-ai',      desc: 'Inference engine status' },
  { method: 'GET', path: '/health',          service: 'vit-storage', desc: 'Storage health, capacity, object count' },
  { method: 'GET', path: '/api/objects',     service: 'vit-storage', desc: 'List all objects' },
  { method: 'GET', path: '/api/metrics',     service: 'vit-storage', desc: 'Storage metrics' },
]

const METHOD_COLORS: Record<string, string> = {
  GET:    'bg-emerald-400/15 text-emerald-400',
  POST:   'bg-blue-400/15 text-blue-400',
  DELETE: 'bg-red-400/15 text-red-400',
}

const SERVICE_URLS: Record<string, string> = {
  Gateway:      ENDPOINTS.gateway,
  'vit-ai':     ENDPOINTS.ai,
  'vit-storage': ENDPOINTS.storage,
}

export default function Documentation() {
  return (
    <div className="pt-24 pb-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-5 h-5 text-vit-400" />
            <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">Documentation</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">Platform Docs</h1>
          <p className="text-white/50 max-w-lg">Everything you need to integrate with the VIT Network platform.</p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* TOC */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 rounded-xl border border-white/10 bg-white/5 p-5">
              <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Contents</h3>
              <div className="space-y-4">
                {SECTIONS.map(section => (
                  <div key={section.title}>
                    <p className="text-xs text-vit-400 font-medium uppercase tracking-wider mb-2">{section.title}</p>
                    <div className="space-y-1">
                      {section.items.map(item => (
                        <a
                          key={item.title}
                          href={item.anchor}
                          className="flex items-center gap-2 text-sm text-white/60 hover:text-white hover:bg-white/5 px-2 py-1.5 rounded-lg transition-colors"
                        >
                          <ChevronRight className="w-3 h-3" />
                          {item.title}
                        </a>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="lg:col-span-2 space-y-10">
            <section id="overview">
              <h2 className="text-2xl font-bold text-white mb-3">Platform Overview</h2>
              <p className="text-white/60 leading-relaxed mb-4">
                VIT Network is an AI-powered decentralized platform gateway. It aggregates multiple owned services (vit-ai, vit-storage, and future modules) behind a single unified interface without duplicating their data or logic.
              </p>
              <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                <p className="text-sm font-mono text-vit-300">
                  Gateway ← owns no data, routes all requests to owning services
                </p>
              </div>
            </section>

            <section id="endpoints">
              <h2 className="text-2xl font-bold text-white mb-3">Production Endpoints</h2>
              <div className="space-y-2">
                {Object.entries(SERVICE_URLS).map(([name, url]) => (
                  <div key={name} className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10">
                    <span className="text-sm text-white/60 w-24">{name}</span>
                    <code className="text-sm font-mono text-vit-300 flex-1">{url}</code>
                  </div>
                ))}
              </div>
            </section>

            <section id="api">
              <h2 className="text-2xl font-bold text-white mb-3">API Reference</h2>
              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="w-full text-sm">
                  <thead className="bg-white/5">
                    <tr>
                      {['Method', 'Path', 'Service', 'Description'].map(h => (
                        <th key={h} className="text-left text-white/40 font-medium px-4 py-3">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {API_REFS.map((row, i) => (
                      <tr key={i} className="border-t border-white/5">
                        <td className="px-4 py-3">
                          <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${METHOD_COLORS[row.method] ?? ''}`}>
                            {row.method}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-vit-300 text-xs">
                          <a
                            href={`${SERVICE_URLS[row.service]}${row.path}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-vit-200 transition-colors"
                          >
                            {row.path}
                          </a>
                        </td>
                        <td className="px-4 py-3 text-white/60">{row.service}</td>
                        <td className="px-4 py-3 text-white/50">{row.desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section id="discovery">
              <h2 className="text-2xl font-bold text-white mb-3">Service Discovery</h2>
              <p className="text-white/60 leading-relaxed mb-4">
                The gateway automatically discovers registered services. Each service exposes its name, version, health status, response time, dependencies, and last heartbeat through the <code className="text-vit-300 font-mono text-sm">/api/services</code> endpoint.
              </p>
              <Link to="/platform" className="text-vit-400 hover:text-vit-300 text-sm flex items-center gap-1">
                View live service list on Platform page →
              </Link>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
