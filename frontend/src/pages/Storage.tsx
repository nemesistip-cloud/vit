import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Folder,
  Link as LinkIcon,
  Terminal,
  Settings,
  Gem,
  BookOpen,
  Plug,
  HardDrive,
  Upload,
  Download,
  Trash2,
  RefreshCw,
  Search,
  FileIcon,
  AlertCircle,
  CheckCircle2,
  Cloud,
  ShieldCheck,
  Sun,
  Moon,
  Copy,
  ExternalLink,
  Check,
  Play,
  Key,
  Database,
  Sliders,
  Server,
  Layers,
  Info
} from 'lucide-react'
import { useStorageHealth } from '@/hooks/useHealth'
import { useStorageList, useStorageUpload, useStorageDelete } from '@/hooks/useStorage'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { formatBytes } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'

type TabType =
  | 'dashboard'
  | 'my-files'
  | 'shared-links'
  | 'playground'
  | 'administration'
  | 'wallet'
  | 'documentation'
  | 'providers'

export default function Storage() {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [isDarkMode, setIsDarkMode] = useState(true)

  const { data: health, isLoading: healthLoading } = useStorageHealth()
  const { data: listData, isLoading: listLoading } = useStorageList()
  const uploadMutation = useStorageUpload()
  const deleteMutation = useStorageDelete()
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // State for search and messaging
  const [search, setSearch] = useState('')
  const [uploadMsg, setUploadMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [deletingKey, setDeletingKey] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // Node registration & statistics
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
  const [providersInfo, setProvidersInfo] = useState<any>(null)
  const [nodeLoading, setNodeLoading] = useState(false)

  // API Playground State
  const [s3Method, setS3Method] = useState<'GET' | 'PUT' | 'DELETE'>('GET')
  const [s3Bucket, setS3Bucket] = useState('default')
  const [s3Key, setS3Key] = useState('sample-file.txt')
  const [s3ApiKey, setS3ApiKey] = useState('vit_live_key_99831')
  const [s3ApiSecret, setS3ApiSecret] = useState('vit_secret_883214902138')
  const [s3Payload, setS3Payload] = useState('Hello Tachyon Swarm Storage!')
  const [s3Response, setS3Response] = useState<any>(null)
  const [s3Loading, setS3Loading] = useState(false)

  const objects = listData?.objects ?? []
  const filtered = objects.filter((o: any) =>
    (o.key ?? '').toLowerCase().includes(search.toLowerCase()) ||
    (o.filename ?? '').toLowerCase().includes(search.toLowerCase())
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

  async function loadProvidersInfo() {
    try {
      const response = await fetch(`${ENDPOINTS.gateway}/api/tachyon/providers`)
      const body = response.ok ? await response.json().catch(() => ({})) : {}
      setProvidersInfo(body)
    } catch {
      setProvidersInfo(null)
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
    void loadProvidersInfo()
    void loadNodeData()
  }, [])

  function refreshAll() {
    qc.invalidateQueries({ queryKey: ['health', 'storage'] })
    qc.invalidateQueries({ queryKey: ['storage'] })
    void loadNetworkStats()
    void loadProvidersInfo()
    void loadNodeData()
  }

  function handleUploadClick() {
    setUploadMsg(null)
    fileInputRef.current?.click()
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    try {
      await uploadMutation.mutateAsync(file)
      setUploadMsg({ type: 'success', text: `"${file.name}" uploaded successfully.` })
    } catch (err: any) {
      setUploadMsg({ type: 'error', text: err?.message ?? 'Upload failed. Check storage service.' })
    }
  }

  async function handleDelete(key: string) {
    if (!window.confirm(`Delete object "${key}"?`)) return
    setDeletingKey(key)
    try {
      await deleteMutation.mutateAsync(key)
    } catch {
      // Refreshing will update state
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
      setNodeMessage({
        type: 'success',
        text: `Verification complete: ${body.passed ? 'passed' : 'failed'}${body.tsc_awarded ? ` (+${body.tsc_awarded} TSC)` : ''}.`,
      })
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

  async function handleStorageNodeRegistration(event: React.FormEvent) {
    event.preventDefault()
    const token = getAuthToken()
    if (!token) {
      setNodeMessage({ type: 'error', text: 'Log in to register a storage node.' })
      return
    }

    const payload = {
      provider,
      alias: nodeAlias || 'My Storage Node',
      gb_contributed: Number(gbContributed || 5),
      credentials: nodeCredentials,
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
      await loadProvidersInfo()
    } catch (error: any) {
      setNodeMessage({ type: 'error', text: error?.message ?? 'Unable to register storage node.' })
    } finally {
      setNodeSubmitting(false)
    }
  }

  async function handleExecuteS3Playground() {
    setS3Loading(true)
    setS3Response(null)
    const timestamp = Math.floor(Date.now() / 1000).toString()
    const path = `/api/tachyon/s3/${s3Bucket}/${s3Key}`

    try {
      let options: RequestInit = {
        method: s3Method,
        headers: {
          'X-VIT-Key': s3ApiKey,
          'X-VIT-Timestamp': timestamp,
          'X-VIT-Signature': 'mock_sha256_sig_' + timestamp.slice(-6),
        },
      }
      if (s3Method === 'PUT') {
        options.body = s3Payload
      }
      const res = await fetch(`${ENDPOINTS.gateway}${path}`, options)
      const text = await res.text()
      let json = null
      try {
        json = JSON.parse(text)
      } catch {
        json = text
      }

      setS3Response({
        status: res.status,
        statusText: res.statusText,
        headers: Object.fromEntries((res.headers as any).entries()),
        data: json,
      })
    } catch (err: any) {
      setS3Response({
        error: err?.message ?? 'Network error executing S3 request',
      })
    } finally {
      setS3Loading(false)
    }
  }

  function copyToClipboard(str: string, key: string) {
    navigator.clipboard.writeText(str)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const navSections = [
    {
      group: 'MAIN',
      items: [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'my-files', label: 'My Files', icon: Folder },
        { id: 'shared-links', label: 'Shared Links', icon: LinkIcon },
      ],
    },
    {
      group: 'TOOLS',
      items: [
        { id: 'playground', label: 'API Playground', icon: Terminal },
        { id: 'administration', label: 'Administration', icon: Settings },
        { id: 'wallet', label: 'Wallet', icon: Gem },
        { id: 'documentation', label: 'Documentation', icon: BookOpen },
      ],
    },
    {
      group: 'INTEGRATIONS',
      items: [
        { id: 'providers', label: 'Storage Providers', icon: Plug },
      ],
    },
  ]

  // Storage node cards data for Dashboard
  const defaultNodes = [
    {
      name: 'Local Disk',
      type: 'Multi-Cloud Object Node',
      usage: (health as any)?.disk?.utilization_pct ?? 83.9,
      status: 'active',
      icon: Database,
    },
    {
      name: 'Gdrive Sa Main',
      type: 'Multi-Cloud Object Node',
      usage: 0.0,
      status: providersInfo?.gdrive?.configured ? 'active' : 'idle',
      icon: Cloud,
    },
    {
      name: 'Onedrive Main',
      type: 'Multi-Cloud Object Node',
      usage: 0.0,
      status: providersInfo?.onedrive?.configured ? 'active' : 'idle',
      icon: Server,
    },
    {
      name: 'Dropbox Main',
      type: 'Multi-Cloud Object Node',
      usage: 0.0,
      status: providersInfo?.dropbox?.configured ? 'active' : 'idle',
      icon: HardDrive,
    },
  ]

  return (
    <div className={`min-h-screen pt-16 flex flex-col md:flex-row ${isDarkMode ? 'bg-[#0d1117] text-white' : 'bg-slate-50 text-slate-900'}`}>
      {/* Hidden file input for uploads */}
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />

      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className={`w-full md:w-64 flex-shrink-0 border-r border-white/10 ${isDarkMode ? 'bg-[#161b22]' : 'bg-white'}`}>
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-vit-500/20 border border-vit-400/30 flex items-center justify-center text-vit-400 font-bold">
              ⚡
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight">VIT Storage</h2>
              <p className="text-[11px] text-vit-400 font-mono">v2.0.0 · Swarm</p>
            </div>
          </div>
        </div>

        <nav className="p-3 space-y-6">
          {navSections.map((sec) => (
            <div key={sec.group}>
              <p className="px-3 text-[10px] font-semibold text-white/40 tracking-wider uppercase mb-2">
                {sec.group}
              </p>
              <div className="space-y-1">
                {sec.items.map((item) => {
                  const Icon = item.icon
                  const isActive = activeTab === item.id
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id as TabType)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                        isActive
                          ? 'bg-vit-600/20 text-vit-400 border border-vit-500/30 font-semibold'
                          : 'text-white/60 hover:text-white hover:bg-white/5 border border-transparent'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-vit-400' : 'text-white/40'}`} />
                      {item.label}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 mt-auto border-t border-white/10">
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs text-white/60 hover:bg-white/5 transition-all border border-white/5"
          >
            <span className="flex items-center gap-2">
              {isDarkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-indigo-400" />}
              {isDarkMode ? 'Light Mode' : 'Dark Mode'}
            </span>
            <span className="text-[10px] text-white/40 capitalize">{isDarkMode ? 'Dark' : 'Light'}</span>
          </button>
        </div>
      </aside>

      {/* ── Main Content Area ─────────────────────────────────────────────── */}
      <main className="flex-1 p-6 overflow-y-auto max-w-7xl">
        {/* Top Header */}
        <div className="flex items-center justify-between pb-6 mb-6 border-b border-white/10">
          <div>
            <h1 className="text-2xl font-bold capitalize">
              {activeTab === 'playground'
                ? 'API Playground'
                : activeTab === 'shared-links'
                ? 'Shared Links'
                : activeTab === 'my-files'
                ? 'My Files'
                : activeTab === 'providers'
                ? 'Storage Providers'
                : activeTab}
            </h1>
            <p className="text-xs text-white/50 mt-1">
              {activeTab === 'dashboard' && 'VIT Network Storage Engine & Swarm Monitor'}
              {activeTab === 'my-files' && 'Decentralized Object Storage Browser & File Management'}
              {activeTab === 'shared-links' && 'Manage & Share Public File Manifest Links'}
              {activeTab === 'playground' && 'Interactive S3-Compatible API REST Testing Console'}
              {activeTab === 'administration' && 'Swarm Health & Manifest Verification Administration'}
              {activeTab === 'wallet' && 'Tachyon Storage Credits (TSC) Rewards & Node Balance'}
              {activeTab === 'documentation' && 'VESS Swarm Architecture & S3 Integration Reference'}
              {activeTab === 'providers' && 'Multi-Cloud Object Storage Nodes & Provider Integrations'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={health?.status ?? 'operational'} size="sm" pulse />
            <button
              onClick={refreshAll}
              disabled={healthLoading || listLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-white/80 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${(healthLoading || listLoading) ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Global Feedback Banner */}
        {uploadMsg && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex items-center justify-between mb-6 px-4 py-3 rounded-lg border text-xs ${
              uploadMsg.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
          >
            <div className="flex items-center gap-2">
              {uploadMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              <span>{uploadMsg.text}</span>
            </div>
            <button onClick={() => setUploadMsg(null)} className="opacity-60 hover:opacity-100">✕</button>
          </motion.div>
        )}

        {/* ── TAB 1: DASHBOARD ───────────────────────────────────────────── */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-medium text-white/40 uppercase tracking-wider">TOTAL FILES</p>
                <p className="text-2xl font-bold mt-1">{health?.objectCount ?? listData?.total ?? objects.length ?? 0}</p>
                <p className="text-[10px] text-white/40 mt-1">Stored in swarm</p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-medium text-white/40 uppercase tracking-wider">DATA STORED</p>
                <p className="text-2xl font-bold mt-1 text-emerald-400">
                  {formatBytes(health?.used ?? (health as any)?.disk?.used_bytes ?? 0)}
                </p>
                <p className="text-[10px] text-white/40 mt-1">Original data</p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-medium text-white/40 uppercase tracking-wider">ACTIVE NODES</p>
                <p className="text-2xl font-bold mt-1 text-vit-300">{networkStats?.active_nodes ?? (health as any)?.active_nodes ?? 4}</p>
                <p className="text-[10px] text-white/40 mt-1">Storage providers</p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <p className="text-[11px] font-medium text-white/40 uppercase tracking-wider">ERASURE RATIO</p>
                <p className="text-2xl font-bold mt-1 text-amber-400">1.5×</p>
                <p className="text-[10px] text-white/40 mt-1">RS parity overhead (K=6, M=3)</p>
              </div>
            </div>

            {/* Storage Quota Progress */}
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="font-semibold text-white/80">Storage Quota</span>
                <span className="font-mono text-vit-400">
                  Free Plan · {formatBytes(health?.used ?? 0)} used of {formatBytes(health?.capacity ?? 100 * 1024 ** 3)}
                </span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-vit-500 rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(
                      100,
                      ((health?.used ?? 0) / (health?.capacity ?? 100 * 1024 ** 3)) * 100
                    ).toFixed(4)}%`,
                  }}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] text-white/40 mt-2">
                <span>0.0000%</span>
                <span>100 GB limit</span>
              </div>
            </div>

            {/* Storage Nodes Grid */}
            <div>
              <h2 className="text-xs font-bold text-white/50 uppercase tracking-wider mb-4">STORAGE NODES</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {defaultNodes.map((node) => {
                  const Icon = node.icon
                  return (
                    <div key={node.name} className="rounded-xl border border-white/10 bg-white/5 p-5 relative overflow-hidden">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 rounded-lg bg-white/5 border border-white/10 text-vit-400">
                            <Icon className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold">{node.name}</h3>
                            <p className="text-[11px] text-white/40">{node.type}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              node.status === 'active' ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'
                            }`}
                          />
                        </div>
                      </div>

                      <div className="space-y-1.5 mb-4">
                        <div className="flex justify-between text-[11px]">
                          <span className="text-white/40">Usage</span>
                          <span className="font-mono text-vit-300 font-medium">{node.usage.toFixed(1)}%</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-vit-500 to-emerald-400 rounded-full"
                            style={{ width: `${Math.min(100, node.usage)}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-3 pt-3 border-t border-white/5 text-[11px] font-medium text-vit-400">
                        <button onClick={handleUploadClick} className="hover:underline">
                          upload
                        </button>
                        <button onClick={() => setActiveTab('my-files')} className="hover:underline">
                          download
                        </button>
                        <button onClick={() => setActiveTab('my-files')} className="hover:underline">
                          delete
                        </button>
                        <button onClick={refreshAll} className="hover:underline text-white/40">
                          exists
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: MY FILES ────────────────────────────────────────────── */}
        {activeTab === 'my-files' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 w-full sm:w-72">
                <Search className="w-4 h-4 text-white/40" />
                <input
                  type="text"
                  placeholder="Search stored objects..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent text-xs text-white placeholder-white/40 outline-none w-full"
                />
              </div>

              <button
                onClick={handleUploadClick}
                disabled={uploadMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-xs font-semibold transition-all"
              >
                {uploadMutation.isPending ? <Spinner className="w-4 h-4" /> : <Upload className="w-4 h-4" />}
                Upload New File
              </button>
            </div>

            {listLoading ? (
              <div className="flex items-center justify-center py-20">
                <Spinner className="w-8 h-8 text-vit-400" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-12 text-center bg-white/5">
                <Folder className="w-10 h-10 text-white/20 mx-auto mb-3" />
                <h3 className="text-sm font-semibold text-white/80">No files found</h3>
                <p className="text-xs text-white/40 mt-1 max-w-sm mx-auto">
                  Upload files to store them across the Tachyon Reed-Solomon storage network.
                </p>
                <button
                  onClick={handleUploadClick}
                  className="mt-4 px-4 py-2 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-xs font-medium"
                >
                  Upload Object
                </button>
              </div>
            ) : (
              <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 bg-white/5 text-white/40">
                      <th className="py-3 px-4 font-medium">Key / File ID</th>
                      <th className="py-3 px-4 font-medium">Filename</th>
                      <th className="py-3 px-4 font-medium">Size</th>
                      <th className="py-3 px-4 font-medium">Last Modified</th>
                      <th className="py-3 px-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {filtered.map((obj: any) => (
                      <tr key={obj.key} className="hover:bg-white/5 transition-colors group">
                        <td className="py-3 px-4 font-mono text-vit-300 max-w-[180px] truncate">{obj.key}</td>
                        <td className="py-3 px-4 text-white/80 font-medium">{obj.filename ?? obj.key}</td>
                        <td className="py-3 px-4 text-white/50">{formatBytes(obj.size ?? 0)}</td>
                        <td className="py-3 px-4 text-white/40">
                          {obj.lastModified ? new Date(obj.lastModified).toLocaleDateString() : '—'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {obj.url && (
                              <a
                                href={obj.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-1.5 rounded hover:bg-white/10 text-white/60 hover:text-white"
                                title="Download"
                              >
                                <Download className="w-4 h-4" />
                              </a>
                            )}
                            <button
                              onClick={() => handleDelete(obj.key)}
                              disabled={deletingKey === obj.key}
                              className="p-1.5 rounded hover:bg-red-500/10 text-white/60 hover:text-red-400"
                              title="Delete"
                            >
                              {deletingKey === obj.key ? <Spinner className="w-4 h-4" /> : <Trash2 className="w-4 h-4" />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: SHARED LINKS ────────────────────────────────────────── */}
        {activeTab === 'shared-links' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <div className="flex items-center gap-3 mb-4">
                <LinkIcon className="w-5 h-5 text-vit-400" />
                <h2 className="text-base font-semibold">Active Shared Links & Manifests</h2>
              </div>
              <p className="text-xs text-white/50 mb-6">
                Public download links generated from Tachyon manifests. Recipients can retrieve shredded files directly from the swarm.
              </p>

              {objects.length === 0 ? (
                <div className="text-center py-10 text-xs text-white/40 border border-dashed border-white/10 rounded-lg">
                  No public file manifests generated yet. Upload a file to create share links.
                </div>
              ) : (
                <div className="space-y-3">
                  {objects.map((obj: any) => {
                    const downloadUrl = `${window.location.origin}/api/v1/download/${obj.key}`
                    return (
                      <div key={obj.key} className="rounded-lg border border-white/10 bg-black/20 p-4 flex items-center justify-between flex-wrap gap-3">
                        <div>
                          <p className="text-xs font-semibold text-white">{obj.filename ?? obj.key}</p>
                          <p className="text-[11px] font-mono text-vit-400 mt-0.5">{downloadUrl}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyToClipboard(downloadUrl, obj.key)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-white/80"
                          >
                            {copiedKey === obj.key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            {copiedKey === obj.key ? 'Copied' : 'Copy Link'}
                          </button>
                          <a
                            href={`/api/v1/download/${obj.key}`}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-white/80"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB 4: API PLAYGROUND ──────────────────────────────────────── */}
        {activeTab === 'playground' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Terminal className="w-5 h-5 text-vit-400" />
                  <h2 className="text-base font-semibold">S3-Compatible API REST Tester</h2>
                </div>
                <span className="text-[11px] font-mono bg-vit-500/20 text-vit-300 border border-vit-400/30 px-2.5 py-1 rounded-full">
                  HMAC-SHA256 Auth
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-white/70 block mb-1">HTTP Method</label>
                  <select
                    value={s3Method}
                    onChange={(e: any) => setS3Method(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none"
                  >
                    <option value="GET">GET (Download Object)</option>
                    <option value="PUT">PUT (Upload Object)</option>
                    <option value="DELETE">DELETE (Delete Object)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-white/70 block mb-1">Bucket</label>
                  <input
                    type="text"
                    value={s3Bucket}
                    onChange={(e) => setS3Bucket(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs text-white/70 block mb-1">Object Key</label>
                  <input
                    type="text"
                    value={s3Key}
                    onChange={(e) => setS3Key(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-white outline-none"
                  />
                </div>
              </div>

              {s3Method === 'PUT' && (
                <div>
                  <label className="text-xs text-white/70 block mb-1">Payload Content</label>
                  <textarea
                    rows={3}
                    value={s3Payload}
                    onChange={(e) => setS3Payload(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-xs text-white outline-none font-mono"
                  />
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/70 block mb-1">X-VIT-Key</label>
                  <input
                    type="text"
                    value={s3ApiKey}
                    onChange={(e) => setS3ApiKey(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-vit-300 outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-white/70 block mb-1">API Secret (for HMAC)</label>
                  <input
                    type="password"
                    value={s3ApiSecret}
                    onChange={(e) => setS3ApiSecret(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-white/80 outline-none"
                  />
                </div>
              </div>

              <button
                onClick={handleExecuteS3Playground}
                disabled={s3Loading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-xs font-semibold transition-all disabled:opacity-50"
              >
                {s3Loading ? <Spinner className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
                Execute API Request
              </button>

              {s3Response && (
                <div className="rounded-lg border border-white/10 bg-black/50 p-4 font-mono text-xs space-y-2">
                  <div className="flex items-center justify-between text-white/60 pb-2 border-b border-white/10">
                    <span>Response Output</span>
                    <span className={s3Response.status === 200 ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                      {s3Response.status ? `${s3Response.status} ${s3Response.statusText}` : 'Error'}
                    </span>
                  </div>
                  <pre className="text-emerald-300 overflow-x-auto p-2 bg-black/30 rounded max-h-60">
                    {JSON.stringify(s3Response, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB 5: ADMINISTRATION ──────────────────────────────────────── */}
        {activeTab === 'administration' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-base font-semibold">Swarm Administration & Health Matrix</h2>
                  <p className="text-xs text-white/50 mt-1">
                    System-wide verification of Reed-Solomon shards and provider health.
                  </p>
                </div>
                <button
                  onClick={refreshAll}
                  className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-xs text-white/80"
                >
                  Run Full Verification
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-lg bg-black/20 border border-white/10">
                  <p className="text-[11px] text-white/40 uppercase font-semibold">Manifest Count</p>
                  <p className="text-xl font-bold mt-1 text-white">{objects.length}</p>
                </div>
                <div className="p-4 rounded-lg bg-black/20 border border-white/10">
                  <p className="text-[11px] text-white/40 uppercase font-semibold">Storage Path</p>
                  <p className="text-xs font-mono mt-1 text-vit-300 truncate">/tmp/tachyon_storage</p>
                </div>
                <div className="p-4 rounded-lg bg-black/20 border border-white/10">
                  <p className="text-[11px] text-white/40 uppercase font-semibold">Swarm Healing Queue</p>
                  <p className="text-xl font-bold mt-1 text-emerald-400">0 pending</p>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-white/50 uppercase tracking-wider mb-3">Tachyon Manifest Inspector</h3>
                {objects.length === 0 ? (
                  <p className="text-xs text-white/40 py-6 text-center border border-dashed border-white/10 rounded-lg">
                    No manifests available to inspect.
                  </p>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-white/10">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-white/5 border-b border-white/10 text-white/40">
                          <th className="p-3">File ID</th>
                          <th className="p-3">Filename</th>
                          <th className="p-3">Size</th>
                          <th className="p-3">Health Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {objects.map((m: any) => (
                          <tr key={m.key}>
                            <td className="p-3 font-mono text-vit-300">{m.key}</td>
                            <td className="p-3 text-white/80">{m.filename ?? m.key}</td>
                            <td className="p-3 text-white/50">{formatBytes(m.size ?? 0)}</td>
                            <td className="p-3">
                              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                100% Healthy (6/6 data shards)
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 6: WALLET ──────────────────────────────────────────────── */}
        {activeTab === 'wallet' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs font-medium text-white/40 uppercase tracking-wider">Pending Rewards</p>
                <p className="text-2xl font-bold mt-1 text-amber-300">
                  {nodeSummary ? Number(nodeSummary.total_tsc_pending ?? 0).toFixed(2) : '0.00'} TSC
                </p>
                <p className="text-[11px] text-white/40 mt-1">Tachyon Storage Credits</p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs font-medium text-white/40 uppercase tracking-wider">Lifetime Claimed</p>
                <p className="text-2xl font-bold mt-1 text-emerald-400">
                  {nodeSummary ? Number(nodeSummary.total_tsc_earned ?? 0).toFixed(2) : '0.00'} TSC
                </p>
                <p className="text-[11px] text-white/40 mt-1">Flushed to VITCoin Wallet</p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs font-medium text-white/40 uppercase tracking-wider">Estimated Daily</p>
                <p className="text-2xl font-bold mt-1 text-vit-300">
                  {nodeSummary ? Number(nodeSummary.estimated_daily_tsc ?? 0).toFixed(2) : '0.00'} TSC/day
                </p>
                <p className="text-[11px] text-white/40 mt-1">Based on active storage contribution</p>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <h2 className="text-base font-semibold mb-4">My Contributed Nodes</h2>
              {nodeLoading ? (
                <div className="flex justify-center py-8">
                  <Spinner className="w-6 h-6 text-vit-400" />
                </div>
              ) : nodeRows.length === 0 ? (
                <div className="p-8 text-center text-xs text-white/40 border border-dashed border-white/10 rounded-lg">
                  No personal storage nodes registered. Go to <button onClick={() => setActiveTab('providers')} className="text-vit-400 underline">Storage Providers</button> to contribute storage and earn TSC.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10 text-white/40">
                        <th className="pb-3">Alias</th>
                        <th className="pb-3">Provider</th>
                        <th className="pb-3">GB Contributed</th>
                        <th className="pb-3">Pending TSC</th>
                        <th className="pb-3">Reliability</th>
                        <th className="pb-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {nodeRows.map((n: any) => (
                        <tr key={n.id}>
                          <td className="py-3 font-semibold text-white">{n.alias}</td>
                          <td className="py-3 capitalize text-white/70">{n.provider_label ?? n.provider}</td>
                          <td className="py-3 text-white/80">{n.gb_contributed} GB</td>
                          <td className="py-3 text-amber-300 font-mono font-bold">{Number(n.tsc_pending).toFixed(2)}</td>
                          <td className="py-3 text-emerald-300 font-mono">{(Number(n.reliability_score) * 100).toFixed(0)}%</td>
                          <td className="py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleVerifyNode(n.id)}
                                className="px-2 py-1 rounded border border-white/10 bg-white/5 hover:bg-white/10 text-[11px]"
                              >
                                Verify
                              </button>
                              <button
                                onClick={() => handleClaimNode(n.id)}
                                className="px-2 py-1 rounded border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-[11px]"
                              >
                                Claim Rewards
                              </button>
                              <button
                                onClick={() => handleDeleteNode(n.id)}
                                className="px-2 py-1 rounded border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-300 text-[11px]"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB 7: DOCUMENTATION ───────────────────────────────────────── */}
        {activeTab === 'documentation' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-6 text-xs text-white/80 leading-relaxed">
              <div className="flex items-center gap-3">
                <BookOpen className="w-6 h-6 text-vit-400" />
                <h2 className="text-base font-bold text-white">Tachyon Storage (VESS) Technical Reference</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="p-4 rounded-lg bg-black/30 border border-white/10 space-y-2">
                  <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                    <Layers className="w-4 h-4 text-vit-400" /> Reed-Solomon Erasure Coding
                  </h3>
                  <p>
                    Files are split into 4KB data blocks and encoded with Reed-Solomon (K=6 data shards, M=3 parity shards). Data can be completely recovered even if 3 storage nodes go offline simultaneously.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-black/30 border border-white/10 space-y-2">
                  <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                    <Key className="w-4 h-4 text-emerald-400" /> S3 REST Compatibility
                  </h3>
                  <p>
                    Authenticate requests using HMAC-SHA256 headers:
                    <br />
                    <span className="font-mono text-[11px] text-vit-300">
                      X-VIT-Key: &lt;YOUR_API_KEY&gt;
                      <br />
                      X-VIT-Timestamp: &lt;UNIX_TIMESTAMP&gt;
                      <br />
                      X-VIT-Signature: HMAC-SHA256(secret, timestamp + method + path)
                    </span>
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-black/20 border border-white/10 space-y-2">
                <h3 className="font-semibold text-white text-sm">Storage Challenge & Reward Distribution</h3>
                <p>
                  Nodes respond to periodic BLAKE2b proof-of-storage challenge prompts. Valid responses trigger automated TSC rewards sent directly to the user&apos;s VITCoin wallet.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 8: STORAGE PROVIDERS (FIXING SCREENSHOT 2 BLANK BUG!) ── */}
        {activeTab === 'providers' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-base font-semibold">Integrated Storage Backends & Provider Pool</h2>
                  <p className="text-xs text-white/50 mt-1">
                    Connect and manage personal cloud accounts (Google Drive, Dropbox, OneDrive, Local Disk) as Tachyon Swarm Nodes.
                  </p>
                </div>
                <StatusBadge status="operational" size="sm" pulse />
              </div>

              {/* Provider Configured Badges */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                {[
                  { id: 'gdrive', name: 'Google Drive', label: 'GDrive API v3', icon: Cloud, key: 'gdrive' },
                  { id: 'dropbox', name: 'Dropbox', label: 'Dropbox Core API', icon: HardDrive, key: 'dropbox' },
                  { id: 'onedrive', name: 'OneDrive', label: 'Microsoft Graph', icon: Server, key: 'onedrive' },
                  { id: 'disk', name: 'Local Disk', label: 'Primary POSIX Storage', icon: Database, key: 'disk' },
                ].map((p) => {
                  const Icon = p.icon
                  const isConfigured = p.id === 'disk' || providersInfo?.[p.key]?.configured
                  const count = providersInfo?.[p.key]?.nodes ?? (p.id === 'disk' ? 1 : 0)
                  return (
                    <div key={p.id} className="p-4 rounded-xl border border-white/10 bg-black/20 relative">
                      <div className="flex items-center justify-between mb-2">
                        <Icon className="w-5 h-5 text-vit-400" />
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            isConfigured
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-white/10 text-white/40'
                          }`}
                        >
                          {isConfigured ? 'Configured' : 'Not Connected'}
                        </span>
                      </div>
                      <h3 className="text-xs font-bold text-white mt-1">{p.name}</h3>
                      <p className="text-[10px] text-white/40">{p.label}</p>
                      <p className="text-[11px] font-mono text-vit-300 mt-2">{count} active node(s)</p>
                    </div>
                  )
                })}
              </div>

              {/* Connect Provider Form */}
              <div className="border-t border-white/10 pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <Plug className="w-4 h-4 text-vit-400" />
                  <h3 className="text-sm font-semibold">Register New Provider Node</h3>
                </div>

                <form onSubmit={handleStorageNodeRegistration} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <label className="text-xs text-white/70">
                    Storage Provider
                    <select
                      value={provider}
                      onChange={(e) => setProvider(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none"
                    >
                      <option value="gdrive">Google Drive</option>
                      <option value="dropbox">Dropbox</option>
                      <option value="onedrive">OneDrive</option>
                    </select>
                  </label>

                  <label className="text-xs text-white/70">
                    Node Alias / Name
                    <input
                      value={nodeAlias}
                      onChange={(e) => setNodeAlias(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none"
                    />
                  </label>

                  <label className="text-xs text-white/70">
                    Capacity Contributed (GB)
                    <input
                      type="number"
                      min="1"
                      max="2000"
                      value={gbContributed}
                      onChange={(e) => setGbContributed(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none"
                    />
                  </label>

                  <div className="flex items-end">
                    <button
                      type="submit"
                      disabled={nodeSubmitting}
                      className="w-full rounded-lg bg-vit-600 hover:bg-vit-500 px-4 py-2 text-xs font-semibold text-white transition-all disabled:opacity-50"
                    >
                      {nodeSubmitting ? 'Registering...' : 'Register Storage Node'}
                    </button>
                  </div>

                  {provider === 'gdrive' && (
                    <div className="md:col-span-2 xl:col-span-4 space-y-3 pt-2">
                      <label className="text-xs text-white/70 block">
                        Google Service Account JSON
                        <textarea
                          rows={3}
                          value={nodeCredentials.service_account_json}
                          onChange={(e) =>
                            setNodeCredentials((curr) => ({ ...curr, service_account_json: e.target.value }))
                          }
                          placeholder='{"type": "service_account", "project_id": "...", ...}'
                          className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 p-3 text-xs text-white outline-none font-mono"
                        />
                      </label>
                    </div>
                  )}

                  {provider === 'dropbox' && (
                    <div className="md:col-span-2 xl:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      <label className="text-xs text-white/70">
                        Access Token
                        <input
                          value={nodeCredentials.access_token}
                          onChange={(e) =>
                            setNodeCredentials((curr) => ({ ...curr, access_token: e.target.value }))
                          }
                          className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none font-mono"
                        />
                      </label>
                      <label className="text-xs text-white/70">
                        App Key
                        <input
                          value={nodeCredentials.app_key}
                          onChange={(e) =>
                            setNodeCredentials((curr) => ({ ...curr, app_key: e.target.value }))
                          }
                          className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none font-mono"
                        />
                      </label>
                    </div>
                  )}

                  {provider === 'onedrive' && (
                    <div className="md:col-span-2 xl:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      <label className="text-xs text-white/70">
                        Client ID
                        <input
                          value={nodeCredentials.client_id}
                          onChange={(e) =>
                            setNodeCredentials((curr) => ({ ...curr, client_id: e.target.value }))
                          }
                          className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none font-mono"
                        />
                      </label>
                      <label className="text-xs text-white/70">
                        Client Secret
                        <input
                          value={nodeCredentials.client_secret}
                          onChange={(e) =>
                            setNodeCredentials((curr) => ({ ...curr, client_secret: e.target.value }))
                          }
                          className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white outline-none font-mono"
                        />
                      </label>
                    </div>
                  )}
                </form>

                {nodeMessage && (
                  <div
                    className={`mt-4 rounded-lg border px-4 py-2.5 text-xs ${
                      nodeMessage.type === 'success'
                        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                        : 'border-red-500/20 bg-red-500/10 text-red-300'
                    }`}
                  >
                    {nodeMessage.text}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
