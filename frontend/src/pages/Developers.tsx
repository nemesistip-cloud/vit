import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Code, Zap, Terminal, Copy, CheckCheck, ExternalLink, Key, Plus,
  Trash2, RefreshCw, Shield, Activity, BarChart3, Clock, AlertCircle,
  Webhook, Send, Eye, EyeOff, Layers, Play, CheckCircle2,
  GitBranch, GitCommit, GitPullRequest, Search, FileText, ChevronRight
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken, getStoredUser } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

// ── Types ─────────────────────────────────────────────────────────────────────

interface DevKey {
  id: number
  name: string
  key_prefix: string
  key?: string
  raw_value?: string
  plan: string
  rate_limit_rpm: number
  rate_limit_rpd: number
  is_active: boolean
  total_requests: number
  total_vitcoin_billed: string
  created_at: string
  last_used_at?: string
  expires_at?: string
}

interface DevUsageLog {
  id: number
  endpoint: string
  method: string
  status_code: number
  latency_ms?: number
  vitcoin_billed: string
  called_at: string
}

interface DevUsageSummary {
  total_api_calls: number
  successful_calls: number
  error_calls: number
  success_rate: number
  total_keys: number
  active_keys: number
}

interface DevWebhook {
  id: number
  url: string
  description?: string
  secret?: string
  events: string[]
  is_active: boolean
  failure_count: number
  last_called_at?: string
  created_at: string
}

interface WebhookLog {
  id: number
  webhook_id: number
  event_type: string
  payload: any
  status_code?: number
  response_body?: string
  latency_ms?: number
  success: boolean
  error_message?: string
  delivered_at: string
}

interface DevPlan {
  name: string
  display_name: string
  rate_limit_rpm: number
  rate_limit_rpd: number
  price_vitcoin_per_1k: string
  description: string
}

interface DevEndpointDoc {
  method: string
  path: string
  description: string
  tags: string[]
}

interface DevDocsResponse {
  openapi_url: string
  redoc_url: string
  swagger_url: string
  base_api_url: string
  endpoint_count: number
  endpoints: DevEndpointDoc[]
}

interface GitStatus {
  branch: string
  dirty_files: string
  remote_url: string
  commits_ahead: number
  commits_behind: number
  recent_log: string
  is_clean: boolean
}

// ── Shared UI Helpers ─────────────────────────────────────────────────────────

function CopyBtn({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors",
      copied ? "bg-green-400/10 text-green-300 border-green-400/30" : "bg-white/5 text-white/60 border-white/10 hover:text-white hover:bg-white/10")}>
      {copied ? <CheckCheck className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : label}
    </button>
  )
}

function MethodBadge({ method }: { method: string }) {
  const m = method.toUpperCase()
  const colors: Record<string, string> = {
    GET: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20',
    POST: 'bg-blue-400/10 text-blue-400 border-blue-400/20',
    PATCH: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
    PUT: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
    DELETE: 'bg-red-400/10 text-red-400 border-red-400/20',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase', colors[m] || 'bg-white/10 text-white border-white/20')}>
      {m}
    </span>
  )
}

function StatusBadge({ code }: { code: number }) {
  if (code >= 200 && code < 300) return <span className="text-emerald-400 font-mono text-xs">{code} OK</span>
  if (code >= 400 && code < 500) return <span className="text-amber-400 font-mono text-xs">{code} ERR</span>
  return <span className="text-red-400 font-mono text-xs">{code} FAIL</span>
}

// ── Tab 1: API Keys ───────────────────────────────────────────────────────────

