import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Shield, Users, Activity, Database, Server,
  TrendingUp, AlertTriangle, RefreshCw, ChevronRight,
  Cpu, Zap, Star, BarChart2, Settings, ClipboardList,
  Wallet as WalletIcon, Layers, CheckCircle2, XCircle,
  Clock, Globe, Lock, Unlock,
} from 'lucide-react'
import { getAuthToken, getStoredUser, authHeaders } from '@/hooks/useAuth'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { cn } from '@/lib/utils'

// ── Hooks ─────────────────────────────────────────────────────────────────────

function useSystemStatus() {
  return useQuery({ queryKey: ['admin-system-status'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/system/status`, { signal })
    return r.ok ? r.json() : null
  }, staleTime: 30_000, refetchInterval: 30_000 })
}
function useAdminHealth() {
  return useQuery({ queryKey: ['admin-health'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/health`, { signal, headers: authHeaders() })
    return r.ok ? r.json() : null
  }, retry: false, staleTime: 30_000, refetchInterval: 30_000 })
}
function useAdminUsers() {
  return useQuery({ queryKey: ['admin-users'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/users?limit=50`, { signal, headers: authHeaders() })
    return r.ok ? r.json() : null
  }, retry: false, staleTime: 60_000 })
}
function useAdminMetrics() {
  return useQuery({ queryKey: ['admin-metrics'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/system/metrics`, { signal, headers: authHeaders() })
    return r.ok ? r.json() : null
  }, retry: false, staleTime: 30_000 })
}
function useAdminWalletTxs() {
  return useQuery({ queryKey: ['admin-wallet-txs'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/wallet/transactions?limit=30`, { signal, headers: authHeaders() })
    if (!r.ok) return []
    const d = await r.json(); return Array.isArray(d) ? d : d.items ?? []
  }, retry: false, staleTime: 60_000 })
}
function useAdminMatches() {
  return useQuery({ queryKey: ['admin-matches'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/matches?limit=30`, { signal, headers: authHeaders() })
    if (!r.ok) return []
    const d = await r.json(); return Array.isArray(d) ? d : d.items ?? []
  }, retry: false, staleTime: 60_000 })
}
function useAdminValidators() {
  return useQuery({ queryKey: ['admin-validators'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/validators`, { signal, headers: authHeaders() })
    if (!r.ok) return []
    const d = await r.json(); return Array.isArray(d) ? d : d.items ?? []
  }, retry: false, staleTime: 60_000 })
}
function useAdminModels() {
  return useQuery({ queryKey: ['admin-models'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/models`, { signal, headers: authHeaders() })
    if (!r.ok) return []
    const d = await r.json(); return Array.isArray(d) ? d : d.items ?? []
  }, retry: false, staleTime: 60_000 })
}
function useAdminConfig() {
  return useQuery({ queryKey: ['admin-config'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/config`, { signal, headers: authHeaders() })
    return r.ok ? r.json() : null
  }, retry: false, staleTime: 120_000 })
}
function useAdminAudit() {
  return useQuery({ queryKey: ['admin-audit'], queryFn: async ({ signal }) => {
    const r = await fetch(`${ENDPOINTS.gateway}/api/admin/audit-log?limit=50`, { signal, headers: authHeaders() })
    if (!r.ok) return []
    const d = await r.json(); return Array.isArray(d) ? d : d.items ?? []
  }, retry: false, staleTime: 30_000 })
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, color = 'text-white', i = 0 }: {
  icon: React.ElementType; label: string; value?: string | number | null; color?: string; i?: number
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
      className="p-5 bg-surface-800/60 border border-white/8 rounded-xl">
      <Icon className={`w-4 h-4 mb-3 ${color}`} />
      <p className={cn('text-2xl font-bold', color)}>{value ?? '—'}</p>
      <p className="text-white/50 text-sm mt-0.5">{label}</p>
    </motion.div>
  )
}
function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-white/6 last:border-0">
      <span className="text-sm text-white/40">{label}</span>
      <span className="text-sm text-white font-medium">{value ?? '—'}</span>
    </div>
  )
}
function EmptyState({ icon: Icon, msg }: { icon: React.ElementType; msg: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-2">
      <Icon className="w-8 h-8 text-white/10" /><p className="text-white/30 text-sm">{msg}</p>
    </div>
  )
}

// ── Tab: Overview ─────────────────────────────────────────────────────────────

function OverviewTab({ status, health, metrics, refetchStatus, refetchHealth, loadingStatus, loadingHealth }: any) {
  if (loadingStatus && loadingHealth) return <div className="flex justify-center py-20"><Spinner className="w-8 h-8 text-vit-400" /></div>
  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Platform Metrics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard icon={Users}      label="Total Users"      value={status?.total_users?.toLocaleString()}        color="text-vit-400"     i={0} />
          <MetricCard icon={Activity}   label="Active (30d)"     value={status?.active_users_30d?.toLocaleString()}   color="text-emerald-400" i={1} />
          <MetricCard icon={Star}       label="Validators"       value={status?.active_validators?.toLocaleString()}  color="text-yellow-400"  i={2} />
          <MetricCard icon={TrendingUp} label="Predictions Made" value={status?.total_predictions?.toLocaleString()}  color="text-purple-400"  i={3} />
        </div>
      </section>
      <section>
        <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">System Health</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2"><Server className="w-4 h-4 text-vit-400" /><span className="text-white font-medium text-sm">VIT Gateway</span></div>
              <StatusBadge status={health?.status ?? (status ? 'operational' : 'unknown')} size="sm" pulse />
            </div>
            <Row label="Version"  value={health?.version ?? status?.version ?? '1.1.0'} />
            <Row label="Database" value={health?.db_connected !== false ? 'Connected' : 'Disconnected'} />
            <Row label="Redis"    value={health?.redis?.status ?? 'Not configured'} />
            <Row label="Models"   value={health?.models_loaded != null ? `${health.models_loaded} loaded` : null} />
          </div>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4"><Cpu className="w-4 h-4 text-purple-400" /><span className="text-white font-medium text-sm">VIT AI</span></div>
            <div className="flex flex-col items-center justify-center py-4 gap-2">
              <Cpu className="w-8 h-8 text-white/15" />
              <a href={`${ENDPOINTS.ai}/health`} target="_blank" rel="noopener noreferrer" className="text-xs text-vit-400 hover:text-vit-300 transition-colors">View AI health →</a>
            </div>
          </div>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4"><Database className="w-4 h-4 text-emerald-400" /><span className="text-white font-medium text-sm">VIT Storage</span></div>
            <div className="flex flex-col items-center justify-center py-4 gap-2">
              <Database className="w-8 h-8 text-white/15" />
              <a href={ENDPOINTS.storage} target="_blank" rel="noopener noreferrer" className="text-xs text-vit-400 hover:text-vit-300 transition-colors">Open Storage Console →</a>
            </div>
          </div>
        </div>
      </section>
      {metrics && (
        <section>
          <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Runtime Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard icon={Zap}       label="Requests/min" value={metrics.requests_per_minute}                                              color="text-vit-400"     i={0} />
            <MetricCard icon={BarChart2} label="Avg Latency"  value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms}ms` : null}            color="text-blue-400"   i={1} />
            <MetricCard icon={Activity}  label="Error Rate"   value={metrics.error_rate ? `${(metrics.error_rate*100).toFixed(2)}%` : null}    color="text-red-400"    i={2} />
            <MetricCard icon={Database}  label="DB Pool"      value={metrics.db_pool_size}                                                     color="text-emerald-400" i={3} />
          </div>
        </section>
      )}
      <section>
        <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Admin Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Audit Log',    href: `${ENDPOINTS.gateway}/api/admin/audit-log`,          icon: ClipboardList },
            { label: 'Transactions', href: `${ENDPOINTS.gateway}/api/admin/wallet/transactions`, icon: TrendingUp    },
            { label: 'Training Jobs',href: `${ENDPOINTS.gateway}/api/admin/training-jobs`,       icon: Cpu           },
            { label: 'API Docs',     href: `${ENDPOINTS.gateway}/docs`,                          icon: ChevronRight  },
          ].map(({ label, href, icon: Icon }) => (
            <a key={label} href={href} target="_blank" rel="noopener noreferrer"
              className="group flex items-center gap-3 p-4 bg-surface-800/60 border border-white/8 rounded-xl hover:border-white/20 hover:bg-surface-800/80 transition-all">
              <Icon className="w-4 h-4 text-white/30 group-hover:text-white/60 transition-colors" />
              <span className="text-sm text-white/60 group-hover:text-white transition-colors">{label}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}

// ── Tab: Users ────────────────────────────────────────────────────────────────

function UsersTab() {
  const { data: raw, isLoading, refetch } = useAdminUsers()
  const list: any[] = Array.isArray(raw?.items ?? raw) ? (raw?.items ?? raw) : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{list.length > 0 ? `${list.length} users` : 'Users'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : list.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','User','Role','Tier','Joined','Active'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{list.map((u: any) => (
                <tr key={u.id} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                  <td className="px-4 py-3 text-white/30 text-xs font-mono">#{u.id}</td>
                  <td className="px-4 py-3"><p className="text-white text-sm font-medium">{u.username}</p><p className="text-white/35 text-xs">{u.email}</p></td>
                  <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', u.role==='admin' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' : 'bg-white/5 text-white/40 border-white/10')}>{u.role}</span></td>
                  <td className="px-4 py-3 text-white/40 text-xs capitalize">{u.subscription_tier ?? 'viewer'}</td>
                  <td className="px-4 py-3 text-white/35 text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">{u.is_active !== false ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={Users} msg={raw === null ? 'Admin access required' : 'No users found'} />}
      </div>
    </div>
  )
}

