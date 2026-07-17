import { Link } from 'react-router-dom'
import { Github, ExternalLink } from 'lucide-react'

const LINKS = {
  Platform: [
    { label: 'Overview',     path: '/platform' },
    { label: 'AI Engine',    path: '/ai' },
    { label: 'Storage',      path: '/storage' },
    { label: 'Chain Explorer', path: '/chain' },
    { label: 'Status',       path: '/status' },
  ],
  'Earn & Trade': [
    { label: 'Wallet',       path: '/wallet' },
    { label: 'DeFi Pools',   path: '/defi' },
    { label: 'Marketplace',  path: '/marketplace' },
    { label: 'In-Play',      path: '/inplay' },
    { label: 'Referral',     path: '/referral' },
  ],
  Community: [
    { label: 'Governance',       path: '/governance' },
    { label: 'Social Feed',      path: '/social' },
    { label: 'Leaderboard',      path: '/leaderboard' },
    { label: 'Analytics Studio', path: '/analytics-studio' },
    { label: 'Ecosystem',        path: '/ecosystem' },
  ],
  Predict: [
    { label: 'Matches',       path: '/matches' },
    { label: 'Predictions',   path: '/predictions' },
    { label: 'Odds Compare',  path: '/odds' },
    { label: 'AI Assistant',  path: '/assistant' },
    { label: 'Analytics',     path: '/analytics' },
  ],
  Resources: [
    { label: 'Documentation', path: '/docs' },
    { label: 'API Reference', path: '/docs#api' },
    { label: 'Developers',    path: '/developers' },
    { label: 'Roadmap',       path: '/roadmap' },
    { label: 'Validators',    path: '/validators' },
  ],
  Company: [
    { label: 'About',         path: '/about' },
    { label: 'Enterprise',    path: '/enterprise' },
    { label: 'Subscription',  path: '/subscription' },
    { label: 'Treasury',      path: '/treasury' },
  ],
}

export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-surface-800/50 mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-10">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5 mb-4">
              <img
                src="/logo.png"
                alt="VIT Network"
                className="w-7 h-7 rounded-lg object-cover"
                onError={(e) => {
                  const img = e.currentTarget
                  img.style.display = 'none'
                  const fallback = document.getElementById('footer-logo-fallback')
                  if (fallback) fallback.style.display = 'flex'
                }}
              />
              {/* Fallback shown only if logo.png fails to load */}
              <div
                id="footer-logo-fallback"
                style={{ display: 'none' }}
                className="w-7 h-7 rounded-lg bg-gradient-to-br from-vit-500 to-vit-700 items-center justify-center"
              >
                <span className="text-white font-bold text-xs">V</span>
              </div>
              <span className="font-bold text-white">VIT Network</span>
            </div>
            <p className="text-sm text-white/50 leading-relaxed mb-4">
              The AI-powered decentralized platform gateway. Aggregating services, never duplicating them.
            </p>
            <div className="flex items-center gap-3">
              <a
                href="https://github.com/nemesistip-cloud/vit"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/50 hover:text-white transition-colors"
              >
                <Github className="w-4 h-4" />
              </a>
            </div>
          </div>

          {Object.entries(LINKS).map(([group, items]) => (
            <div key={group}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-white/40 mb-4">{group}</h4>
              <ul className="space-y-2.5">
                {items.map(item => (
                  <li key={item.path}>
                    <Link to={item.path} className="text-sm text-white/60 hover:text-white transition-colors">
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/30">
            © {new Date().getFullYear()} VIT Network. All rights reserved.
          </p>
          <div className="flex items-center gap-1.5 text-xs text-white/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            All systems operational
            <a
              href="/status"
              className="ml-1 text-vit-400 hover:text-vit-300 flex items-center gap-0.5"
            >
              Status <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
