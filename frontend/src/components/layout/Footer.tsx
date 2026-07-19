import { Link } from 'react-router-dom'
import { Github, Twitter, ExternalLink, Zap, Shield, Globe } from 'lucide-react'

// ── Link columns ──────────────────────────────────────────────────────────────

const COLUMNS = [
  {
    heading: 'Platform',
    links: [
      { label: 'Overview',       path: '/platform' },
      { label: 'AI Engine',      path: '/ai' },
      { label: 'Tachyon Storage',path: '/storage' },
      { label: 'Chain Explorer', path: '/chain' },
      { label: 'System Status',  path: '/status' },
      { label: 'Validators',     path: '/validators' },
    ],
  },
  {
    heading: 'Earn & Trade',
    links: [
      { label: 'Wallet',       path: '/wallet' },
      { label: 'VITCoin',      path: '/vitcoin' },
      { label: 'P2P Exchange', path: '/exchange' },
      { label: 'DeFi Pools',   path: '/defi' },
      { label: 'Vaults',       path: '/vaults' },
      { label: 'Bridge',       path: '/bridge' },
      { label: 'Marketplace',  path: '/marketplace' },
    ],
  },
  {
    heading: 'Predict',
    links: [
      { label: 'Matches',      path: '/matches' },
      { label: 'Predictions',  path: '/predictions' },
      { label: 'In-Play',      path: '/inplay' },
      { label: 'Odds Compare', path: '/odds' },
      { label: 'AI Assistant', path: '/assistant' },
      { label: 'Accumulator',  path: '/accumulator' },
      { label: 'Bankroll',     path: '/bankroll' },
    ],
  },
  {
    heading: 'Community',
    links: [
      { label: 'Governance',       path: '/governance' },
      { label: 'Social Feed',      path: '/social' },
      { label: 'Leaderboard',      path: '/leaderboard' },
      { label: 'Analytics Studio', path: '/analytics-studio' },
      { label: 'Referral',         path: '/referral' },
      { label: 'Ecosystem',        path: '/ecosystem' },
    ],
  },
  {
    heading: 'Resources',
    links: [
      { label: 'Documentation', path: '/docs' },
      { label: 'API Reference', path: '/developers' },
      { label: 'Roadmap',       path: '/roadmap' },
      { label: 'About',         path: '/about' },
      { label: 'Enterprise',    path: '/enterprise' },
      { label: 'Subscription',  path: '/subscription' },
    ],
  },
]

const SOCIALS = [
  { href: 'https://github.com/vitnetwork', icon: Github,  label: 'GitHub' },
  { href: 'https://twitter.com/vitnetwork', icon: Twitter, label: 'Twitter' },
]

const CHAIN_STATS = [
  { icon: Zap,    label: 'Chain ID',   value: '7764' },
  { icon: Shield, label: 'Network',    value: 'PoS' },
  { icon: Globe,  label: 'Status',     value: 'Mainnet Beta' },
]

// ── Component ─────────────────────────────────────────────────────────────────

export function Footer() {
  return (
    <footer className="mt-24 border-t border-white/6 bg-gradient-to-b from-surface-800/40 to-surface-900">

      {/* ── Chain stats strip ──────────────────────────────────────────────── */}
      <div className="border-b border-white/5 bg-white/2">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between gap-6 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-6 shrink-0">
              {CHAIN_STATS.map(({ icon: Icon, label, value }) => (
                <div key={label} className="flex items-center gap-2 text-xs shrink-0">
                  <Icon className="w-3.5 h-3.5 text-vit-500/60" />
                  <span className="text-white/30">{label}:</span>
                  <span className="text-white/60 font-medium">{value}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-1.5 text-xs shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-emerald-400/70 font-medium">All systems operational</span>
              <Link to="/status" className="text-white/25 hover:text-white/50 transition-colors ml-1">
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
                <p className="text-white/25 text-[10px] mt-0.5">Chain ID 7764</p>
              </div>
            </Link>

            <p className="text-sm text-white/40 leading-relaxed mb-5">
              Africa's sovereign AI intelligence layer — predictions, storage, and a native PoS blockchain unified in one gateway.
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

            <Link
              to="/status"
              className="inline-flex items-center gap-1.5 text-xs text-white/25 hover:text-white/50 transition-colors"
            >
              <ExternalLink className="w-3 h-3" /> Status page
            </Link>
          </div>

          {/* Link columns */}
          {COLUMNS.map(col => (
            <div key={col.heading}>
              <h4 className="text-[10px] font-semibold uppercase tracking-widest text-white/25 mb-4">
                {col.heading}
              </h4>
              <ul className="space-y-2.5">
                {col.links.map(item => (
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
        </div>

        {/* ── Bottom bar ─────────────────────────────────────────────────── */}
        <div className="pt-6 border-t border-white/6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/20 order-2 sm:order-1">
            © {new Date().getFullYear()} VIT Network. Built on VIT Chain (Chain ID 7764). All rights reserved.
          </p>
          <div className="flex items-center gap-4 order-1 sm:order-2">
            {[
              { label: 'Privacy',  path: '/docs#privacy' },
              { label: 'Terms',    path: '/docs#terms' },
              { label: 'Security', path: '/docs#security' },
            ].map(({ label, path }) => (
              <Link key={label} to={path} className="text-xs text-white/20 hover:text-white/45 transition-colors">
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