function ApiKeysTab({ isAuth }: { isAuth: boolean }) {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [keyPlan, setKeyPlan] = useState('free')
  const [newKeyRevealed, setNewKeyRevealed] = useState<string | null>(null)
  const [rotatedKey, setRotatedKey] = useState<{ name: string; key: string } | null>(null)

  const { data: keys = [], isLoading } = useQuery<DevKey[]>({
    queryKey: ['dev-keys'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/keys`, { headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load keys')
      return r.json()
    },
    enabled: isAuth,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/keys`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: keyName, plan: keyPlan }),
      })
      if (!r.ok) throw new Error('Key creation failed')
      return r.json()
    },
    onSuccess: (data: DevKey) => {
      qc.invalidateQueries({ queryKey: ['dev-keys'] })
      setNewKeyRevealed(data.key || data.raw_value || null)
      setKeyName('')
      setShowCreate(false)
    },
  })

  const rotateMutation = useMutation({
    mutationFn: async (id: number) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/keys/${id}/regenerate`, {
        method: 'POST',
        headers: authHeaders(),
      })
      if (!r.ok) throw new Error('Key rotation failed')
      return r.json()
    },
    onSuccess: (data: DevKey) => {
      qc.invalidateQueries({ queryKey: ['dev-keys'] })
      setRotatedKey({ name: data.name, key: data.key || data.raw_value || '' })
    },
  })

  const revokeMutation = useMutation({
    mutationFn: async (id: number) => {
      await fetch(`${ENDPOINTS.gateway}/api/developer/keys/${id}/revoke`, {
        method: 'PATCH',
        headers: authHeaders(),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dev-keys'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await fetch(`${ENDPOINTS.gateway}/api/developer/keys/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dev-keys'] }),
  })

  if (!isAuth) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/50">
        <Key className="w-10 h-10 mx-auto mb-3 opacity-30 text-vit-400" />
        <p className="text-base font-semibold text-white">Authentication Required</p>
        <p className="text-sm text-white/40 mt-1">Please sign in to generate and manage developer API keys.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Developer API Keys</h2>
          <p className="text-sm text-white/40">Include keys in the <code className="text-vit-300 font-mono">X-API-Key</code> request header.</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vit-400 hover:bg-vit-300 text-black font-semibold text-sm transition-colors">
          <Plus className="w-4 h-4" /> Create New Key
        </button>
      </div>

      {/* Creation Modal / Form */}
      {showCreate && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-2xl border border-vit-400/30 bg-vit-400/5 space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Key className="w-4 h-4 text-vit-400" /> Generate New API Key
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-white/60 mb-1 block font-medium">Key Name / Identifier</label>
              <input value={keyName} onChange={e => setKeyName(e.target.value)} required placeholder="e.g. Production Trading Bot"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-vit-400/50" />
            </div>
            <div>
              <label className="text-xs text-white/60 mb-1 block font-medium">Pricing Plan</label>
              <select value={keyPlan} onChange={e => setKeyPlan(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-vit-400/50">
                <option value="free" className="bg-[#0f111a]">Free (60 RPM / 1k RPD)</option>
                <option value="starter" className="bg-[#0f111a]">Starter (120 RPM / 5k RPD)</option>
                <option value="pro" className="bg-[#0f111a]">Pro (300 RPM / 50k RPD)</option>
                <option value="enterprise" className="bg-[#0f111a]">Enterprise (1,000 RPM)</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 text-sm">Cancel</button>
            <button onClick={() => createMutation.mutate()} disabled={!keyName || createMutation.isPending}
              className="px-5 py-2 rounded-xl bg-vit-400 hover:bg-vit-300 text-black font-semibold text-sm transition-colors disabled:opacity-50 flex items-center gap-2">
              {createMutation.isPending ? <Spinner className="w-4 h-4" /> : <Key className="w-4 h-4" />} Generate Key
            </button>
          </div>
        </motion.div>
      )}

      {/* Secret Reveal Banner (One-time) */}
      {(newKeyRevealed || rotatedKey) && (
        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
          className="p-5 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-300 font-semibold text-sm">
              <CheckCircle2 className="w-5 h-5" /> API Key Generated / Rotated Successfully!
            </div>
            <button onClick={() => { setNewKeyRevealed(null); setRotatedKey(null) }} className="text-white/40 hover:text-white text-xs">Dismiss</button>
          </div>
          <p className="text-xs text-white/60">
            Make sure to copy your API key now. For security reasons, <span className="text-white font-medium">it will not be shown again</span>.
          </p>
          <div className="flex items-center gap-2 p-3 bg-black/40 border border-emerald-400/20 rounded-xl font-mono text-sm text-emerald-300">
            <span className="flex-1 truncate">{newKeyRevealed || rotatedKey?.key}</span>
            <CopyBtn text={newKeyRevealed || rotatedKey?.key || ''} label="Copy Secret" />
          </div>
        </motion.div>
      )}

      {/* Key Table */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>
      ) : keys.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/40">
          <Key className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No API keys created yet. Generate your first key to start integrating.</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
          <div className="divide-y divide-white/5">
            {keys.map(k => (
              <div key={k.id} className="p-5 flex flex-wrap items-center justify-between gap-4 hover:bg-white/[0.02] transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-white text-base">{k.name}</span>
                    <span className={cn("px-2 py-0.5 rounded-full text-[10px] uppercase font-bold border",
                      k.is_active ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/20" : "bg-red-400/10 text-red-400 border-red-400/20")}>
                      {k.is_active ? 'Active' : 'Revoked'}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-white/10 text-white/70">{k.plan}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-mono text-white/40">
                    <span>Prefix: <span className="text-vit-300">{k.key_prefix}...</span></span>
                    <span>Requests: {k.total_requests.toLocaleString()}</span>
                    <span>RPM: {k.rate_limit_rpm}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {k.is_active && (
                    <>
                      <button onClick={() => rotateMutation.mutate(k.id)} disabled={rotateMutation.isPending} title="Rotate Key"
                        className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/70 hover:text-white transition-colors">
                        <RefreshCw className={cn("w-4 h-4", rotateMutation.isPending && "animate-spin")} />
                      </button>
                      <button onClick={() => revokeMutation.mutate(k.id)} title="Revoke Key"
                        className="p-2 rounded-xl bg-amber-400/10 hover:bg-amber-400/20 text-amber-400 transition-colors">
                        <Shield className="w-4 h-4" />
                      </button>
                    </>
                  )}
                  <button onClick={() => deleteMutation.mutate(k.id)} title="Delete Key"
                    className="p-2 rounded-xl bg-red-400/10 hover:bg-red-400/20 text-red-400 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab 2: Usage Logs & Analytics ─────────────────────────────────────────────

function UsageTab({ isAuth }: { isAuth: boolean }) {
  const [filterText, setFilterText] = useState('')

  const { data: summary } = useQuery<DevUsageSummary>({
    queryKey: ['dev-usage-summary'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/usage/summary`, { headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load summary')
      return r.json()
    },
    enabled: isAuth,
  })

  const { data: logs = [], isLoading, refetch } = useQuery<DevUsageLog[]>({
    queryKey: ['dev-usage-logs'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/usage?limit=100`, { headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load logs')
      return r.json()
    },
    enabled: isAuth,
  })

  const filteredLogs = logs.filter(l => l.endpoint.toLowerCase().includes(filterText.toLowerCase()))

  if (!isAuth) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/50">
        <Activity className="w-10 h-10 mx-auto mb-3 opacity-30 text-vit-400" />
        <p className="text-base font-semibold text-white">Authentication Required</p>
        <p className="text-sm text-white/40 mt-1">Please sign in to view real-time API call metrics and logs.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total API Calls', value: summary?.total_api_calls.toLocaleString() ?? '0', icon: <Activity className="w-4 h-4 text-vit-400" /> },
          { label: 'Success Rate', value: `${summary?.success_rate ?? 100}%`, icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" /> },
          { label: 'Active Keys', value: summary?.active_keys.toString() ?? '0', icon: <Key className="w-4 h-4 text-blue-400" /> },
          { label: 'Error Responses', value: summary?.error_calls.toLocaleString() ?? '0', icon: <AlertCircle className="w-4 h-4 text-amber-400" /> },
        ].map(m => (
          <div key={m.label} className="p-4 rounded-2xl border border-white/10 bg-white/5 space-y-1">
            <div className="flex items-center justify-between text-xs text-white/50">
              <span>{m.label}</span>
              {m.icon}
            </div>
            <p className="text-2xl font-bold text-white font-mono">{m.value}</p>
          </div>
        ))}
      </div>

      {/* Logs Table Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-white/30" />
          <input value={filterText} onChange={e => setFilterText(e.target.value)} placeholder="Filter logs by endpoint path..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-vit-400/50" />
        </div>
        <button onClick={() => refetch()} className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/70 text-xs font-medium border border-white/10">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Logs
        </button>
      </div>

      {/* Logs Table */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>
      ) : filteredLogs.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/40">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No API call logs recorded yet.</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-white/10 bg-white/5 overflow-x-auto">
          <table className="w-full text-left text-sm font-mono">
            <thead className="bg-white/5 text-xs text-white/40 uppercase tracking-wider border-b border-white/10">
              <tr>
                <th className="p-3.5">Method</th>
                <th className="p-3.5">Endpoint</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Latency</th>
                <th className="p-3.5">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredLogs.map(log => (
                <tr key={log.id} className="hover:bg-white/[0.02]">
                  <td className="p-3.5"><MethodBadge method={log.method} /></td>
                  <td className="p-3.5 text-vit-300 font-semibold">{log.endpoint}</td>
                  <td className="p-3.5"><StatusBadge code={log.status_code} /></td>
                  <td className="p-3.5 text-white/60">{log.latency_ms ? `${log.latency_ms} ms` : '—'}</td>
                  <td className="p-3.5 text-white/40 text-xs">{new Date(log.called_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Tab 3: Webhooks Manager ───────────────────────────────────────────────────

function WebhooksTab({ isAuth }: { isAuth: boolean }) {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [url, setUrl] = useState('')
  const [desc, setDesc] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<string[]>(['prediction.resolved'])
  const [testResult, setTestResult] = useState<{ id: number; msg: string; success: boolean } | null>(null)
  const [activeLogsWh, setActiveLogsWh] = useState<number | null>(null)

  const ALL_EVENTS = [
    { id: 'prediction.resolved', label: 'Prediction Resolved' },
    { id: 'match.started', label: 'Match Started' },
    { id: 'match.settled', label: 'Match Settled' },
    { id: 'wallet.transaction', label: 'Wallet Transaction' },
  ]

  const { data: webhooks = [], isLoading } = useQuery<DevWebhook[]>({
    queryKey: ['dev-webhooks'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/webhooks`, { headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load webhooks')
      return r.json()
    },
    enabled: isAuth,
  })

  const { data: whLogs = [] } = useQuery<WebhookLog[]>({
    queryKey: ['dev-webhook-logs', activeLogsWh],
    queryFn: async () => {
      if (!activeLogsWh) return []
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/webhooks/${activeLogsWh}/logs`, { headers: authHeaders() })
      if (!r.ok) return []
      return r.json()
    },
    enabled: !!activeLogsWh,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/webhooks`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, description: desc, events: selectedEvents }),
      })
      if (!r.ok) throw new Error('Failed to create webhook')
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dev-webhooks'] })
      setUrl(''); setDesc(''); setShowCreate(false)
    },
  })

  const toggleMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      await fetch(`${ENDPOINTS.gateway}/api/developer/webhooks/${id}`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active }),
      })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dev-webhooks'] }),
  })

  const testMutation = useMutation({
    mutationFn: async (id: number) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/webhooks/${id}/test`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: 'ping' }),
      })
      return r.json()
    },
    onSuccess: (data, id) => {
      setTestResult({
        id,
        success: data.success,
        msg: data.success ? `Ping delivered! Status ${data.log?.status_code || 200}` : `Ping failed: ${data.log?.error_message || 'Connection refused'}`,
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await fetch(`${ENDPOINTS.gateway}/api/developer/webhooks/${id}`, { method: 'DELETE', headers: authHeaders() })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dev-webhooks'] }),
  })

  if (!isAuth) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/50">
        <Webhook className="w-10 h-10 mx-auto mb-3 opacity-30 text-vit-400" />
        <p className="text-base font-semibold text-white">Authentication Required</p>
        <p className="text-sm text-white/40 mt-1">Please sign in to register and test webhook callback endpoints.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Developer Webhooks</h2>
          <p className="text-sm text-white/40">Receive real-time signed HTTP POST callbacks on event triggers.</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vit-400 hover:bg-vit-300 text-black font-semibold text-sm transition-colors">
          <Plus className="w-4 h-4" /> Register Webhook
        </button>
      </div>

      {showCreate && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-2xl border border-vit-400/30 bg-vit-400/5 space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Webhook className="w-4 h-4 text-vit-400" /> Register Webhook Endpoint
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-white/60 mb-1 block font-medium">Payload URL (HTTPS)</label>
              <input value={url} onChange={e => setUrl(e.target.value)} required placeholder="https://api.yourdomain.com/vit-webhook"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-vit-400/50" />
            </div>
            <div>
              <label className="text-xs text-white/60 mb-1 block font-medium">Description</label>
              <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="e.g. Settlement bot listener"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-vit-400/50" />
            </div>
            <div>
              <label className="text-xs text-white/60 mb-2 block font-medium">Subscribed Event Types</label>
              <div className="flex flex-wrap gap-2">
                {ALL_EVENTS.map(ev => {
                  const sel = selectedEvents.includes(ev.id)
                  return (
                    <button key={ev.id} type="button"
                      onClick={() => setSelectedEvents(sel ? selectedEvents.filter(x => x !== ev.id) : [...selectedEvents, ev.id])}
                      className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                        sel ? "bg-vit-400/10 text-vit-300 border-vit-400/30" : "bg-white/5 text-white/40 border-white/10")}>
                      {ev.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 text-sm">Cancel</button>
            <button onClick={() => createMutation.mutate()} disabled={!url || createMutation.isPending}
              className="px-5 py-2 rounded-xl bg-vit-400 hover:bg-vit-300 text-black font-semibold text-sm transition-colors disabled:opacity-50">
              {createMutation.isPending ? <Spinner className="w-4 h-4" /> : 'Register Endpoint'}
            </button>
          </div>
        </motion.div>
      )}

      {testResult && (
        <div className={cn("p-4 rounded-xl border flex items-center justify-between text-sm font-mono",
          testResult.success ? "bg-emerald-400/10 border-emerald-400/30 text-emerald-300" : "bg-red-400/10 border-red-400/30 text-red-300")}>
          <span>{testResult.msg}</span>
          <button onClick={() => setTestResult(null)} className="text-xs text-white/40 hover:text-white">Dismiss</button>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>
      ) : webhooks.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/40">
          <Webhook className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No webhooks registered yet. Register an endpoint to receive callbacks.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {webhooks.map(w => (
            <div key={w.id} className="p-5 rounded-2xl border border-white/10 bg-white/5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-white text-sm">{w.url}</span>
                    <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold uppercase border",
                      w.is_active ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/20" : "bg-white/10 text-white/40 border-white/10")}>
                      {w.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                  {w.description && <p className="text-xs text-white/50">{w.description}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => testMutation.mutate(w.id)} disabled={testMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-vit-400/10 hover:bg-vit-400/20 text-vit-300 border border-vit-400/20 text-xs font-semibold">
                    <Send className="w-3.5 h-3.5" /> Test Ping
                  </button>
                  <button onClick={() => setActiveLogsWh(activeLogsWh === w.id ? null : w.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-white/70 text-xs font-semibold">
                    <FileText className="w-3.5 h-3.5" /> Delivery Logs
                  </button>
                  <button onClick={() => toggleMutation.mutate({ id: w.id, is_active: !w.is_active })}
                    className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 text-xs">
                    {w.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button onClick={() => deleteMutation.mutate(w.id)} className="p-2 rounded-xl bg-red-400/10 text-red-400">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {w.secret && (
                <div className="flex items-center gap-2 p-2.5 rounded-xl bg-black/30 text-xs font-mono text-white/60">
                  <span className="text-white/40">Signing Secret:</span>
                  <span className="text-vit-300 truncate">{w.secret}</span>
                  <CopyBtn text={w.secret} label="Copy Secret" />
                </div>
              )}

              {/* Delivery logs drawer */}
              {activeLogsWh === w.id && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="pt-3 border-t border-white/10 space-y-2">
                  <p className="text-xs font-semibold text-white/80">Recent Delivery History</p>
                  {whLogs.length === 0 ? (
                    <p className="text-xs text-white/40">No deliveries recorded for this endpoint.</p>
                  ) : (
                    <div className="space-y-2 max-h-48 overflow-y-auto font-mono text-xs">
                      {whLogs.map(l => (
                        <div key={l.id} className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className={cn("px-1.5 py-0.5 rounded text-[10px] uppercase font-bold",
                              l.success ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400")}>
                              {l.success ? 'DELIVERED' : 'FAILED'}
                            </span>
                            <span className="text-white/80">{l.event_type}</span>
                            <span className="text-white/40">{l.latency_ms}ms</span>
                          </div>
                          <span className="text-white/30 text-[10px]">{new Date(l.delivered_at).toLocaleTimeString()}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tab 4: Interactive API Explorer & Docs ───────────────────────────────────

function ApiExplorerTab() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<DevEndpointDoc | null>(null)
  const [search, setSearch] = useState('')
  const [activeCodeLang, setActiveCodeLang] = useState<'curl' | 'js' | 'python' | 'go'>('curl')
  const [testResponse, setTestResponse] = useState<any>(null)
  const [testLoading, setTestLoading] = useState(false)

  const { data: docs } = useQuery<DevDocsResponse>({
    queryKey: ['dev-docs-explorer'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/docs`)
      if (!r.ok) throw new Error('Failed to load docs')
      return r.json()
    },
  })

  const endpoints = docs?.endpoints || []
  const filtered = endpoints.filter(e => e.path.toLowerCase().includes(search.toLowerCase()) || e.description.toLowerCase().includes(search.toLowerCase()))

  const activeEp = selectedEndpoint || filtered[0] || { method: 'GET', path: '/api/predictions/today', description: 'Fetch today certified predictions' }

  const generateSnippet = (ep: DevEndpointDoc, lang: string) => {
    const fullUrl = `${ENDPOINTS.gateway}${ep.path}`
    if (lang === 'curl') {
      return `curl -X ${ep.method} "${fullUrl}" \\
  -H "X-API-Key: vit_live_sk_..." \\
  -H "Content-Type: application/json"`
    }
    if (lang === 'js') {
      return `const res = await fetch('${fullUrl}', {
  method: '${ep.method}',
  headers: {
    'X-API-Key': 'vit_live_sk_...',
    'Content-Type': 'application/json'
  }
});
const data = await res.json();`
    }
    if (lang === 'python') {
      return `import httpx

res = httpx.${ep.method.toLowerCase()}("${fullUrl}", headers={
    "X-API-Key": "vit_live_sk_...",
    "Content-Type": "application/json"
})
data = res.json()`
    }
    return `package main

import (
    "net/http"
    "io"
)

func main() {
    req, _ := http.NewRequest("${ep.method}", "${fullUrl}", nil)
    req.Header.Set("X-API-Key", "vit_live_sk_...")
    resp, _ := http.DefaultClient.Do(req)
    defer resp.Body.Close()
}`
  }

  const runTestRequest = async () => {
    if (!activeEp) return
    setTestLoading(true)
    try {
      const fullUrl = `${ENDPOINTS.gateway}${activeEp.path}`
      const res = await fetch(fullUrl, {
        method: activeEp.method,
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      })
      const data = await res.json().catch(() => ({ status: res.status, text: res.statusText }))
      setTestResponse({ status: res.status, data })
    } catch (err: any) {
      setTestResponse({ error: err.message || 'Execution error' })
    } finally {
      setTestLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Endpoint List Sidebar */}
      <div className="lg:col-span-5 space-y-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-white/30" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search endpoints..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-vit-400/50" />
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 max-h-[600px] overflow-y-auto divide-y divide-white/5">
          {filtered.map(e => (
            <button key={`${e.method}-${e.path}`} onClick={() => { setSelectedEndpoint(e); setTestResponse(null) }}
              className={cn("w-full text-left p-3.5 flex items-center justify-between gap-3 hover:bg-white/5 transition-colors",
                activeEp.path === e.path && activeEp.method === e.method && "bg-vit-400/10 border-l-2 border-vit-400")}>
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-2">
                  <MethodBadge method={e.method} />
                  <span className="font-mono text-xs font-semibold text-white truncate">{e.path}</span>
                </div>
                <p className="text-xs text-white/40 truncate">{e.description || 'No description'}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-white/20 flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>

      {/* Endpoint Playground */}
      <div className="lg:col-span-7 space-y-6">
        <div className="p-6 rounded-2xl border border-white/10 bg-white/5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MethodBadge method={activeEp.method} />
              <h3 className="font-mono font-bold text-white text-base">{activeEp.path}</h3>
            </div>
            <button onClick={runTestRequest} disabled={testLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vit-400 hover:bg-vit-300 text-black font-semibold text-sm transition-colors disabled:opacity-50">
              {testLoading ? <Spinner className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />} Try It Out
            </button>
          </div>
          <p className="text-sm text-white/60">{activeEp.description || 'Execute directly against live backend gateway.'}</p>

          {/* Code Generator Tabs */}
          <div className="rounded-xl border border-white/10 bg-black/40 overflow-hidden">
            <div className="flex border-b border-white/10 bg-white/5">
              {(['curl', 'js', 'python', 'go'] as const).map(lang => (
                <button key={lang} onClick={() => setActiveCodeLang(lang)}
                  className={cn("px-4 py-2 text-xs font-mono font-medium uppercase transition-colors",
                    activeCodeLang === lang ? "text-vit-300 border-b-2 border-vit-400 bg-white/5" : "text-white/40 hover:text-white")}>
                  {lang}
                </button>
              ))}
              <div className="ml-auto p-1.5"><CopyBtn text={generateSnippet(activeEp, activeCodeLang)} /></div>
            </div>
            <pre className="p-4 text-xs font-mono text-emerald-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {generateSnippet(activeEp, activeCodeLang)}
            </pre>
          </div>

          {/* Live Response Box */}
          {testResponse && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-white/60">Response Payload</span>
                {testResponse.status && <StatusBadge code={testResponse.status} />}
              </div>
              <pre className="p-4 rounded-xl border border-white/10 bg-black/60 text-xs font-mono text-vit-300 max-h-80 overflow-y-auto">
                {JSON.stringify(testResponse.data || testResponse, null, 2)}
              </pre>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Tab 5: Plans & Pricing ───────────────────────────────────────────────────

function PlansTab() {
  const { data: plans = [] } = useQuery<DevPlan[]>({
    queryKey: ['dev-plans'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/plans`)
      if (!r.ok) return []
      return r.json()
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Developer API Plans</h2>
        <p className="text-sm text-white/40">Select rate limits and billing tiers for your integration applications.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {plans.map(p => (
          <div key={p.name} className="p-6 rounded-2xl border border-white/10 bg-white/5 flex flex-col justify-between space-y-4 hover:border-vit-400/30 transition-colors">
            <div className="space-y-2">
              <span className="text-xs font-mono uppercase text-vit-400 font-bold">{p.display_name}</span>
              <div className="text-2xl font-bold text-white font-mono">
                {p.price_vitcoin_per_1k === '0.00' ? 'Free' : `${p.price_vitcoin_per_1k} VIT`}
                <span className="text-xs text-white/40 font-normal"> / 1k calls</span>
              </div>
              <p className="text-xs text-white/50 leading-relaxed">{p.description}</p>
            </div>

            <div className="space-y-2 border-t border-white/10 pt-4 text-xs font-mono">
              <div className="flex justify-between text-white/60">
                <span>Rate Limit RPM:</span>
                <span className="text-white font-bold">{p.rate_limit_rpm.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-white/60">
                <span>Rate Limit RPD:</span>
                <span className="text-white font-bold">{p.rate_limit_rpd.toLocaleString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Tab 6: Admin Git Sync ──────────────────────────────────────────────────────

function AdminGitTab({ isAuth }: { isAuth: boolean }) {
  const qc = useQueryClient()
  const user = getStoredUser()

  const { data: gitStatus, isLoading } = useQuery<GitStatus>({
    queryKey: ['admin-git-status'],
    queryFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/git/status`, { headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load git status')
      return r.json()
    },
    enabled: isAuth && user?.role === 'admin',
  })

  const pullMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/git/pull`, { method: 'POST', headers: authHeaders() })
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-git-status'] }),
  })

  const pushMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/developer/git/push`, { method: 'POST', headers: authHeaders() })
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-git-status'] }),
  })

  if (!isAuth || user?.role !== 'admin') {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-white/50">
        <Shield className="w-10 h-10 mx-auto mb-3 opacity-30 text-vit-400" />
        <p className="text-base font-semibold text-white">Admin Privileges Required</p>
        <p className="text-sm text-white/40 mt-1">Git repository synchronization is restricted to super admins.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Repository Health & Git Sync</h2>
          <p className="text-sm text-white/40">Synchronize deployment origin state directly from the developer portal.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => pullMutation.mutate()} disabled={pullMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white font-semibold text-sm border border-white/10">
            {pullMutation.isPending ? <Spinner className="w-4 h-4" /> : <GitPullRequest className="w-4 h-4" />} Git Pull
          </button>
          <button onClick={() => pushMutation.mutate()} disabled={pushMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vit-400 hover:bg-vit-300 text-black font-semibold text-sm transition-colors">
            {pushMutation.isPending ? <Spinner className="w-4 h-4" /> : <GitCommit className="w-4 h-4" />} Stage & Push
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-sm">
          <div className="p-4 rounded-2xl border border-white/10 bg-white/5 space-y-1">
            <span className="text-xs text-white/40 flex items-center gap-1.5"><GitBranch className="w-3.5 h-3.5 text-vit-400" /> Current Branch</span>
            <p className="text-lg font-bold text-white">{gitStatus?.branch || 'main'}</p>
          </div>
          <div className="p-4 rounded-2xl border border-white/10 bg-white/5 space-y-1">
            <span className="text-xs text-white/40">Commits Ahead / Behind</span>
            <p className="text-lg font-bold text-vit-300">+{gitStatus?.commits_ahead ?? 0} / -{gitStatus?.commits_behind ?? 0}</p>
          </div>
          <div className="p-4 rounded-2xl border border-white/10 bg-white/5 space-y-1">
            <span className="text-xs text-white/40">Working Tree State</span>
            <p className={cn("text-lg font-bold", gitStatus?.is_clean ? "text-emerald-400" : "text-amber-400")}>
              {gitStatus?.is_clean ? 'Clean' : 'Modified Files'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Page Component ───────────────────────────────────────────────────────

export default function Developers() {
  const [activeTab, setActiveTab] = useState<'keys' | 'usage' | 'webhooks' | 'explorer' | 'plans' | 'admin_git'>('keys')
  const isAuth = !!getAuthToken()
  const user = getStoredUser()

  const tabs = [
    { id: 'keys', label: 'API Keys', icon: <Key className="w-4 h-4" /> },
    { id: 'usage', label: 'Usage & Metrics', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'webhooks', label: 'Webhooks', icon: <Webhook className="w-4 h-4" /> },
    { id: 'explorer', label: 'API Explorer & Docs', icon: <Terminal className="w-4 h-4" /> },
    { id: 'plans', label: 'Plans & Pricing', icon: <Layers className="w-4 h-4" /> },
    ...(user?.role === 'admin' ? [{ id: 'admin_git', label: 'Git Sync', icon: <GitBranch className="w-4 h-4" /> }] : []),
  ] as const

  return (
    <div className="min-h-screen bg-[#07090f] text-white pt-24 pb-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-8">

        {/* Hero Section */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          <div className="flex items-center gap-2 text-vit-400 font-semibold text-sm">
            <Code className="w-4 h-4" /> Developer Platform & SDK
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">Build on VIT Network</h1>
          <p className="text-white/50 max-w-2xl leading-relaxed">
            Direct real-data API access to AI prediction models, settlement webhooks, chain analytics, and storage infrastructure.
          </p>
        </motion.div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-white/10 overflow-x-auto gap-2">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id as any)}
              className={cn("flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all whitespace-nowrap",
                activeTab === t.id ? "border-vit-400 text-white bg-vit-400/5" : "border-transparent text-white/40 hover:text-white/80")}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Tab Contents */}
        <motion.div key={activeTab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
          {activeTab === 'keys' && <ApiKeysTab isAuth={isAuth} />}
          {activeTab === 'usage' && <UsageTab isAuth={isAuth} />}
          {activeTab === 'webhooks' && <WebhooksTab isAuth={isAuth} />}
          {activeTab === 'explorer' && <ApiExplorerTab />}
          {activeTab === 'plans' && <PlansTab />}
          {activeTab === 'admin_git' && <AdminGitTab isAuth={isAuth} />}
        </motion.div>

      </div>
    </div>
  )
}
