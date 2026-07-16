import { motion } from 'framer-motion'
import { Code, Zap, Terminal, Copy, CheckCheck, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { ENDPOINTS } from '@/lib/api'

function CodeBlock({ code, lang = 'bash' }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="relative rounded-lg bg-black/40 border border-white/10 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <span className="text-xs text-white/40 font-mono">{lang}</span>
        <button onClick={copy} className="text-white/40 hover:text-white transition-colors">
          {copied ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>
      <pre className="p-4 text-sm font-mono text-white/80 overflow-x-auto whitespace-pre-wrap">{code}</pre>
    </div>
  )
}

const QUICK_STARTS = [
  {
    title: 'Platform Health',
    description: 'Check if the VIT gateway is healthy',
    code: `curl ${ENDPOINTS.gateway}/health`,
  },
  {
    title: 'AI Service Health',
    description: 'Query the vit-ai inference engine',
    code: `curl ${ENDPOINTS.ai}/health`,
  },
  {
    title: 'Storage Health',
    description: 'Check vit-storage availability',
    code: `curl ${ENDPOINTS.storage}/health`,
  },
  {
    title: 'List Storage Objects',
    description: 'Browse objects in vit-storage',
    code: `curl ${ENDPOINTS.storage}/api/objects`,
  },
]

export default function Developers() {
  return (
    <div className="pt-24 pb-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <div className="flex items-center gap-2 mb-3">
            <Code className="w-5 h-5 text-vit-400" />
            <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">Developer Hub</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">Build on VIT Network</h1>
          <p className="text-white/50 max-w-lg leading-relaxed">
            Integrate directly with production services. The gateway is the single point of entry — all data flows from the owning service.
          </p>
        </motion.div>

        {/* Base URLs */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6 mb-8"
        >
          <div className="flex items-center gap-2 mb-4">
            <Terminal className="w-4 h-4 text-vit-400" />
            <h2 className="text-lg font-semibold text-white">Production Endpoints</h2>
          </div>
          <div className="space-y-3">
            {[
              { label: 'Gateway',     url: ENDPOINTS.gateway },
              { label: 'vit-ai',      url: ENDPOINTS.ai },
              { label: 'vit-storage', url: ENDPOINTS.storage },
            ].map(e => (
              <div key={e.label} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
                <span className="text-sm text-white/60 w-24">{e.label}</span>
                <code className="text-sm font-mono text-vit-300 flex-1 px-3">{e.url}</code>
                <a href={`${e.url}/health`} target="_blank" rel="noopener noreferrer"
                  className="text-white/40 hover:text-white transition-colors">
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Quick-start examples */}
        <h2 className="text-xl font-bold text-white mb-5 flex items-center gap-2">
          <Zap className="w-5 h-5 text-vit-400" /> Quick Start
        </h2>
        <div className="space-y-6 mb-10">
          {QUICK_STARTS.map((q, i) => (
            <motion.div
              key={q.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.07 }}
            >
              <h3 className="text-base font-semibold text-white mb-1">{q.title}</h3>
              <p className="text-sm text-white/50 mb-3">{q.description}</p>
              <CodeBlock code={q.code} />
            </motion.div>
          ))}
        </div>

        {/* Expected response */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
          className="mb-10"
        >
          <h2 className="text-xl font-bold text-white mb-4">Health Response Shape</h2>
          <CodeBlock lang="json" code={`{
  "name": "VIT Platform",
  "status": "healthy",
  "version": "1.1.0",
  "environment": "production"
}`} />
        </motion.div>

        {/* Gateway philosophy */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}
          className="rounded-xl border border-vit-500/20 bg-vit-500/5 p-6"
        >
          <h2 className="text-lg font-semibold text-white mb-3">Gateway Philosophy</h2>
          <p className="text-white/60 text-sm leading-relaxed mb-4">
            VIT Network owns no business data. Every feature displayed must originate from the owning service.
            The gateway aggregates — it never duplicates. When building integrations, always call the service
            that owns the data directly through the gateway.
          </p>
          <div className="grid sm:grid-cols-2 gap-3 font-mono text-xs">
            {[
              { from: 'AI inference',   to: 'vit-ai' },
              { from: 'File storage',   to: 'vit-storage' },
              { from: 'Blockchain',     to: 'blockchain service (future)' },
              { from: 'Identity',       to: 'identity service (future)' },
            ].map(r => (
              <div key={r.from} className="flex items-center gap-2 text-white/50">
                <span className="text-white/80">{r.from}</span>
                <span className="text-vit-500">→</span>
                <span className="text-vit-300">{r.to}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