// ── Tab: Wallet ───────────────────────────────────────────────────────────────

function WalletAdminTab() {
  const { data: list = [], isLoading, refetch } = useAdminWalletTxs()
  const txs: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{txs.length > 0 ? `${txs.length} transactions` : 'Transactions'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : txs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','User','Type','Amount','Status','Date'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{txs.map((tx: any, i: number) => {
                const isOut = ['sent','withdrawal','stake'].includes(tx.type) || (tx.amount ?? 0) < 0
                return (
                  <tr key={tx.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                    <td className="px-4 py-3 text-white/30 text-xs font-mono">#{tx.id ?? i}</td>
                    <td className="px-4 py-3 text-white/60 text-sm">{tx.user_id ?? '—'}</td>
                    <td className="px-4 py-3 text-white/60 text-xs capitalize">{tx.type?.replace(/_/g,' ') ?? '—'}</td>
                    <td className={cn('px-4 py-3 text-sm font-medium', isOut ? 'text-red-400' : 'text-emerald-400')}>{isOut ? '-' : '+'}{Math.abs(tx.amount ?? 0).toLocaleString()} VIT</td>
                    <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', tx.status==='completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : tx.status==='pending' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-white/5 text-white/30 border-white/10')}>{tx.status ?? 'unknown'}</span></td>
                    <td className="px-4 py-3 text-white/30 text-xs">{tx.created_at ? new Date(tx.created_at).toLocaleString() : '—'}</td>
                  </tr>
                )
              })}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={WalletIcon} msg="No transactions found" />}
      </div>
    </div>
  )
}

