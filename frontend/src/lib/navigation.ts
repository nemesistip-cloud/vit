import {
  Activity,
  BarChart3,
  Boxes,
  BriefcaseBusiness,
  CircleHelp,
  Coins,
  Database,
  FileText,
  Globe2,
  HardDrive,
  LayoutDashboard,
  Landmark,
  Radio,
  Settings,
  Shield,
  ShieldCheck,
  Smartphone,
  Store,
  Users,
  Wallet,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getAppRegistry } from '@/lib/appRegistry'

export const ROUTES = {
  home: '/',
  platform: '/platform',
  ai: '/ai',
  storage: '/storage',
  status: '/status-page',
  verification: '/verification',
  developers: '/developers',
  docs: '/docs',
  responsibleUse: '/responsible-use',
  roadmap: '/roadmap',
  about: '/about',
  applications: '/applications',
  matches: '/matches',
  predictions: '/predictions',
  odds: '/odds',
  analyticsStudio: '/analytics-studio',
  leaderboard: '/leaderboard',
  governance: '/governance',
  marketplace: '/marketplace',
  explorer: '/chain',
  validators: '/validators',
  networkValidators: '/network/validators',
  login: '/login',
  register: '/register',
  forgotPassword: '/forgot-password',
  resetPassword: '/reset-password',
  verifyEmail: '/verify-email',
  vitpredict: '/apps/vitpredict',
  vitpredictHome: '/apps/vitpredict/home',
  vitpredictVerification: '/apps/vitpredict/verification',
  vitpredictDashboard: '/apps/vitpredict/dashboard',
  vitpredictMatches: '/apps/vitpredict/matches',
  vitpredictPredictions: '/apps/vitpredict/predictions',
  vitpredictOdds: '/apps/vitpredict/odds',
  vitpredictAnalytics: '/apps/vitpredict/analytics',
  dashboard: '/dashboard',
  workspace: '/workspace',
  settings: '/settings',
  subscription: '/subscription',
  analytics: '/analytics',
  assistant: '/assistant',
  tasks: '/tasks',
  wallet: '/wallet',
  defi: '/defi',
  inPlay: '/inplay',
  genesis: '/genesis',
  referral: '/referral',
  treasury: '/treasury',
  social: '/social',
  ecosystem: '/ecosystem',
  enterprise: '/enterprise',
  accumulator: '/accumulator',
  rollover: '/rollover',
  backtest: '/backtest',
  bankroll: '/bankroll',
  vitcoin: '/vitcoin',
  exchange: '/exchange',
  vaults: '/vaults',
  bridge: '/bridge',
  admin: '/admin',
} as const

export interface NavigationItem {
  id: string
  label: string
  path: string
  icon: LucideIcon
  audience: 'public' | 'authenticated' | 'admin'
}

export interface NavigationGroup {
  label: string
  items: NavigationItem[]
}

export const VITPREDICT_NAVIGATION_ITEMS = [
  { id: 'overview', label: 'Overview', path: ROUTES.vitpredict, icon: Globe2, end: true },
  { id: 'insights', label: 'Insights', path: ROUTES.vitpredictHome, icon: Activity },
  { id: 'fixtures', label: 'Fixtures', path: ROUTES.vitpredictMatches, icon: Radio },
  { id: 'predictions', label: 'Predictions', path: ROUTES.vitpredictPredictions, icon: ShieldCheck },
  { id: 'odds', label: 'Odds data', path: ROUTES.vitpredictOdds, icon: BarChart3 },
  { id: 'evaluation', label: 'Evaluation', path: ROUTES.vitpredictAnalytics, icon: BarChart3 },
  { id: 'verification', label: 'Verification', path: ROUTES.vitpredictVerification, icon: ShieldCheck },
]

