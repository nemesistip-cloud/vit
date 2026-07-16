import { useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Landmark, TrendingUp, PieChart, Gift, Clock, CheckCircle2,
  XCircle, AlertCircle, DollarSign, Layers,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface TreasuryPool {
  pool_type: string
  balance: number
  reserved: number
  available: number
  description?: string
}

interface TreasuryOverview {
  total_balance: number
  total_reserved: number
  total_available: number
  pool_count: number
  pools?: TreasuryPool[]
}

interface Grant {
  id: number
  title: string
  status: string
  pool_type: string
  requested_amount: number
  approved_amount: number | null
  created_at: string
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useTreasuryOverview() {
  return useQuery({
    queryKey: ['treasury-overview'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/treasury/overview`, { signal, headers: authHeaders() })
      return r.ok ? r.json() as Promise<TreasuryOverview> : null
    },
    staleTime: 30_000,
    retry: false,
  })
}

function useTreasuryPools() {
  return useQuery({
    queryKey: ['treasury-pools'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/treasury/pools`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return (d.pools ?? []) as TreasuryPool[]
    },
    staleTime: 30_000,
    retry: false,
  })
}

function useGrants() {
  return useQuery({
    queryKey: ['treasury-grants'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/treasury/grants`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return (d.proposals ?? []) as Grant[]
    },
    staleTime: 30_000,
    retry: false,
  })
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`
  return n.toFixed(2)
}

const POOL_COLORS: Record<string, string> = {
  rewards_pool:    'bg-emerald-500',
  validator_fund:  'bg-sky-500',
  development_fund:'bg-vit-500',
  insurance_fund:  'bg-amber-500',
  liquidity_pool:  'bg-purple-500',
  staking_reserve: 'bg-rose-500',
}

const GRANT_STATUS_STYLES: Record<string, { pill: string; icon: ReactNode }> = {
  pending:  { pill: 'bg-amber-500/15 text-amber-400 border-amber-500/30',   icon: <Clock className="w-3.5 h-3.5" /> },
  approved: { pill: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
  rejected: { pill: 'bg-red-500/15 text-red-400 border-red-500/30',         icon: <XCircle className="w-3.5 h-3.5" /> },
  executed: { pill: 'bg-sky-500/15 text-sky-400 border-sky-500/30',          icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function PoolCard({ pool, totalBalance }: { pool: TreasuryPool; totalBalance: number }) {
  const color = POOL_COLORS[pool.pool_type] ?? 'bg-white/20'
  const pct = totalBalance > 0 ? Math.round((pool.balance / totalBalance) * 100) : 0
  const label = pool.pool_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())

  return (
    <div className="bg-white/3 border border-white/8 rounded-xl p-4">
      <div className="flex items-center gap-2.5 mb-3">
        <div className={cn('w-2.5 h-2.5 rounded-full', color)} />
        <span className="text-sm font-medium text-white">{label}</span>
        <span className="ml-auto text-xs text-white/30">{pct}%</span>
      </div>
      <p className="text-2xl font-bold text-white mb-1">{fmt(pool.balance)} <span className="text-sm font-normal text-white/40">VIT</span></p>
      <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden mt-2">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3">
        <div className="text-xs text-white/40">Reserved <span className="text-white/60 ml-1">{fmt(pool.reserved)}</span></div>
        <div className="text-xs text-white/40 text-right">Available <span className="text-emerald-400 ml-1">{fmt(pool.available)}</span></div>
      </div>
    </div>
  )
}

function GrantRow({ grant }: { grant: Grant }) {
  const style = GRANT_STATUS_STYLES[grant.status] ?? GRANT_STATUS_STYLES.pending
  return (
    <div className="flex items-center gap-4 p-4 border-b border-white/5 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{grant.title}</p>
        <p className="text-xs text-white/40 mt-0.5">
          {grant.pool_type.replace(/_/g, ' ')} · {new Date(grant.created_at).toLocaleDateString()}
        </p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-sm font-semibold text-white">{fmt(grant.approved_amount ?? grant.requested_amount)} VIT</p>
        <div className={cn('inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-xs border', style.pill)}>
          {style.icon}
          <span className="capitalize">{grant.status}</span>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function Treasury() {
  const { data: overview, isLoading: loadingOverview } = useTreasuryOverview()
  const { data: pools = [], isLoading: loadingPools } = useTreasuryPools()
  const { data: grants = [], isLoading: loadingGrants } = useGrants()

  const loading = loadingOverview || loadingPools

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Landmark className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Treasury</h1>
              <p className="text-white/50 text-sm">Protocol-owned reserves & community grant system</p>
            </div>
          </motion.div>

          {/* Summary cards */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-white/5 border border-white/8 rounded-xl p-4 animate-pulse h-20" />
              ))
            ) : ([
              { label: 'Total Balance',   value: `${fmt(overview?.total_balance ?? 0)} VIT`,    icon: DollarSign,   color: 'text-white' },
              { label: 'Available',       value: `${fmt(overview?.total_available ?? 0)} VIT`,   icon: TrendingUp,   color: 'text-emerald-400' },
              { label: 'Reserved',        value: `${fmt(overview?.total_reserved ?? 0)} VIT`,    icon: Layers,       color: 'text-amber-400' },
              { label: 'Active Pools',    value: `${overview?.pool_count ?? pools.length}`,      icon: PieChart,     color: 'text-vit-400' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-white/5 border border-white/8 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Icon className={cn('w-4 h-4', color)} />
                  <span className="text-xs text-white/40">{label}</span>
                </div>
                <p className={cn('text-xl font-bold', color)}>{value}</p>
              </div>
            )))}
          </motion.div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Pool distribution */}
        <div>
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-widest mb-4">Pool Distribution</h2>
          {loadingPools ? (
            <div className="flex items-center justify-center py-12"><Spinner size="lg" /></div>
          ) : pools.length === 0 ? (
            <div className="text-center py-12 text-white/30 text-sm">
              <PieChart className="w-8 h-8 mx-auto mb-2 opacity-30" />
              No pools found — treasury may need bootstrapping
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {pools.map(pool => (
                <PoolCard key={pool.pool_type} pool={pool} totalBalance={overview?.total_balance ?? 1} />
              ))}
            </div>
          )}
        </div>

        {/* Grant proposals */}
        <div>
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Gift className="w-4 h-4" /> Community Grants
          </h2>
          <div className="bg-white/3 border border-white/8 rounded-xl overflow-hidden">
            {loadingGrants ? (
              <div className="flex items-center justify-center py-12"><Spinner /></div>
            ) : grants.length === 0 ? (
              <div className="text-center py-12 text-white/30 text-sm">
                <Gift className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No grant proposals yet
              </div>
            ) : (
              grants.map(g => <GrantRow key={g.id} grant={g} />)
            )}
          </div>
        </div>

        {/* Info panel */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { icon: Landmark,     title: 'Protocol Reserves',  body: 'Treasury pools are funded by trading fees, prediction settlements, and epoch block rewards. All movements are on-chain and auditable.' },
            { icon: Gift,         title: 'Community Grants',   body: 'Anyone can submit a grant proposal. Approved grants are released from the designated pool after governance approval.' },
            { icon: AlertCircle,  title: 'Governance Link',    body: 'Major treasury allocations (> 10,000 VIT) require a passing DAO vote via the Governance module before execution.' },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="bg-white/3 border border-white/8 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4 text-vit-400" />
                <span className="text-sm font-medium text-white">{title}</span>
              </div>
              <p className="text-xs text-white/40 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