// ── Tab: Matches ──────────────────────────────────────────────────────────────

function MatchesTab() {
  const { data: list = [], isLoading, refetch } = useAdminMatches()
  const matches: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{matches.length > 0 ? `${matches.length} matches` : 'Matches'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : matches.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','Match','League','Status','Date'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{matches.map((m: any, i: number) => (
                <tr key={m.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                  <td className="px-4 py-3 text-white/30 text-xs font-mono">#{m.id ?? i}</td>
                  <td className="px-4 py-3 text-white text-sm">{m.home_team ?? m.name ?? '—'}{m.away_team ? ` vs ${m.away_team}` : ''}</td>
                  <td className="px-4 py-3 text-white/50 text-xs">{m.league_name ?? m.competition ?? '—'}</td>
                  <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', m.status==='live' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : m.status==='scheduled' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-white/5 text-white/30 border-white/10')}>{m.status ?? 'unknown'}</span></td>
                  <td className="px-4 py-3 text-white/30 text-xs">{m.kickoff_time ? new Date(m.kickoff_time).toLocaleString() : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={Activity} msg="No matches found" />}
      </div>
    </div>
  )
}

// ── Tab: Validators ───────────────────────────────────────────────────────────

function ValidatorsTab() {
  const { data: list = [], isLoading, refetch } = useAdminValidators()
  const vals: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{vals.length > 0 ? `${vals.length} validators` : 'Validators'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : vals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr className="border-b border-white/8">
                {['ID','Address','Stake','Accuracy','Status','Since'].map(h => <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-4 py-3">{h}</th>)}
              </tr></thead>
              <tbody>{vals.map((v: any, i: number) => (
                <tr key={v.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                  <td className="px-4 py-3 text-white/30 text-xs font-mono">#{v.id ?? i}</td>
                  <td className="px-4 py-3 text-white/60 text-xs font-mono">{v.wallet_address ? `${v.wallet_address.slice(0,10)}…` : v.username ?? '—'}</td>
                  <td className="px-4 py-3 text-amber-400 text-sm font-medium">{v.staked_amount != null ? `${Number(v.staked_amount).toLocaleString()} VIT` : '—'}</td>
                  <td className="px-4 py-3 text-white/60 text-sm">{v.accuracy_score != null ? `${(v.accuracy_score*100).toFixed(1)}%` : '—'}</td>
                  <td className="px-4 py-3"><span className={cn('text-xs px-2 py-0.5 rounded-full border', v.status==='active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : v.status==='slashed' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-white/5 text-white/30 border-white/10')}>{v.status ?? 'unknown'}</span></td>
                  <td className="px-4 py-3 text-white/30 text-xs">{v.created_at ? new Date(v.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState icon={Shield} msg="No validators found" />}
      </div>
    </div>
  )
}

// ── Tab: Models ───────────────────────────────────────────────────────────────

function ModelsTab() {
  const { data: list = [], isLoading, refetch } = useAdminModels()
  const models: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{models.length > 0 ? `${models.length} models` : 'AI Models'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? <div className="col-span-3 flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : models.length > 0 ? models.map((m: any, i: number) => (
          <motion.div key={m.id ?? i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
            className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center"><Cpu className="w-4 h-4 text-purple-400" /></div>
              <div><p className="text-white text-sm font-medium">{m.name ?? m.model_name ?? `Model ${i+1}`}</p><p className="text-white/30 text-xs">{m.type ?? m.framework ?? '—'}</p></div>
            </div>
            {m.accuracy != null && <Row label="Accuracy" value={`${(m.accuracy*100).toFixed(1)}%`} />}
            {m.version  != null && <Row label="Version"  value={m.version} />}
            {m.status   != null && <Row label="Status"   value={m.status}  />}
          </motion.div>
        )) : <div className="col-span-3"><EmptyState icon={Cpu} msg="No models found" /></div>}
      </div>
    </div>
  )
}

// ── Tab: Config ───────────────────────────────────────────────────────────────

function ConfigTab() {
  const { data: cfg, isLoading } = useAdminConfig()
  const config = cfg ?? {}
  const featureFlags = [
    { key: 'predictions_enabled', label: 'Predictions' }, { key: 'wallet_enabled', label: 'Wallet' },
    { key: 'governance_enabled',  label: 'Governance'  }, { key: 'marketplace_enabled', label: 'Marketplace' },
    { key: 'defi_enabled',        label: 'DeFi Pools'  }, { key: 'social_enabled', label: 'Social Feed' },
    { key: 'inplay_enabled',      label: 'In-Play'     }, { key: 'analytics_enabled', label: 'Analytics' },
    { key: 'enterprise_enabled',  label: 'Enterprise'  },
  ]
  return (
    <div className="space-y-6">
      {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div> : (
        <>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Feature Flags</h3>
            <div className="grid sm:grid-cols-2 gap-2">
              {featureFlags.map(f => {
                const enabled = config[f.key] !== false
                return (
                  <div key={f.key} className="flex items-center justify-between p-3 rounded-lg bg-white/3 border border-white/6">
                    <span className="text-sm text-white/70">{f.label}</span>
                    <div className={cn('flex items-center gap-1.5 text-xs font-medium', enabled ? 'text-emerald-400' : 'text-white/25')}>
                      {enabled ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                      {enabled ? 'Enabled' : 'Disabled'}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          {cfg && Object.keys(config).length > 0 && (
            <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">Raw Config</h3>
              <pre className="text-xs text-white/50 overflow-x-auto leading-relaxed">{JSON.stringify(config, null, 2)}</pre>
            </div>
          )}
          {(!cfg || Object.keys(config).length === 0) && <EmptyState icon={Settings} msg={cfg === null ? 'Admin access required' : 'No config data'} />}
        </>
      )}
    </div>
  )
}

// ── Tab: Audit ────────────────────────────────────────────────────────────────

function AuditTab() {
  const { data: list = [], isLoading, refetch } = useAdminAudit()
  const entries: any[] = Array.isArray(list) ? list : []
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">{entries.length > 0 ? `${entries.length} entries` : 'Audit Log'}</p>
        <button onClick={() => refetch()} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
        {isLoading ? <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
        : entries.length > 0 ? (
          <div>{entries.map((e: any, i: number) => (
            <div key={e.id ?? i} className="flex items-start gap-4 px-5 py-4 border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
              <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center shrink-0"><ClipboardList className="w-4 h-4 text-white/25" /></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-medium">{e.action ?? e.event ?? `Event ${i+1}`}</p>
                {e.user_id && <p className="text-xs text-white/40 mt-0.5">User #{e.user_id}{e.ip_address ? ` · ${e.ip_address}` : ''}</p>}
                {e.details && <p className="text-xs text-white/25 mt-0.5 truncate">{typeof e.details === 'object' ? JSON.stringify(e.details) : e.details}</p>}
              </div>
              <p className="text-xs text-white/25 shrink-0">{e.created_at ? new Date(e.created_at).toLocaleString() : '—'}</p>
            </div>
          ))}</div>
        ) : <EmptyState icon={ClipboardList} msg="No audit entries found" />}
      </div>
    </div>
  )
}

// ── Tab: System ───────────────────────────────────────────────────────────────

function SystemTab({ health, status, metrics, loadingHealth, loadingStatus }: any) {
  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Server className="w-4 h-4 text-vit-400" /> Gateway Info</h3>
          {loadingHealth ? <Spinner className="w-4 h-4 text-vit-400" /> : <>
            <Row label="Version"     value={health?.version ?? status?.version ?? '—'} />
            <Row label="Environment" value={health?.environment ?? 'production'} />
            <Row label="DB"          value={health?.db_connected !== false ? 'Connected' : 'Disconnected'} />
            <Row label="Redis"       value={health?.redis?.status ?? '—'} />
            <Row label="Models"      value={health?.models_loaded != null ? `${health.models_loaded} loaded` : '—'} />
            <Row label="Uptime"      value={health?.uptime_seconds ? `${Math.floor(health.uptime_seconds/3600)}h ${Math.floor((health.uptime_seconds%3600)/60)}m` : '—'} />
          </>}
        </div>
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Globe className="w-4 h-4 text-emerald-400" /> Platform Stats</h3>
          {loadingStatus ? <Spinner className="w-4 h-4 text-vit-400" /> : <>
            <Row label="Total Users"        value={status?.total_users?.toLocaleString()} />
            <Row label="Active Users (30d)" value={status?.active_users_30d?.toLocaleString()} />
            <Row label="Active Validators"  value={status?.active_validators?.toLocaleString()} />
            <Row label="Total Predictions"  value={status?.total_predictions?.toLocaleString()} />
          </>}
        </div>
      </div>
      {metrics && (
        <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Activity className="w-4 h-4 text-blue-400" /> Runtime</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard icon={Zap}           label="Req/min"     value={metrics.requests_per_minute}                                             color="text-vit-400"     />
            <MetricCard icon={Clock}         label="Avg Latency" value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms}ms` : null}           color="text-blue-400"   />
            <MetricCard icon={AlertTriangle} label="Error Rate"  value={metrics.error_rate ? `${(metrics.error_rate*100).toFixed(2)}%` : null}   color="text-red-400"    />
            <MetricCard icon={Database}      label="DB Pool"     value={metrics.db_pool_size}                                                    color="text-emerald-400" />
          </div>
        </div>
      )}
      <div className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-4"><Layers className="w-4 h-4 text-amber-400" /> Service Endpoints</h3>
        <Row label="Gateway" value={ENDPOINTS.gateway} />
        <Row label="AI"      value={ENDPOINTS.ai}      />
        <Row label="Storage" value={ENDPOINTS.storage} />
      </div>
    </div>
  )
}

// ── Tabs config ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',    label: 'Overview',   icon: BarChart2    },
  { id: 'users',       label: 'Users',      icon: Users        },
  { id: 'wallet',      label: 'Wallet',     icon: WalletIcon   },
  { id: 'matches',     label: 'Matches',    icon: Activity     },
  { id: 'validators',  label: 'Validators', icon: Shield       },
  { id: 'models',      label: 'Models',     icon: Cpu          },
  { id: 'config',      label: 'Config',     icon: Settings     },
  { id: 'audit',       label: 'Audit',      icon: ClipboardList},
  { id: 'system',      label: 'System',     icon: Server       },
] as const
type TabId = typeof TABS[number]['id']

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Admin() {
  const navigate    = useNavigate()
  const token       = getAuthToken()
  const user        = getStoredUser()
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  useEffect(() => { if (!token) navigate('/login', { replace: true }) }, [token, navigate])

  const { data: status,  isLoading: loadingStatus,  refetch: refetchStatus  } = useSystemStatus()
  const { data: health,  isLoading: loadingHealth,  refetch: refetchHealth  } = useAdminHealth()
  const { data: metrics                                                       } = useAdminMetrics()

  if (!token) return <div className="pt-16 min-h-screen flex items-center justify-center"><Spinner className="w-8 h-8 text-vit-400" /></div>

  if (user?.role && user.role !== 'admin') return (
    <div className="pt-16 min-h-screen flex items-center justify-center">
      <div className="text-center max-w-sm mx-4">
        <div className="w-14 h-14 rounded-full bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-6 h-6 text-yellow-400" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Admin Access Required</h2>
        <p className="text-white/40 text-sm mb-6">This page is restricted to administrators.</p>
        <Link to="/dashboard" className="px-5 py-2.5 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors">Back to Dashboard</Link>
      </div>
    </div>
  )

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-25" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center justify-between">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-lg">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Administration</h1>
                <p className="text-white/40 text-sm">System management and monitoring</p>
              </div>
            </motion.div>
            <button onClick={() => { refetchStatus(); refetchHealth() }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800/60 border border-white/10 text-white/50 hover:text-white text-sm transition-all">
              <RefreshCw className={cn('w-3.5 h-3.5', (loadingStatus || loadingHealth) && 'animate-spin')} />
              Refresh
            </button>
          </div>
          {/* Tab bar */}
          <div className="flex items-center gap-1 mt-6 overflow-x-auto pb-px">
            {TABS.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={cn('flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
                  activeTab === tab.id ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70 hover:bg-white/5')}>
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {activeTab === 'overview'   && <OverviewTab  status={status} health={health} metrics={metrics} refetchStatus={refetchStatus} refetchHealth={refetchHealth} loadingStatus={loadingStatus} loadingHealth={loadingHealth} />}
        {activeTab === 'users'      && <UsersTab      />}
        {activeTab === 'wallet'     && <WalletAdminTab />}
        {activeTab === 'matches'    && <MatchesTab    />}
        {activeTab === 'validators' && <ValidatorsTab />}
        {activeTab === 'models'     && <ModelsTab     />}
        {activeTab === 'config'     && <ConfigTab     />}
        {activeTab === 'audit'      && <AuditTab      />}
        {activeTab === 'system'     && <SystemTab     status={status} health={health} metrics={metrics} loadingStatus={loadingStatus} loadingHealth={loadingHealth} />}
      </div>
    </div>
  )
}
