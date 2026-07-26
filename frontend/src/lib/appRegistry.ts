import { lazy } from 'react'
import type { ComponentType } from 'react'
import {
  LayoutDashboard,
  Brain,
  Wallet,
  HardDrive,
  BarChart3,
  Vote,
  Store,
  Sparkles,
} from 'lucide-react'

export interface AppRegistryItem {
  id: string
  name: string
  icon: typeof LayoutDashboard
  category: string
  description: string
  route: string
  component: ComponentType
  defaultWindowSize: { width: number; height: number }
  minimumWindowSize: { width: number; height: number }
  permissions?: string[]
  featureFlag?: string
  enabled?: boolean
  pinned?: boolean
}

const appRegistry: AppRegistryItem[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: LayoutDashboard,
    category: 'Overview',
    description: 'Mission control',
    route: '/dashboard',
    component: lazy(() => import('@/pages/Dashboard')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
    pinned: true,
  },
  {
    id: 'wallet',
    name: 'Wallet',
    icon: Wallet,
    category: 'Finance',
    description: 'Balances and activity',
    route: '/wallet',
    component: lazy(() => import('@/pages/Wallet')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
    pinned: true,
  },
  {
    id: 'ai',
    name: 'AI',
    icon: Brain,
    category: 'Overview',
    description: 'Get guided insights',
    route: '/ai',
    component: lazy(() => import('@/pages/AI')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
    pinned: true,
  },
  {
    id: 'storage',
    name: 'Storage',
    icon: HardDrive,
    category: 'Network',
    description: 'Storage overview',
    route: '/storage',
    component: lazy(() => import('@/pages/Storage')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
  },
  {
    id: 'analytics',
    name: 'Analytics',
    icon: BarChart3,
    category: 'Analytics',
    description: 'Operational analytics',
    route: '/analytics',
    component: lazy(() => import('@/pages/Analytics')),
    defaultWindowSize: { width: 560, height: 460 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
  },
  {
    id: 'governance',
    name: 'Governance',
    icon: Vote,
    category: 'Network',
    description: 'Governance and voting',
    route: '/governance',
    component: lazy(() => import('@/pages/Governance')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
  },
  {
    id: 'marketplace',
    name: 'Marketplace',
    icon: Store,
    category: 'Finance',
    description: 'Marketplace overview',
    route: '/marketplace',
    component: lazy(() => import('@/pages/Marketplace')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
  },
  {
    id: 'predictions',
    name: 'Predictions',
    icon: Sparkles,
    category: 'Sports & Predictions',
    description: 'Open positions',
    route: '/predictions',
    component: lazy(() => import('@/pages/Predictions')),
    defaultWindowSize: { width: 520, height: 420 },
    minimumWindowSize: { width: 320, height: 260 },
    enabled: true,
    pinned: true,
  },
]

const registryMap = new Map(appRegistry.map((app) => [app.id, app]))

export function getAppRegistry() {
  return appRegistry.filter((app) => app.enabled !== false)
}

export function getAppById(id: string) {
  return registryMap.get(id) ?? null
}

export function getEnabledAppsByCategory(category: string) {
  return getAppRegistry().filter((app) => app.category === category)
}

export function getPinnedApps() {
  return getAppRegistry().filter((app) => app.pinned)
}
