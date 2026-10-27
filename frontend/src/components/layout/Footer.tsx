import { Link } from 'react-router-dom'
import { Github, Twitter, ExternalLink, Zap, Shield, Globe } from 'lucide-react'
import { useGatewayHealth } from '@/hooks/useHealth'
import { FOOTER_LEGAL_LINKS, FOOTER_NAVIGATION_GROUPS, ROUTES } from '@/lib/navigation'

// ── Link columns ──────────────────────────────────────────────────────────────

const SOCIALS = [
  { href: 'https://github.com/vitnetwork', icon: Github,  label: 'GitHub' },
  { href: 'https://twitter.com/vitnetwork', icon: Twitter, label: 'Twitter' },
]

const CHAIN_STATS = [
  { icon: Zap,    label: 'Chain ID',   value: '7764' },
  { icon: Shield, label: 'Consensus',  value: 'Proof of Storage' },
  { icon: Globe,  label: 'Environment', value: 'Live services' },
]

// ── Component ─────────────────────────────────────────────────────────────────

export function Footer() {
  const { data: health } = useGatewayHealth()
  const isHealthy = health?.status === 'healthy' || health?.status === 'ok'
  const healthLabel = health?.status === 'degraded' ? 'Network degraded' : isHealthy ? 'All systems operational' : 'Status unavailable'
  const healthClass = health?.status === 'degraded' ? 'text-amber-400/80' : isHealthy ? 'text-emerald-400/70' : 'text-white/40'
  const healthDotClass = health?.status === 'degraded' ? 'bg-amber-400' : isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-white/35'
  return (
    <footer className="mt-24 border-t border-white/6 bg-gradient-to-b from-surface-800/40 to-surface-900">

      {/* ── Chain stats strip ──────────────────────────────────────────────── */}
      <div className="border-b border-white/5 bg-white/2">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between gap-6 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-6 shrink-0">
              {CHAIN_STATS.map(({ icon: Icon, label, value }) => (
                <div key={`${label}-${value}`} className="flex items-center gap-2 text-xs shrink-0">
                  <Icon className="w-3.5 h-3.5 text-vit-500/60" />
                  <span className="text-white/30">{label}:</span>
                  <span className="text-white/60 font-medium">{value}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-1.5 text-xs shrink-0">
              <Link
                to={ROUTES.status}
                aria-label={`View system status: ${healthLabel}`}
                className="inline-flex items-center gap-1.5 text-white/40 hover:text-white/70 transition-colors"
              >
                <span className={`w-1.5 h-1.5 rounded-full ${healthDotClass}`} />
                <span className={`${healthClass} font-medium`}>{healthLabel}</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main footer body ───────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-12 pb-8">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-10 mb-12">

          {/* Brand column */}
          <div className="col-span-2 sm:col-span-3 lg:col-span-1">
            <Link to="/" className="inline-flex items-center gap-2.5 mb-4 group">
              <img
                src="/logo.png"
                alt="VIT Network"
                className="w-8 h-8 rounded-xl object-cover shadow-md shadow-vit-500/20 group-hover:shadow-vit-500/35 transition-shadow"
                onError={e => { e.currentTarget.style.display = 'none' }}
              />
              <div>
                <span className="font-bold text-white text-sm leading-none">VIT Network</span>
                <p className="text-white/25 text-[10px] mt-0.5">Value · Intelligence · Transparency</p>
              </div>
            </Link>

            <p className="text-sm text-white/40 leading-relaxed mb-5">
              A proof-first intelligence layer for sports modeling, public recordkeeping, and transparent platform monitoring.
            </p>

            <div className="flex items-center gap-2 mb-5">
              {SOCIALS.map(({ href, icon: Icon, label }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 border border-white/6 hover:border-white/12 flex items-center justify-center text-white/40 hover:text-white transition-all"
                >
                  <Icon className="w-3.5 h-3.5" />
                </a>
              ))}
            </div>

          </div>

          {/* Link columns */}
          <nav aria-label="Footer navigation" className="col-span-2 grid grid-cols-2 gap-x-6 gap-y-10 sm:col-span-3 lg:col-span-5 lg:grid-cols-4">
          {FOOTER_NAVIGATION_GROUPS.map(group => (
            <div key={group.label}>
              <h4 className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-4">
                {group.label}
              </h4>
              <ul className="space-y-2.5">
                {group.items.map(item => (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      className="text-sm text-white/45 hover:text-white transition-colors leading-none"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          </nav>
        </div>

        {/* ── Bottom bar ─────────────────────────────────────────────────── */}
        <div className="pt-6 border-t border-white/6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/30 order-2 sm:order-1">
            © {new Date().getFullYear()} VIT Network. Built on VIT Chain (Chain ID 7764).
          </p>
          <div className="flex items-center gap-4 order-1 sm:order-2 flex-wrap">
            {FOOTER_LEGAL_LINKS.map(({ label, path }) => (
              <Link key={label} to={path} className="text-xs text-white/30 hover:text-white/60 transition-colors">
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
