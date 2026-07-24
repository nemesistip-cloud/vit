import { useState, type MouseEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Building2, Key, Webhook, Database, Check,
  X, Plus, Trash2, Eye, EyeOff, Copy, ExternalLink,
  AlertTriangle, Send, ChevronRight, Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Plan {
  id: string
  name: string
  price_usd_month: number | null
  requests_per_min: number
  daily_limit: number | null
  features: string[]
  webhooks: number
  data_bundles: string[]
}

interface APIKey {
  id: string
  name: string
  description: string
  plan: string
  key_preview: string
  status: 'active' | 'revoked'
  created_at: number
  last_used_at: number | null
  requests_today: number
  daily_limit: number | null
  rpm_limit: number
}

interface Webhook {
  id: string
  name: string
  url: string
  events: string[]
  active: boolean
  created_at: number
  success_count: number
  failure_count: number
}

interface DataBundle {
  id: string
  name: string
  records_per_day: number
  price_usd: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

const BASE = () => `${ENDPOINTS.gateway}/api/enterprise`

function usePlans() {
  return useQuery({
    queryKey: ['enterprise-plans'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/plans`, { signal })
      return r.ok ? r.json() : { plans: [] }
    },
    staleTime: 300_000,
  })
}

function useAPIKeys() {
  return useQuery({
    queryKey: ['enterprise-keys'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/api-keys`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { keys: [] }
    },
    staleTime: 30_000,
  })
}

function useWebhooks() {
  return useQuery({
    queryKey: ['enterprise-webhooks'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/webhooks`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { webhooks: [] }
    },
    staleTime: 30_000,
  })
}

function useDataBundles() {
  return useQuery({
    queryKey: ['enterprise-bundles'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/data-bundles`, { signal })
      return r.ok ? r.json() : { bundles: [] }
    },
    staleTime: 300_000,
  })
}

// ── Create API key modal ───────────────────────────────────────────────────────

function CreateKeyModal({ plans, onClose }: { plans: Plan[]; onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ name: '', plan: 'starter', description: '' })
  const [revealed, setRevealed] = useState('')
  const [err, setErr] = useState('')

  const create = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/api-keys`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed') }
      return r.json()
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['enterprise-keys'] })
      setRevealed(data.key)
    },
    onError: (e: Error) => setErr(e.message),
  })

  if (revealed) {
    return (
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          className="w-full max-w-md bg-surface-900 border border-white/10 rounded-2xl p-6 space-y-4"
        >
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-5 h-5 text-emerald-400" />
            <h2 className="font-semibold text-white">API Key Created</h2>
          </div>
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
            <div className="flex items-start gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-300">Copy this key now — it won't be shown again.</p>
            </div>
            <div className="font-mono text-xs text-white bg-black/30 rounded-lg p-3 break-all select-all">{revealed}</div>
          </div>
          <button
            onClick={() => { navigator.clipboard.writeText(revealed); onClose() }}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-vit-500 hover:bg-vit-600 text-white rounded-xl text-sm font-medium transition-colors"
          >
            <Copy className="w-4 h-4" />
            Copy & Close
          </button>
        </motion.div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e: MouseEvent) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-md bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/8">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-vit-400" />
            <span className="font-semibold text-white">Create API Key</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Key Name</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Production API Key"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50" />
          </div>
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Plan</label>
            <select value={form.plan} onChange={e => setForm(f => ({ ...f, plan: e.target.value }))}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-vit-500/50">
              {plans.map(p => <option key={p.id} value={p.id}>{p.name} {p.price_usd_month ? `— $${p.price_usd_month}/mo` : '— Contact sales'}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Description (optional)</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={2} placeholder="What will this key be used for?"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50 resize-none" />
          </div>
          {err && <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400"><AlertTriangle className="w-4 h-4" />{err}</div>}
          <button onClick={() => create.mutate()} disabled={!form.name.trim() || create.isPending}
            className="w-full py-2.5 bg-vit-500 hover:bg-vit-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-40">
            {create.isPending ? <Spinner className="w-4 h-4 mx-auto" /> : 'Generate Key'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Create webhook modal ──────────────────────────────────────────────────────

const ALL_EVENTS = ['prediction.settled','match.result','odds.update','user.stake','defi.yield','inplay.bet','governance.vote']

function CreateWebhookModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ url: '', events: [] as string[], name: '', secret: '' })
  const [err, setErr] = useState('')

  const create = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/webhooks`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed') }
      return r.json()
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['enterprise-webhooks'] }); onClose() },
    onError: (e: Error) => setErr(e.message),
  })

  function toggleEvent(ev: string) {
    setForm(f => ({ ...f, events: f.events.includes(ev) ? f.events.filter(e => e !== ev) : [...f.events, ev] }))
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e: MouseEvent) => e.target === e.currentTarget && onClose()}>
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-md bg-surface-900 border border-white/10 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-white/8">
          <div className="flex items-center gap-2"><Webhook className="w-4 h-4 text-vit-400" /><span className="font-semibold text-white">Add Webhook</span></div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Endpoint URL</label>
            <input value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
              placeholder="https://your-server.com/webhook"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50" />
          </div>
          <div>
            <label className="block text-xs font-medium text-white/50 mb-2">Events to receive</label>
            <div className="flex flex-wrap gap-1.5">
              {ALL_EVENTS.map(ev => (
                <button key={ev} onClick={() => toggleEvent(ev)}
                  className={cn('px-2 py-1 rounded-lg text-xs border transition-all',
                    form.events.includes(ev) ? 'bg-vit-500/20 text-vit-300 border-vit-500/30' : 'bg-white/3 text-white/50 border-white/10 hover:border-white/20')}>
                  {ev}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Signing Secret (optional)</label>
            <input type="password" value={form.secret} onChange={e => setForm(f => ({ ...f, secret: e.target.value }))}
              placeholder="Used to sign payloads (HMAC-SHA256)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50" />
          </div>
          {err && <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400"><AlertTriangle className="w-4 h-4" />{err}</div>}
          <button onClick={() => create.mutate()} disabled={!form.url.trim() || form.events.length === 0 || create.isPending}
            className="w-full py-2.5 bg-vit-500 hover:bg-vit-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-40">
            {create.isPending ? <Spinner className="w-4 h-4 mx-auto" /> : 'Create Webhook'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Enterprise() {
  const navigate  = useNavigate()
  const qc        = useQueryClient()
  const [tab, setTab] = useState<'plans' | 'keys' | 'webhooks' | 'data'>('plans')
  const [showCreateKey,  setShowCreateKey]  = useState(false)
  const [showCreateHook, setShowCreateHook] = useState(false)

  useEffect(() => {
    if (!getAuthToken()) navigate('/login')
  }, [navigate])

  const { data: plansData   } = usePlans()
  const { data: keysData    } = useAPIKeys()
  const { data: hooksData   } = useWebhooks()
  const { data: bundlesData } = useDataBundles()

  const plans:   Plan[]        = plansData?.plans    ?? []
  const keys:    APIKey[]      = keysData?.keys      ?? []
  const hooks:   Webhook[]     = hooksData?.webhooks ?? []
  const bundles: DataBundle[]  = bundlesData?.bundles ?? []

  const TABS = [
    { id: 'plans',    label: 'Plans',      icon: Building2 },
    { id: 'keys',     label: `API Keys (${keys.length})`, icon: Key },
    { id: 'webhooks', label: `Webhooks (${hooks.length})`, icon: Webhook },
    { id: 'data',     label: 'Data Licensing', icon: Database },
  ] as const

  // Revoke key
  const revokeKey = useMutation({
    mutationFn: async (keyId: string) => {
      const r = await fetch(`${BASE()}/api-keys/${keyId}`, { method: 'DELETE', headers: authHeaders() })
      if (!r.ok) throw new Error('Failed')
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['enterprise-keys'] }),
  })

  // Delete webhook
  const deleteHook = useMutation({
    mutationFn: async (hookId: string) => {
      const r = await fetch(`${BASE()}/webhooks/${hookId}`, { method: 'DELETE', headers: authHeaders() })
      if (!r.ok) throw new Error('Failed')
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['enterprise-webhooks'] }),
  })

  // Test webhook
  const testHook = useMutation({
    mutationFn: async (hookId: string) => {
      const r = await fetch(`${BASE()}/webhooks/${hookId}/test`, { method: 'POST', headers: authHeaders() })
      if (!r.ok) throw new Error('Failed')
      return r.json()
    },
  })

  return (
    <div className="min-h-screen bg-surface-950 pt-24 pb-16">
      <div className="max-w-5xl mx-auto px-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-sky-500/15 border border-sky-500/25 rounded-xl">
              <Building2 className="w-5 h-5 text-sky-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Enterprise Portal</h1>
              <p className="text-white/50 text-sm">API keys, webhooks, data licensing & commercial access</p>
            </div>
          </div>
        </motion.div>

        {/* Tab bar */}
        <div className="flex gap-1 mb-6 bg-white/3 border border-white/8 rounded-xl p-1 overflow-x-auto">
          {TABS.map(t => {
            const Icon = t.icon
            return (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={cn('flex-shrink-0 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
                  tab === t.id ? 'bg-vit-500/20 text-vit-300 border border-vit-500/30' : 'text-white/50 hover:text-white/80')}>
                <Icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Plans */}
        {tab === 'plans' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {plans.map((plan, i) => (
              <div key={plan.id}
                className={cn('rounded-2xl border p-5 space-y-4 relative overflow-hidden',
                  i === 1 ? 'bg-vit-500/5 border-vit-500/30' : 'bg-white/3 border-white/8')}>
                {i === 1 && <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-vit-500 via-vit-400 to-vit-600" />}
                <div>
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-1">{plan.name}</p>
                  <div className="flex items-baseline gap-1">
                    {plan.price_usd_month
                      ? <><span className="text-3xl font-bold text-white">${plan.price_usd_month}</span><span className="text-white/40 text-sm">/mo</span></>
                      : <span className="text-xl font-bold text-white">Contact Sales</span>}
                  </div>
                </div>
                <div className="space-y-1.5">
                  {plan.features.map(f => (
                    <div key={f} className="flex items-center gap-2 text-sm text-white/70">
                      <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      {f}
                    </div>
                  ))}
                </div>
                <div className="pt-2 border-t border-white/5 text-xs text-white/40 space-y-0.5">
                  <div>{plan.requests_per_min} req/min</div>
                  <div>{plan.daily_limit ? `${plan.daily_limit.toLocaleString()} req/day` : 'Unlimited requests'}</div>
                  <div>{plan.webhooks} webhooks</div>
                </div>
                <button
                  onClick={() => setTab('keys')}
                  className={cn('w-full py-2 rounded-xl text-sm font-medium transition-colors',
                    i === 1 ? 'bg-vit-500 hover:bg-vit-600 text-white' : 'bg-white/5 hover:bg-white/10 text-white/70')}>
                  {plan.price_usd_month ? 'Get Started' : 'Contact Us'}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* API Keys */}
        {tab === 'keys' && (
          <div>
            <div className="flex justify-end mb-4">
              <button onClick={() => setShowCreateKey(true)}
                className="flex items-center gap-2 px-4 py-2 bg-vit-500 hover:bg-vit-600 text-white rounded-xl text-sm font-medium transition-colors">
                <Plus className="w-4 h-4" /> New Key
              </button>
            </div>
            {keys.length === 0 && (
              <div className="text-center py-14">
                <Key className="w-10 h-10 text-white/20 mx-auto mb-3" />
                <p className="text-white/40 text-sm">No API keys yet. Create one to get started.</p>
              </div>
            )}
            <div className="space-y-3">
              {keys.map(k => (
                <div key={k.id} className="flex items-center justify-between p-4 bg-white/3 border border-white/8 rounded-xl">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-white">{k.name}</span>
                      <span className={cn('px-1.5 py-0.5 rounded text-xs', k.status === 'active' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400')}>{k.status}</span>
                      <span className="px-1.5 py-0.5 rounded text-xs bg-white/10 text-white/50 capitalize">{k.plan}</span>
                    </div>
                    <p className="font-mono text-xs text-white/30">{k.key_preview}</p>
                    <p className="text-xs text-white/30 mt-0.5">{k.requests_today} / {k.daily_limit?.toLocaleString() ?? '∞'} req today</p>
                  </div>
                  <button onClick={() => revokeKey.mutate(k.id)} disabled={k.status !== 'active' || revokeKey.isPending}
                    className="p-2 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-30">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            <AnimatePresence>
              {showCreateKey && <CreateKeyModal plans={plans} onClose={() => setShowCreateKey(false)} />}
            </AnimatePresence>
          </div>
        )}

        {/* Webhooks */}
        {tab === 'webhooks' && (
          <div>
            <div className="flex justify-end mb-4">
              <button onClick={() => setShowCreateHook(true)}
                className="flex items-center gap-2 px-4 py-2 bg-vit-500 hover:bg-vit-600 text-white rounded-xl text-sm font-medium transition-colors">
                <Plus className="w-4 h-4" /> Add Webhook
              </button>
            </div>
            {hooks.length === 0 && (
              <div className="text-center py-14">
                <Webhook className="w-10 h-10 text-white/20 mx-auto mb-3" />
                <p className="text-white/40 text-sm">No webhooks configured. Add one to receive real-time events.</p>
              </div>
            )}
            <div className="space-y-3">
              {hooks.map(h => (
                <div key={h.id} className="p-4 bg-white/3 border border-white/8 rounded-xl">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-medium text-sm text-white">{h.name || 'Unnamed webhook'}</span>
                        <span className={cn('px-1.5 py-0.5 rounded text-xs', h.active ? 'bg-emerald-500/15 text-emerald-400' : 'bg-white/10 text-white/40')}>
                          {h.active ? 'active' : 'paused'}
                        </span>
                      </div>
                      <p className="text-xs text-white/40 font-mono truncate max-w-sm">{h.url}</p>
                    </div>
                    <div className="flex gap-1.5">
                      <button onClick={() => testHook.mutate(h.id)} disabled={testHook.isPending}
                        title="Send test event"
                        className="p-1.5 text-white/40 hover:text-sky-400 hover:bg-sky-500/10 rounded-lg transition-colors">
                        <Send className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => deleteHook.mutate(h.id)} disabled={deleteHook.isPending}
                        className="p-1.5 text-white/40 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {h.events.map(ev => (
                      <span key={ev} className="px-1.5 py-0.5 bg-vit-500/10 text-vit-400/70 border border-vit-500/15 rounded text-xs">{ev}</span>
                    ))}
                  </div>
                  <div className="flex gap-4 mt-2 text-xs text-white/30">
                    <span>✓ {h.success_count} delivered</span>
                    <span>{h.failure_count > 0 ? `✗ ${h.failure_count} failed` : ''}</span>
                  </div>
                </div>
              ))}
            </div>
            <AnimatePresence>
              {showCreateHook && <CreateWebhookModal onClose={() => setShowCreateHook(false)} />}
            </AnimatePresence>
          </div>
        )}

        {/* Data bundles */}
        {tab === 'data' && (
          <div>
            <p className="text-white/50 text-sm mb-4">License VIT Network data for commercial use, research, or product integration.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {bundles.map(b => (
                <div key={b.id} className="bg-white/3 border border-white/8 rounded-xl p-4 hover:border-white/15 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-semibold text-sm text-white">{b.name}</p>
                      <p className="text-xs text-white/40">{b.records_per_day.toLocaleString()} records/day</p>
                    </div>
                    <span className="text-lg font-bold text-vit-300">${b.price_usd}<span className="text-xs text-white/40">/mo</span></span>
                  </div>
                  <button className="w-full mt-2 py-1.5 bg-vit-500/15 hover:bg-vit-500/25 text-vit-300 border border-vit-500/25 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5">
                    Request License <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
