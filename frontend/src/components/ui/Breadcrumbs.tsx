import { Link, useLocation } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'

const ROUTE_LABELS: Record<string, string> = {
  dashboard:        'Dashboard',
  predictions:      'Predictions',
  matches:          'Matches',
  wallet:           'Wallet',
  governance:       'Governance',
  treasury:         'Treasury',
  marketplace:      'Marketplace',
  referral:         'Referral',
  defi:             'DeFi',
  inplay:           'In-Play',
  'analytics-studio': 'Analytics Studio',
  analytics:        'Analytics',
  enterprise:       'Enterprise',
  social:           'Social',
  ecosystem:        'Ecosystem',
  leaderboard:      'Leaderboard',
  validators:       'Validators',
  explorer:         'Explorer',
  chain:            'Chain Explorer',
  storage:          'Storage',
  ai:               'AI Oracle',
  assistant:        'AI Assistant',
  settings:         'Settings',
  subscription:     'Subscription',
  tasks:            'Tasks',
  bridge:           'Bridge',
  exchange:         'Exchange',
  vaults:           'Vaults',
  vitcoin:          'VITCoin',
  accumulator:      'Accumulator',
  rollover:         'Rollover',
  backtest:         'Backtest',
  bankroll:         'Bankroll',
  status:           'System Status',
  admin:            'Admin',
  login:            'Login',
  platform:         'Platform',
  docs:             'Documentation',
  roadmap:          'Roadmap',
  about:            'About',
}

interface BreadcrumbsProps {
  className?: string
  /** Extra items to append after the route-derived crumbs */
  extra?: { label: string; href?: string }[]
}

export function Breadcrumbs({ className, extra }: BreadcrumbsProps) {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)

  // Don't render on home / auth pages
  if (segments.length === 0 || ['login', 'forgot-password', 'reset-password', 'verify-email'].includes(segments[0])) {
    return null
  }

  const crumbs: { label: string; href?: string }[] = [
    { label: 'Home', href: '/' },
    ...segments.map((seg, i) => ({
      label: ROUTE_LABELS[seg] ?? seg.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      href: i === segments.length - 1 ? undefined : `/${segments.slice(0, i + 1).join('/')}`,
    })),
    ...(extra ?? []),
  ]

  return (
    <nav aria-label="Breadcrumb" className={cn('flex items-center gap-1 text-sm', className)}>
      {crumbs.map((crumb, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-white/20 shrink-0" />}
          {crumb.href ? (
            <Link to={crumb.href} className="flex items-center gap-1 text-white/40 hover:text-white/70 transition-colors">
              {i === 0 && <Home className="w-3.5 h-3.5" />}
              {i > 0 && crumb.label}
            </Link>
          ) : (
            <span className="text-white/70 font-medium">{crumb.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
