import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Upload, Download, Trash2, RefreshCw, Search, FileIcon, AlertCircle, CheckCircle2, Cloud, ShieldCheck } from 'lucide-react'
import { useStorageHealth } from '@/hooks/useHealth'
import { useStorageList, useStorageUpload, useStorageDelete } from '@/hooks/useStorage'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { formatBytes } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'

export default function Storage() {
  const { data: health, isLoading: healthLoading } = useStorageHealth()
  const { data: listData, isLoading: listLoading }  = useStorageList()
  const uploadMutation  = useStorageUpload()
  const deleteMutation  = useStorageDelete()
  const qc              = useQueryClient()
  const fileInputRef    = useRef<HTMLInputElement>(null)
  const [search, setSearch]       = useState('')
  const [uploadMsg, setUploadMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [deletingKey, setDeletingKey] = useState<string | null>(null)
  const [nodeAlias, setNodeAlias] = useState('My Google Drive')
  const [provider, setProvider] = useState('gdrive')
  const [gbContributed, setGbContributed] = useState('5')
  const [nodeSubmitting, setNodeSubmitting] = useState(false)
  const [nodeMessage, setNodeMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [nodeCredentials, setNodeCredentials] = useState({
    service_account_json: '',
    access_token: '',
    refresh_token: '',
    app_key: '',
    app_secret: '',
    client_id: '',
    client_secret: '',
    tenant_id: '',
    user_id: '',
  })
  const [nodeRows, setNodeRows] = useState<any[]>([])
  const [nodeSummary, setNodeSummary] = useState<any>(null)
  const [networkStats, setNetworkStats] = useState<any>(null)
  const [nodeLoading, setNodeLoading] = useState(false)

  const objects  = listData?.objects ?? []
  const filtered = objects.filter((o: any) =>
    o.key?.toLowerCase().includes(search.toLowerCase()),
  )

  async function loadNetworkStats() {
    try {
      const response = await fetch(`${ENDPOINTS.gateway}/api/tachyon/node/network-stats`)
      const body = response.ok ? await response.json().catch(() => ({})) : {}
      setNetworkStats(body)
    } catch {
      setNetworkStats(null)
    }
  }

  async function loadNodeData() {
    const token = getAuthToken()
    if (!token) {
      setNodeRows([])
      setNodeSummary(null)
      return
    }

    try {
      setNodeLoading(true)
      const [nodesRes, earningsRes] = await Promise.all([
        fetch(`${ENDPOINTS.gateway}/api/tachyon/node/my-nodes`, { headers: authHeaders() }),
        fetch(`${ENDPOINTS.gateway}/api/tachyon/node/earnings`, { headers: authHeaders() }),
      ])

      const nodesData = nodesRes.ok ? await nodesRes.json().catch(() => ({ nodes: [] })) : { nodes: [] }
      const earningsData = earningsRes.ok ? await earningsRes.json().catch(() => ({})) : {}
      setNodeRows(Array.isArray(nodesData?.nodes) ? nodesData.nodes : [])
      setNodeSummary(earningsData)
    } catch {
      setNodeRows([])
      setNodeSummary(null)
    } finally {
      setNodeLoading(false)
    }
  }

  useEffect(() => {
    void loadNetworkStats()
    void loadNodeData()
  }, [])

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health', 'storage'] })
    qc.invalidateQueries({ queryKey: ['storage'] })
    void loadNetworkStats()
    void loadNodeData()
  }

  function handleUploadClick() {
    setUploadMsg(null)
    fileInputRef.current?.click()
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    // Reset input so the same file can be re-uploaded if needed
    e.target.value = ''
    try {
      await uploadMutation.mutateAsync(file)
      setUploadMsg({ type: 'success', text: `"${file.name}" uploaded successfully.` })
    } catch (err: any) {
      setUploadMsg({ type: 'error', text: err?.message ?? 'Upload failed. Check the storage service.' })
    }
  }

  async function handleDelete(key: string) {
    if (!window.confirm(`Delete object "${key}"?`)) return
    setDeletingKey(key)
    try {
      await deleteMutation.mutateAsync(key)
    } catch {
      // silent — the list will simply not refresh; user can Refresh manually
    } finally {
      setDeletingKey(null)
    }
  }

  async function handleVerifyNode(nodeId: number) {
    try {
      const response = await fetch(`${ENDPOINTS.gateway}/api/tachyon/node/${nodeId}/verify`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail ?? 'Verification failed.')
      setNodeMessage({ type: 'success', text: `Verification complete: ${body.passed ? 'passed' : 'failed'}${body.tsc_awarded ? ` (+${body.tsc_awarded} TSC)` : ''}.` })
      await loadNodeData()
    } catch (error: any) {
      setNodeMessage({ type: 'error', text: error?.message ?? 'Unable to verify node.' })
    }
  }

  async function handleClaimNode(nodeId: number) {
    try {
      const response = await fetch(`${ENDPOINTS.gateway}/api/tachyon/node/${nodeId}/claim`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail ?? 'Claim failed.')
      setNodeMessage({ type: 'success', text: body.message ?? `Claimed ${body.claimed ?? 0} TSC.` })
      await loadNodeData()
    } catch (error: any) {
      setNodeMessage({ type: 'error', text: error?.message ?? 'Unable to claim rewards.' })
    }
  }

  async function handleDeleteNode(nodeId: number) {
    if (!window.confirm('Delete this storage node?')) return
    try {
      const response = await fetch(`${ENDPOINTS.gateway}/api/tachyon/node/${nodeId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail ?? 'Delete failed.')
      setNodeMessage({ type: 'success', text: `Node ${nodeId} removed successfully.` })
      await loadNodeData()
    } catch (error: any) {
      setNodeMessage({ type: 'error', text: error?.message ?? 'Unable to delete node.' })
    }
  }

  const isUploading = uploadMutation.isPending

  async function handleStorageNodeRegistration(event: React.FormEvent) {
    event.preventDefault()
    const token = getAuthToken()
    if (!token) {
      setNodeMessage({ type: 'error', text: 'Log in to register a storage node.' })
      return
    }

    const credentialPayload: Record<string, string> = {
      service_account_json: nodeCredentials.service_account_json,
      access_token: nodeCredentials.access_token,
      refresh_token: nodeCredentials.refresh_token,
      app_key: nodeCredentials.app_key,
      app_secret: nodeCredentials.app_secret,
      client_id: nodeCredentials.client_id,
      client_secret: nodeCredentials.client_secret,
      tenant_id: nodeCredentials.tenant_id,
      user_id: nodeCredentials.user_id,
    }

    const payload = {
      provider,
      alias: nodeAlias || 'My Storage Node',
      gb_contributed: Number(gbContributed || 5),
      credentials: credentialPayload,
    }

    try {
      setNodeSubmitting(true)
      setNodeMessage(null)
      const response = await fetch(`${ENDPOINTS.gateway}/api/tachyon/node/register`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail ?? 'Storage node registration failed.')
      setNodeMessage({ type: 'success', text: body.message ?? 'Storage node registered successfully.' })
      setNodeAlias('My Google Drive')
      setGbContributed('5')
      setNodeCredentials({
        service_account_json: '',
        access_token: '',
        refresh_token: '',
        app_key: '',
        app_secret: '',
        client_id: '',
        client_secret: '',
        tenant_id: '',
        user_id: '',
      })
      await loadNodeData()
    } catch (error: any) {
      setNodeMessage({ type: 'error', text: error?.message ?? 'Unable to register storage node.' })
    } finally {
      setNodeSubmitting(false)
    }
  }

  return (
    <div className="pt-24 pb-16">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-2 mb-2">
              <HardDrive className="w-5 h-5 text-vit-400" />
              <span className="text-sm text-vit-400 font-medium uppercase tracking-wider">Storage Service</span>
            </div>
            <h1 className="text-4xl font-bold text-white mb-2">vit-storage</h1>
            <p className="text-white/50 max-w-lg">
              Decentralized object storage. Data sourced directly from the vit-storage service.
            </p>
          </motion.div>
          <button
            onClick={refresh}
            disabled={healthLoading || listLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${(healthLoading || listLoading) ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            { label: 'Status',       value: health?.status ?? '—',                                           icon: HardDrive },
            { label: 'Objects',      value: health?.objectCount ?? listData?.total ?? objects.length ?? '—',  icon: FileIcon },
            { label: 'Used Storage', value: health?.used != null ? formatBytes(health.used) : '—',            icon: HardDrive },
            { label: 'Capacity',     value: health?.capacity != null ? formatBytes(health.capacity) : '—',    icon: HardDrive },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Upload feedback */}
        {uploadMsg && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex items-center gap-2 mb-6 px-4 py-3 rounded-lg border text-sm ${
              uploadMsg.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
          >
            {uploadMsg.type === 'success'
              ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
            {uploadMsg.text}
            <button onClick={() => setUploadMsg(null)} className="ml-auto text-xs opacity-60 hover:opacity-100">✕</button>
          </motion.div>
        )}

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="mb-8 rounded-xl border border-white/10 bg-surface-800/50 p-5"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Cloud className="w-4 h-4 text-vit-400" />
              <h2 className="text-lg font-semibold text-white">Connect a TACHYON storage node</h2>
            </div>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <form onSubmit={handleStorageNodeRegistration} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-sm text-white/70">
              Provider
              <select value={provider} onChange={e => setProvider(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none">
                <option value="gdrive">Google Drive</option>
                <option value="dropbox">Dropbox</option>
                <option value="onedrive">OneDrive</option>
              </select>
            </label>
            <label className="text-sm text-white/70">
              Alias
              <input value={nodeAlias} onChange={e => setNodeAlias(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" />
            </label>
            <label className="text-sm text-white/70">
              GB contributed
              <input type="number" min="1" max="2000" value={gbContributed} onChange={e => setGbContributed(e.target.value)} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" />
            </label>
            <div className="flex items-end">
              <button type="submit" disabled={nodeSubmitting} className="w-full rounded-lg bg-vit-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-vit-500 disabled:opacity-60">
                {nodeSubmitting ? 'Registering…' : 'Register Node'}
              </button>
            </div>
            {provider === 'gdrive' && (
              <>
                <label className="text-sm text-white/70 md:col-span-2 xl:col-span-4">
                  Google service account JSON
                  <textarea value={nodeCredentials.service_account_json} onChange={e => setNodeCredentials(current => ({ ...current, service_account_json: e.target.value }))} placeholder='{"type":"service_account", ...}' className="mt-1 min-h-28 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" />
                </label>
                <label className="text-sm text-white/70">
                  OAuth access token
                  <input value={nodeCredentials.access_token} onChange={e => setNodeCredentials(current => ({ ...current, access_token: e.target.value }))} placeholder='Optional OAuth access token' className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" />
                </label>
                <label className="text-sm text-white/70">
                  OAuth refresh token
                  <input value={nodeCredentials.refresh_token} onChange={e => setNodeCredentials(current => ({ ...current, refresh_token: e.target.value }))} placeholder='Optional OAuth refresh token' className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" />
                </label>
              </>
            )}
            {provider === 'dropbox' && (
              <>
                <label className="text-sm text-white/70"><span>Access token</span><input value={nodeCredentials.access_token} onChange={e => setNodeCredentials(current => ({ ...current, access_token: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
                <label className="text-sm text-white/70"><span>App key</span><input value={nodeCredentials.app_key} onChange={e => setNodeCredentials(current => ({ ...current, app_key: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
                <label className="text-sm text-white/70"><span>App secret</span><input value={nodeCredentials.app_secret} onChange={e => setNodeCredentials(current => ({ ...current, app_secret: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
                <label className="text-sm text-white/70"><span>Refresh token</span><input value={nodeCredentials.refresh_token} onChange={e => setNodeCredentials(current => ({ ...current, refresh_token: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
              </>
            )}
            {provider === 'onedrive' && (
              <>
                <label className="text-sm text-white/70"><span>Client ID</span><input value={nodeCredentials.client_id} onChange={e => setNodeCredentials(current => ({ ...current, client_id: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
                <label className="text-sm text-white/70"><span>Client secret</span><input value={nodeCredentials.client_secret} onChange={e => setNodeCredentials(current => ({ ...current, client_secret: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
                <label className="text-sm text-white/70"><span>Tenant ID</span><input value={nodeCredentials.tenant_id} onChange={e => setNodeCredentials(current => ({ ...current, tenant_id: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
                <label className="text-sm text-white/70"><span>User ID</span><input value={nodeCredentials.user_id} onChange={e => setNodeCredentials(current => ({ ...current, user_id: e.target.value }))} className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none" /></label>
              </>
            )}
          </form>
          {nodeMessage && (
            <div className={`mt-4 rounded-lg border px-3 py-2 text-sm ${nodeMessage.type === 'success' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-red-500/20 bg-red-500/10 text-red-300'}`}>
              {nodeMessage.text}
            </div>
          )}
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-8 rounded-xl border border-white/10 bg-surface-800/40 p-5"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">Tachyon swarm</h2>
              <p className="text-sm text-white/40">Global decentralised storage network health and contribution totals</p>
            </div>
            <button type="button" onClick={() => void loadNetworkStats()} className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:text-white">
              <RefreshCw className="w-4 h-4" />
              Sync
            </button>
          </div>

          <div className="mb-5 grid gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">Nodes</p>
              <p className="mt-2 text-2xl font-bold text-white">{networkStats?.total_nodes ?? 0}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">Active</p>
              <p className="mt-2 text-2xl font-bold text-emerald-300">{networkStats?.active_nodes ?? 0}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">GB</p>
              <p className="mt-2 text-2xl font-bold text-vit-300">{networkStats ? Number(networkStats.total_gb_contributed ?? 0).toFixed(1) : '0.0'}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">TSC</p>
              <p className="mt-2 text-2xl font-bold text-amber-300">{networkStats ? Number(networkStats.tsc_distributed_total ?? 0).toFixed(2) : '0.00'}</p>
            </div>
          </div>

          {networkStats?.provider_breakdown && Object.keys(networkStats.provider_breakdown).length > 0 && (
            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <p className="mb-3 text-xs uppercase tracking-wide text-white/40">Provider split</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(networkStats.provider_breakdown).map(([provider, count]: [string, any]) => (
                  <span key={provider} className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/70">
                    {provider}: {Number(count)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-8 rounded-xl border border-white/10 bg-surface-800/40 p-5"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">My Tachyon nodes</h2>
              <p className="text-sm text-white/40">Registered cloud storage capacity and live rewards</p>
            </div>
            <button type="button" onClick={() => void loadNodeData()} className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 hover:text-white">
              <RefreshCw className={`w-4 h-4 ${nodeLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          <div className="mb-5 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">Nodes</p>
              <p className="mt-2 text-2xl font-bold text-white">{nodeSummary?.active_nodes ?? nodeRows.length ?? 0}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">Pending TSC</p>
              <p className="mt-2 text-2xl font-bold text-amber-300">{nodeSummary ? Number(nodeSummary.total_tsc_pending ?? 0).toFixed(2) : '0.00'}</p>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-wide text-white/40">Earnings</p>
              <p className="mt-2 text-2xl font-bold text-emerald-300">{nodeSummary ? Number(nodeSummary.total_tsc_earned ?? 0).toFixed(2) : '0.00'}</p>
            </div>
          </div>

          {nodeLoading ? (
            <div className="flex justify-center py-8"><Spinner className="w-6 h-6 text-vit-400" /></div>
          ) : nodeRows.length === 0 ? (
            <div className="rounded-lg border border-dashed border-white/10 px-4 py-10 text-center text-sm text-white/40">
              No storage nodes registered yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-white/40">
                    <th className="pb-3 pr-4">Alias</th>
                    <th className="pb-3 pr-4">Provider</th>
                    <th className="pb-3 pr-4">GB</th>
                    <th className="pb-3 pr-4">Status</th>
                    <th className="pb-3 pr-4">TSC pending</th>
                    <th className="pb-3 pr-4">Reliability</th>
                  </tr>
                </thead>
                <tbody>
                  {nodeRows.map((node: any) => (
                    <tr key={node.id} className="border-b border-white/5 last:border-0 text-white/70">
                      <td className="py-3 pr-4">{node.alias}</td>
                      <td className="py-3 pr-4 capitalize">{node.provider_label ?? node.provider}</td>
                      <td className="py-3 pr-4">{Number(node.gb_contributed ?? 0).toFixed(1)}</td>
                      <td className="py-3 pr-4"><span className={`rounded-full border px-2 py-0.5 text-xs ${node.status === 'active' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/20 bg-amber-500/10 text-amber-300'}`}>{node.status}</span></td>
                      <td className="py-3 pr-4 text-amber-300">{Number(node.tsc_pending ?? 0).toFixed(2)}</td>
                      <td className="py-3 pr-4">{Number(node.reliability_score ?? 0).toFixed(2)}</td>
                      <td className="py-3 pr-4">
                        <div className="flex flex-wrap gap-2">
                          <button type="button" onClick={() => void handleVerifyNode(node.id)} className="rounded border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-white/80 hover:bg-white/10">Verify</button>
                          <button type="button" onClick={() => void handleClaimNode(node.id)} className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-300 hover:bg-emerald-500/20">Claim</button>
                          <button type="button" onClick={() => void handleDeleteNode(node.id)} className="rounded border border-red-500/20 bg-red-500/10 px-2 py-1 text-[11px] text-red-300 hover:bg-red-500/20">Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.section>

        {/* Object Browser */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6"
        >
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-white">Object Browser</h2>
              <StatusBadge status={health?.status} size="sm" pulse />
            </div>
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2">
                <Search className="w-4 h-4 text-white/40" />
                <input
                  type="text"
                  placeholder="Search objects…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="bg-transparent text-sm text-white placeholder-white/30 outline-none w-40"
                />
              </div>
              {/* Upload — triggers hidden file input */}
              <button
                onClick={handleUploadClick}
                disabled={isUploading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-vit-600 hover:bg-vit-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
              >
                {isUploading ? (
                  <><Spinner className="w-4 h-4" /> Uploading…</>
                ) : (
                  <><Upload className="w-4 h-4" /> Upload</>
                )}
              </button>
            </div>
          </div>

          {listLoading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-8 h-8" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16">
              <HardDrive className="w-10 h-10 text-white/20 mx-auto mb-3" />
              <p className="text-white/40 text-sm">
                {objects.length === 0
                  ? 'No objects found in vit-storage — the bucket may be empty.'
                  : 'No objects match your search.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Key</th>
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Size</th>
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Type</th>
                    <th className="text-left text-white/40 font-medium pb-3 pr-4">Modified</th>
                    <th className="text-right text-white/40 font-medium pb-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((obj: any) => (
                    <tr key={obj.key} className="border-b border-white/5 last:border-0 group">
                      <td className="py-3 pr-4 font-mono text-vit-300 text-xs truncate max-w-[200px]">{obj.key}</td>
                      <td className="py-3 pr-4 text-white/60">{formatBytes(obj.size ?? 0)}</td>
                      <td className="py-3 pr-4 text-white/40 text-xs">{obj.contentType ?? '—'}</td>
                      <td className="py-3 pr-4 text-white/40 text-xs">
                        {obj.lastModified ? new Date(obj.lastModified).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {obj.url && (
                            <a
                              href={obj.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 rounded hover:bg-white/10 text-white/50 hover:text-white transition-colors"
                              title="Download"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </a>
                          )}
                          <button
                            onClick={() => handleDelete(obj.key)}
                            disabled={deletingKey === obj.key}
                            className="p-1.5 rounded hover:bg-red-500/10 text-white/50 hover:text-red-400 disabled:opacity-40 transition-colors"
                            title="Delete"
                          >
                            {deletingKey === obj.key
                              ? <Spinner className="w-3.5 h-3.5" />
                              : <Trash2 className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