const items = {
  platform: { id: 'platform', label: 'Platform', path: ROUTES.platform, icon: Globe2, audience: 'public' },
  applications: { id: 'applications', label: 'Applications', path: ROUTES.applications, icon: Smartphone, audience: 'public' },
  explorer: { id: 'explorer', label: 'Explorer', path: ROUTES.explorer, icon: Boxes, audience: 'public' },
  validators: { id: 'validators', label: 'Validators', path: ROUTES.validators, icon: Shield, audience: 'public' },
  developers: { id: 'developers', label: 'Developers', path: ROUTES.developers, icon: FileText, audience: 'public' },
  status: { id: 'status', label: 'Status', path: ROUTES.status, icon: Activity, audience: 'public' },
  network: { id: 'network', label: 'Network', path: ROUTES.dashboard, icon: LayoutDashboard, audience: 'authenticated' },
  workspace: { id: 'workspace', label: 'Workspace', path: ROUTES.workspace, icon: BriefcaseBusiness, audience: 'authenticated' },
  wallet: { id: 'wallet', label: 'Wallet', path: ROUTES.wallet, icon: Wallet, audience: 'authenticated' },
  analytics: { id: 'analytics', label: 'Analytics', path: ROUTES.analytics, icon: BarChart3, audience: 'authenticated' },
  governance: { id: 'governance', label: 'Governance', path: ROUTES.governance, icon: ShieldCheck, audience: 'authenticated' },
  marketplace: { id: 'marketplace', label: 'Marketplace', path: ROUTES.marketplace, icon: Store, audience: 'authenticated' },
  contributors: { id: 'contributors', label: 'Contributors', path: ROUTES.social, icon: Users, audience: 'authenticated' },
  treasury: { id: 'treasury', label: 'Treasury', path: ROUTES.treasury, icon: Landmark, audience: 'authenticated' },
  defi: { id: 'defi', label: 'DeFi', path: ROUTES.defi, icon: Coins, audience: 'authenticated' },
  storage: { id: 'storage', label: 'Storage', path: ROUTES.storage, icon: HardDrive, audience: 'authenticated' },
  genesis: { id: 'genesis', label: 'Genesis', path: ROUTES.genesis, icon: ShieldCheck, audience: 'authenticated' },
  referral: { id: 'referral', label: 'Referral', path: ROUTES.referral, icon: Users, audience: 'authenticated' },
  enterprise: { id: 'enterprise', label: 'Enterprise', path: ROUTES.enterprise, icon: Landmark, audience: 'authenticated' },
  assistant: { id: 'assistant', label: 'Assistant', path: ROUTES.assistant, icon: CircleHelp, audience: 'authenticated' },
  tasks: { id: 'tasks', label: 'Tasks', path: ROUTES.tasks, icon: Radio, audience: 'authenticated' },
  subscription: { id: 'subscription', label: 'Subscription', path: ROUTES.subscription, icon: Coins, audience: 'authenticated' },
  settings: { id: 'settings', label: 'Settings', path: ROUTES.settings, icon: Settings, audience: 'authenticated' },
  admin: { id: 'admin', label: 'Admin Control', path: ROUTES.admin, icon: ShieldCheck, audience: 'admin' },
} satisfies Record<string, NavigationItem>

export const PUBLIC_NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: 'Explore',
    items: [items.platform, items.applications, items.explorer, items.validators, items.developers, items.status],
  },
]

export const AUTHENTICATED_NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: 'Network',
    items: [items.network, items.workspace, items.explorer, items.validators, items.status],
  },
  {
    label: 'Applications',
    items: [items.applications],
  },
  {
    label: 'Ecosystem',
    items: [
      items.analytics,
      items.assistant,
      items.tasks,
      items.governance,
      items.marketplace,
      items.contributors,
      items.treasury,
      items.defi,
      items.storage,
      items.genesis,
      items.referral,
      items.enterprise,
    ],
  },
  {
    label: 'Account',
    items: [items.wallet, items.subscription, items.settings],
  },
]

export const FOOTER_NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: 'Platform',
    items: [
      items.platform,
      { ...items.platform, id: 'ai', label: 'AI Oracle', path: ROUTES.ai, icon: CircleHelp },
      items.storage,
      items.explorer,
    ],
  },
  {
    label: 'Applications',
    items: [
      items.applications,
      ...getAppRegistry()
        .filter((app) => app.category === 'Applications')
        .map((app) => ({
          id: app.id,
          label: app.name,
          path: app.route,
          icon: app.icon,
          audience: 'public' as const,
        })),
    ],
  },
  {
    label: 'Ecosystem',
    items: [items.marketplace, items.treasury, items.defi, items.governance, items.validators],
  },
  {
    label: 'Developer',
    items: [
      { ...items.analytics, id: 'analytics-studio', label: 'Analytics Studio', path: ROUTES.analyticsStudio },
      items.enterprise,
      items.subscription,
      items.developers,
      { ...items.developers, id: 'documentation', label: 'Docs', path: ROUTES.docs },
    ],
  },
]

export const FOOTER_LEGAL_LINKS = [
  { label: 'Responsible use', path: ROUTES.responsibleUse },
  { label: 'About', path: ROUTES.about },
]

export function getNavigationGroups(isAuthenticated: boolean, isAdmin = false): NavigationGroup[] {
  if (!isAuthenticated) return PUBLIC_NAVIGATION_GROUPS

  const groups = [...AUTHENTICATED_NAVIGATION_GROUPS]
  if (isAdmin) groups.push({ label: 'Administration', items: [items.admin] })
  return groups
}

export function isNavigationItemActive(pathname: string, path: string): boolean {
  if (path === ROUTES.home) return pathname === path
  return pathname === path || pathname.startsWith(`${path}/`)
}
