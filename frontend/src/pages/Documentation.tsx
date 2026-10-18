import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BookOpen, Search, Copy, CheckCheck, ExternalLink, Shield, Server,
  Code, Play, Layers, FileText, Database, ChevronRight, ChevronDown,
  Sun, Moon, RefreshCw, Cpu, Activity, Key, Terminal, ArrowUpRight,
  Filter, CheckCircle2, AlertTriangle, Zap, HardDrive, Lock, UserCheck,
  Workflow
} from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  OpenAPISpec, ParsedEndpoint, ParsedGroup, OpenAPIMetrics,
  parseOpenAPISpec, generateMockFromSchema, generateCodeExamples, resolveSchemaRef
} from '@/lib/openapi'

// ── Default / Fallback Server Config ─────────────────────────────────────────

const DEFAULT_BASE_URL = ENDPOINTS.gateway || 'https://api.vitchain.network'

// ── Method Badge Colors ───────────────────────────────────────────────────────

const METHOD_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  get:    { bg: 'bg-emerald-500/10 dark:bg-emerald-500/15', text: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-500/30' },
  post:   { bg: 'bg-blue-500/10 dark:bg-blue-500/15', text: 'text-blue-600 dark:text-blue-400', border: 'border-blue-500/30' },
  put:    { bg: 'bg-amber-500/10 dark:bg-amber-500/15', text: 'text-amber-600 dark:text-amber-400', border: 'border-amber-500/30' },
  patch:  { bg: 'bg-purple-500/10 dark:bg-purple-500/15', text: 'text-purple-600 dark:text-purple-400', border: 'border-purple-500/30' },
  delete: { bg: 'bg-rose-500/10 dark:bg-rose-500/15', text: 'text-rose-600 dark:text-rose-400', border: 'border-rose-500/30' },
}

export default function Documentation() {
  // Theme state
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('vit_doc_theme') as 'dark' | 'light') || 'dark'
  })

  // OpenAPI spec state
  const [spec, setSpec] = useState<OpenAPISpec | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Configuration state
  const [baseUrl, setBaseUrl] = useState<string>(() => {
    return localStorage.getItem('vit_doc_base_url') || DEFAULT_BASE_URL
  })
  const [apiKey, setApiKey] = useState<string>(() => {
    return localStorage.getItem('vit_doc_api_key') || ''
  })

  // Search & Navigation
  const [searchQuery, setSearchQuery] = useState('')
  const [schemaSearch, setSchemaSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'api' | 'tachyon' | 'auth' | 'schemas'>('overview')
  const [selectedEndpointId, setSelectedEndpointId] = useState<string | null>(null)
  const [selectedSchemaName, setSelectedSchemaName] = useState<string | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({})

  // Interactive Runner State
  const [runnerParams, setRunnerParams] = useState<Record<string, string>>({})
  const [runnerHeaders, setRunnerHeaders] = useState<Record<string, string>>({})
  const [runnerBody, setRunnerBody] = useState<string>('')
  const [runnerActiveLang, setRunnerActiveLang] = useState<'curl' | 'js' | 'python'>('curl')
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<{
    status?: number
    statusText?: string
    durationMs?: number
    headers?: Record<string, string>
    data?: any
    error?: string
  } | null>(null)

  // Copy Feedback
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const handleCopy = (key: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  // Persist Theme & Config
  useEffect(() => {
    localStorage.setItem('vit_doc_theme', theme)
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  useEffect(() => {
    localStorage.setItem('vit_doc_base_url', baseUrl)
  }, [baseUrl])

  useEffect(() => {
    localStorage.setItem('vit_doc_api_key', apiKey)
  }, [apiKey])

  // Fetch OpenAPI Spec
  useEffect(() => {
    let isMounted = true
    async function loadSpec() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch('/openapi.json')
        if (!res.ok) throw new Error(`Failed to load OpenAPI spec: ${res.statusText}`)
        const data: OpenAPISpec = await res.json()
        if (isMounted) {
          setSpec(data)
          // Set initial expanded groups
          const parsed = parseOpenAPISpec(data)
          const initialExpanded: Record<string, boolean> = {}
          parsed.groups.slice(0, 5).forEach(g => {
            initialExpanded[g.name] = true
          })
          setExpandedGroups(initialExpanded)
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Error fetching specification')
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    loadSpec()
    return () => { isMounted = false }
  }, [])

  // Parsed Spec Memo
  const parsedSpec = useMemo(() => {
    if (!spec) return null
    return parseOpenAPISpec(spec)
  }, [spec])

  // Filtered Endpoints / Groups
  const filteredGroups = useMemo(() => {
    if (!parsedSpec) return []
    if (!searchQuery.trim()) return parsedSpec.groups

    const q = searchQuery.toLowerCase().trim()
    return parsedSpec.groups
      .map(group => {
        const matchingEndpoints = group.endpoints.filter(
          ep =>
            ep.path.toLowerCase().includes(q) ||
            ep.summary.toLowerCase().includes(q) ||
            ep.description.toLowerCase().includes(q) ||
            ep.method.toLowerCase().includes(q) ||
            ep.operationId.toLowerCase().includes(q)
        )
        return {
          ...group,
          endpoints: matchingEndpoints
        }
      })
      .filter(group => group.endpoints.length > 0)
  }, [parsedSpec, searchQuery])

  // Currently Selected Endpoint
  const selectedEndpoint = useMemo(() => {
    if (!parsedSpec || !selectedEndpointId) return null
    return parsedSpec.endpoints.find(ep => ep.id === selectedEndpointId) || null
  }, [parsedSpec, selectedEndpointId])

  // Synchronize Runner Input when selected endpoint changes
  useEffect(() => {
    if (!selectedEndpoint) return

    const initialParams: Record<string, string> = {}
    selectedEndpoint.parameters.forEach(p => {
      if (p.example !== undefined) initialParams[p.name] = String(p.example)
      else if (p.in === 'path') initialParams[p.name] = '1'
      else initialParams[p.name] = ''
    })
    setRunnerParams(initialParams)

    const initialHeaders: Record<string, string> = {}
    if (apiKey) {
      initialHeaders['X-API-Key'] = apiKey
      initialHeaders['Authorization'] = `Bearer ${apiKey}`
    }
    setRunnerHeaders(initialHeaders)

    if (selectedEndpoint.requestBody) {
      const mock = selectedEndpoint.requestBody.example || (
        selectedEndpoint.requestBody.schema
          ? generateMockFromSchema(selectedEndpoint.requestBody.schema, spec || undefined)
          : {}
      )
      setRunnerBody(typeof mock === 'string' ? mock : JSON.stringify(mock, null, 2))
    } else {
      setRunnerBody('')
    }

    setExecutionResult(null)
  }, [selectedEndpoint, apiKey, spec])

  // Execute Interactive API Request
  const handleExecuteRequest = async () => {
    if (!selectedEndpoint) return
    setIsExecuting(true)
    setExecutionResult(null)

    const startTime = performance.now()
    try {
      let fullPath = selectedEndpoint.path
      selectedEndpoint.parameters.filter(p => p.in === 'path').forEach(p => {
        const val = runnerParams[p.name] || `{${p.name}}`
        fullPath = fullPath.replace(`{${p.name}}`, val)
      })

      const queryParams = selectedEndpoint.parameters
        .filter(p => p.in === 'query' && runnerParams[p.name])
        .map(p => `${encodeURIComponent(p.name)}=${encodeURIComponent(runnerParams[p.name])}`)
        .join('&')

      const targetUrl = `${baseUrl.replace(/\/$/, '')}${fullPath}${queryParams ? `?${queryParams}` : ''}`

      const headersToSend: Record<string, string> = {
        'Accept': 'application/json',
        ...runnerHeaders
      }

      const options: RequestInit = {
        method: selectedEndpoint.method.toUpperCase(),
        headers: headersToSend,
      }

      if (['post', 'put', 'patch'].includes(selectedEndpoint.method) && runnerBody.trim()) {
        headersToSend['Content-Type'] = selectedEndpoint.requestBody?.mediaType || 'application/json'
        options.body = runnerBody
      }

      const response = await fetch(targetUrl, options)
      const durationMs = Math.round(performance.now() - startTime)

      const respHeaders: Record<string, string> = {}
      response.headers.forEach((val, key) => {
        respHeaders[key] = val
      })

      let responseData: any = null
      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        responseData = await response.json()
      } else {
        responseData = await response.text()
      }

      setExecutionResult({
        status: response.status,
        statusText: response.statusText,
        durationMs,
        headers: respHeaders,
        data: responseData
      })
    } catch (err: any) {
      const durationMs = Math.round(performance.now() - startTime)
      setExecutionResult({
        durationMs,
        error: err.message || 'Network request failed. Please check CORS configuration or server availability.'
      })
    } finally {
      setIsExecuting(false)
    }
  }

  // Schema List & Filtering
  const schemasList = useMemo(() => {
    if (!spec?.components?.schemas) return []
    const all = Object.entries(spec.components.schemas).map(([name, schema]) => ({
      name,
      schema
    }))
    if (!schemaSearch.trim()) return all
    const q = schemaSearch.toLowerCase().trim()
    return all.filter(s => s.name.toLowerCase().includes(q))
  }, [spec, schemaSearch])

  // Tachyon Filtered Endpoints
  const tachyonEndpoints = useMemo(() => {
    if (!parsedSpec) return []
    return parsedSpec.endpoints.filter(ep => ep.path.includes('/tachyon'))
  }, [parsedSpec])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
        <RefreshCw className="w-8 h-8 text-vit-400 animate-spin mb-4" />
        <p className="text-sm text-slate-400 font-medium">Loading VIT Network OpenAPI 3.1 Specification...</p>
      </div>
    )
  }

  if (error || !spec || !parsedSpec) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-rose-400 mb-4" />
        <h2 className="text-xl font-bold mb-2">Failed to Load API Documentation</h2>
        <p className="text-sm text-slate-400 max-w-md mb-6">{error || 'An unexpected error occurred while parsing the specification.'}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-vit-500 hover:bg-vit-600 text-white rounded-lg font-medium text-sm transition-colors"
        >
          Retry Loading
        </button>
      </div>
    )
  }

  const { metrics, groups } = parsedSpec

  return (
    <div className={cn('min-h-screen transition-colors duration-200', theme === 'dark' ? 'bg-slate-950 text-slate-100 dark' : 'bg-slate-50 text-slate-900')}>

      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md px-4 lg:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <img src="/vit-icon.svg" alt="VIT Logo" className="w-7 h-7" />
            <span className="font-bold text-lg tracking-tight text-slate-900 dark:text-white">
              VIT Network <span className="text-vit-500 font-normal text-sm ml-1">Portal</span>
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-vit-500/10 text-vit-600 dark:text-vit-400 border border-vit-500/20">
            v{metrics.version}
          </div>
        </div>

        {/* Global Navigation Tabs */}
        <div className="hidden md:flex items-center gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={cn('px-3 py-1.5 rounded-lg transition-colors', activeTab === 'overview' ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white')}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('api')}
            className={cn('px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5', activeTab === 'api' ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white')}
          >
            <Code className="w-3.5 h-3.5" /> API Reference ({metrics.totalEndpoints})
          </button>
          <button
            onClick={() => setActiveTab('tachyon')}
            className={cn('px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5', activeTab === 'tachyon' ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white')}
          >
            <HardDrive className="w-3.5 h-3.5" /> Tachyon Storage
          </button>
          <button
            onClick={() => setActiveTab('auth')}
            className={cn('px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5', activeTab === 'auth' ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white')}
          >
            <Shield className="w-3.5 h-3.5" /> Security
          </button>
          <button
            onClick={() => setActiveTab('schemas')}
            className={cn('px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5', activeTab === 'schemas' ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white')}
          >
            <Database className="w-3.5 h-3.5" /> Schemas ({metrics.schemaCount})
          </button>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          <a
            href="/openapi.json"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
          >
            OpenAPI Spec <ExternalLink className="w-3 h-3" />
          </a>

          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-xl text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 transition-colors"
            title="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </button>
        </div>
      </header>

      {/* Mobile Sub-Header Navigation */}
      <div className="md:hidden flex items-center justify-around bg-slate-100 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 p-2 text-xs font-medium">
        <button onClick={() => setActiveTab('overview')} className={cn(activeTab === 'overview' && 'font-bold text-vit-500')}>Overview</button>
        <button onClick={() => setActiveTab('api')} className={cn(activeTab === 'api' && 'font-bold text-vit-500')}>API Ref</button>
        <button onClick={() => setActiveTab('tachyon')} className={cn(activeTab === 'tachyon' && 'font-bold text-vit-500')}>Tachyon</button>
        <button onClick={() => setActiveTab('auth')} className={cn(activeTab === 'auth' && 'font-bold text-vit-500')}>Auth</button>
        <button onClick={() => setActiveTab('schemas')} className={cn(activeTab === 'schemas' && 'font-bold text-vit-500')}>Schemas</button>
      </div>

      {/* ── MAIN CONTENT CONTAINER ─────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 lg:px-8 py-8">

        {/* 1. OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-10">
            {/* Hero Banner */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 text-white p-8 border border-slate-800 shadow-xl">
              <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-vit-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative z-10 max-w-3xl">
                <div className="flex items-center gap-2 text-vit-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  <Zap className="w-4 h-4" /> Official Developer Portal
                </div>
                <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-4">
                  VIT Network API Platform
                </h1>
                <p className="text-slate-300 text-base leading-relaxed mb-6">
                  Build high-performance applications on top of the VIT Network ecosystem. Explore hundreds of interactive endpoints covering decentralized predictions, Tachyon distributed file storage, AI intelligence engines, smart contracts, and identity management.
                </p>

                {/* Base URL & Config Bar */}
                <div className="grid sm:grid-cols-2 gap-4 bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 backdrop-blur-sm">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-vit-400" /> Active Base URL
                    </label>
                    <input
                      type="text"
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-vit-500 transition-colors"
                      placeholder="https://api.vitchain.network"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-amber-400" /> Session API Key / JWT
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-vit-500 transition-colors"
                      placeholder="Optional API Key or JWT Bearer Token"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Quick-Start Panel */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
              <h3 className="text-lg font-bold mb-2 flex items-center gap-2 text-slate-900 dark:text-white">
                <Terminal className="w-5 h-5 text-vit-500" /> Quick Start Health Check
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                Verify platform status in under 5 seconds with a credential-free health request.
              </p>

              <div className="relative rounded-xl bg-slate-950 border border-slate-800 p-4 font-mono text-xs text-slate-200 overflow-x-auto">
                <button
                  onClick={() => handleCopy('quickstart', `curl -X GET "${baseUrl}/health" \\\n  -H "Accept: application/json"`)}
                  className="absolute top-3 right-3 p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                  title="Copy Code"
                >
                  {copiedKey === 'quickstart' ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
                <pre>{`curl -X GET "${baseUrl}/health" \\\n  -H "Accept: application/json"`}</pre>
              </div>
            </div>

            {/* API Overview Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Total Endpoints</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.totalEndpoints}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">GET Operations</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.methodCounts.GET}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">POST Operations</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.methodCounts.POST}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-amber-600 dark:text-amber-400 font-medium">PUT / PATCH</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.methodCounts.PUT + metrics.methodCounts.PATCH}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-rose-600 dark:text-rose-400 font-medium">DELETE</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.methodCounts.DELETE}</p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Data Schemas</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.schemaCount}</p>
              </div>
            </div>

            {/* Feature Discovery */}
            <div>
              <h3 className="text-xl font-bold mb-4 text-slate-900 dark:text-white">API Categories</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {groups.slice(0, 9).map(group => (
                  <div
                    key={group.name}
                    onClick={() => {
                      setActiveTab('api')
                      if (group.endpoints.length > 0) {
                        setSelectedEndpointId(group.endpoints[0].id)
                      }
                    }}
                    className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-vit-500/50 cursor-pointer transition-all group"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-slate-900 dark:text-white group-hover:text-vit-500 transition-colors">
                        {group.name}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold">
                        {group.endpoints.length}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                      {group.description || `Endpoints for managing ${group.name.toLowerCase()} operations.`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 2. API REFERENCE TAB */}
        {activeTab === 'api' && (
          <div className="grid lg:grid-cols-12 gap-8">

            {/* Sidebar Endpoint Browser */}
            <div className="lg:col-span-4 space-y-4">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter endpoints, methods, paths..."
                  className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-vit-500"
                />
              </div>

              <div className="space-y-2 max-h-[75vh] overflow-y-auto pr-1">
                {filteredGroups.map(group => {
                  const isExpanded = expandedGroups[group.name] ?? false
                  return (
                    <div key={group.name} className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900">
                      <button
                        onClick={() => setExpandedGroups(prev => ({ ...prev, [group.name]: !isExpanded }))}
                        className="w-full px-3.5 py-2.5 flex items-center justify-between bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100 dark:hover:bg-slate-800/50 text-xs font-semibold text-slate-800 dark:text-slate-200 transition-colors"
                      >
                        <span className="truncate">{group.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold">
                            {group.endpoints.length}
                          </span>
                          <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', isExpanded && 'rotate-180')} />
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-1 space-y-0.5">
                          {group.endpoints.map(ep => {
                            const badge = METHOD_BADGES[ep.method]
                            const isSelected = selectedEndpointId === ep.id
                            return (
                              <button
                                key={ep.id}
                                onClick={() => setSelectedEndpointId(ep.id)}
                                className={cn(
                                  'w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center gap-2 transition-all',
                                  isSelected
                                    ? 'bg-vit-500/10 text-vit-600 dark:text-vit-400 font-semibold border border-vit-500/30'
                                    : 'hover:bg-slate-100 dark:hover:bg-slate-800/60 text-slate-700 dark:text-slate-300'
                                )}
                              >
                                <span className={cn('text-[10px] font-mono font-extrabold uppercase px-1.5 py-0.5 rounded border', badge.bg, badge.text, badge.border)}>
                                  {ep.method}
                                </span>
                                <span className="font-mono text-[11px] truncate">{ep.path}</span>
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Endpoint Detail & Try It Out Runner */}
            <div className="lg:col-span-8">
              {selectedEndpoint ? (
                <div className="space-y-8">

                  {/* Header Detail */}
                  <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className={cn('text-xs font-mono font-bold uppercase px-2.5 py-1 rounded-md border', METHOD_BADGES[selectedEndpoint.method].bg, METHOD_BADGES[selectedEndpoint.method].text, METHOD_BADGES[selectedEndpoint.method].border)}>
                        {selectedEndpoint.method}
                      </span>
                      <span className="font-mono text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                        {selectedEndpoint.path}
                      </span>
                    </div>

                    <h2 className="text-xl font-extrabold text-slate-900 dark:text-white">{selectedEndpoint.summary}</h2>
                    {selectedEndpoint.description && (
                      <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                        {selectedEndpoint.description}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
                      <span>Operation ID: <code className="font-mono text-vit-500">{selectedEndpoint.operationId}</code></span>
                      <span>Tag: <span className="font-medium">{selectedEndpoint.tag}</span></span>
                    </div>
                  </div>

                  {/* Split Panel: Parameters vs Interactive Runner */}
                  <div className="grid md:grid-cols-2 gap-6">

                    {/* Left: Input Parameters */}
                    <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
                      <h4 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                        <Filter className="w-4 h-4 text-vit-500" /> Request Parameters
                      </h4>

                      {selectedEndpoint.parameters.length === 0 ? (
                        <p className="text-xs text-slate-400 italic">No path or query parameters required.</p>
                      ) : (
                        <div className="space-y-3">
                          {selectedEndpoint.parameters.map(p => (
                            <div key={p.name} className="space-y-1">
                              <div className="flex items-center justify-between text-xs">
                                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{p.name}</span>
                                <span className="text-[10px] text-slate-400 uppercase">{p.in} {p.required && '• required'}</span>
                              </div>
                              <input
                                type="text"
                                value={runnerParams[p.name] || ''}
                                onChange={(e) => setRunnerParams({ ...runnerParams, [p.name]: e.target.value })}
                                placeholder={p.description || `Enter ${p.name}`}
                                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-vit-500"
                              />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Request Body JSON Editor */}
                      {selectedEndpoint.requestBody && (
                        <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-900 dark:text-white">Request Body JSON</span>
                            <span className="text-[10px] text-slate-400 font-mono">{selectedEndpoint.requestBody.mediaType}</span>
                          </div>
                          <textarea
                            rows={8}
                            value={runnerBody}
                            onChange={(e) => setRunnerBody(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-emerald-400 focus:outline-none focus:border-vit-500"
                          />
                        </div>
                      )}
                    </div>

                    {/* Right: Try It Out & Code Snippets */}
                    <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                          <Play className="w-4 h-4 text-emerald-500" /> Interactive Runner
                        </h4>
                        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-0.5 rounded-lg text-[10px] font-semibold">
                          <button
                            onClick={() => setRunnerActiveLang('curl')}
                            className={cn('px-2 py-1 rounded', runnerActiveLang === 'curl' && 'bg-white dark:bg-slate-700 shadow-sm')}
                          >
                            cURL
                          </button>
                          <button
                            onClick={() => setRunnerActiveLang('js')}
                            className={cn('px-2 py-1 rounded', runnerActiveLang === 'js' && 'bg-white dark:bg-slate-700 shadow-sm')}
                          >
                            JS
                          </button>
                          <button
                            onClick={() => setRunnerActiveLang('python')}
                            className={cn('px-2 py-1 rounded', runnerActiveLang === 'python' && 'bg-white dark:bg-slate-700 shadow-sm')}
                          >
                            Python
                          </button>
                        </div>
                      </div>

                      {/* Code Snippet Box */}
                      <div className="relative rounded-xl bg-slate-950 border border-slate-800 p-3 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-48">
                        <button
                          onClick={() => handleCopy('snippet', generateCodeExamples(selectedEndpoint, baseUrl, runnerParams, runnerBody, runnerHeaders)[runnerActiveLang])}
                          className="absolute top-2 right-2 p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"
                        >
                          {copiedKey === 'snippet' ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                        <pre>
                          {generateCodeExamples(selectedEndpoint, baseUrl, runnerParams, runnerBody, runnerHeaders)[runnerActiveLang]}
                        </pre>
                      </div>

                      {/* Execute Button */}
                      <button
                        onClick={handleExecuteRequest}
                        disabled={isExecuting}
                        className="w-full py-2.5 px-4 bg-vit-500 hover:bg-vit-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center gap-2"
                      >
                        {isExecuting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                        Execute Request Against {baseUrl}
                      </button>

                      {/* Execution Result */}
                      {executionResult && (
                        <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-900 dark:text-white">Response Status</span>
                            <span className={cn('font-mono font-bold px-2 py-0.5 rounded', (executionResult.status || 0) < 400 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500')}>
                              {executionResult.status || 'Error'} {executionResult.statusText} ({executionResult.durationMs}ms)
                            </span>
                          </div>

                          <div className="rounded-xl bg-slate-950 border border-slate-800 p-3 font-mono text-[11px] text-slate-200 max-h-64 overflow-y-auto">
                            {executionResult.error ? (
                              <p className="text-rose-400">{executionResult.error}</p>
                            ) : (
                              <pre>{JSON.stringify(executionResult.data, null, 2)}</pre>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Documented Responses */}
                  <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">Documented Responses</h3>
                    <div className="space-y-3">
                      {selectedEndpoint.responses.map(r => (
                        <div key={r.statusCode} className="p-3.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className={cn('text-xs font-mono font-bold px-2 py-0.5 rounded', r.statusCode.startsWith('2') ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500')}>
                              HTTP {r.statusCode}
                            </span>
                            <span className="text-xs text-slate-500">{r.description}</span>
                          </div>
                          {r.example && (
                            <pre className="p-3 rounded-lg bg-slate-950 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-40">
                              {JSON.stringify(r.example, null, 2)}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              ) : (
                <div className="p-12 text-center border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900">
                  <Code className="w-12 h-12 text-slate-400 mx-auto mb-3" />
                  <h3 className="font-bold text-slate-900 dark:text-white">Select an Endpoint</h3>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                    Choose any endpoint from the sidebar browser to view interactive parameters, code snippets, and execute live API calls.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 3. TACHYON FILE STORAGE TAB */}
        {activeTab === 'tachyon' && (
          <div className="space-y-10">
            <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-900/40 via-slate-900 to-slate-950 border border-blue-800/50 space-y-3">
              <div className="flex items-center gap-2 text-blue-400 text-xs font-bold uppercase">
                <HardDrive className="w-4 h-4" /> Decentralized File Engine
              </div>
              <h2 className="text-2xl font-extrabold text-white">Tachyon Storage Architecture</h2>
              <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                Tachyon provides high-throughput, Reed-Solomon erasure coded decentralized file storage across the VIT Network. Access direct multipart uploads, file key metadata retrieval, manifest tracking, and provider linking.
              </p>
            </div>

            {/* Lifecycle Flow Diagram */}
            <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Workflow className="w-5 h-5 text-vit-500" /> Tachyon Storage Lifecycle
              </h3>

              <div className="grid sm:grid-cols-4 gap-4 text-center">
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-full bg-blue-500/10 text-blue-500 font-bold flex items-center justify-center mx-auto text-xs">1</div>
                  <p className="text-xs font-bold text-slate-900 dark:text-white">Upload File</p>
                  <code className="text-[10px] font-mono text-vit-500 block">POST /api/tachyon/upload</code>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/10 text-emerald-500 font-bold flex items-center justify-center mx-auto text-xs">2</div>
                  <p className="text-xs font-bold text-slate-900 dark:text-white">Retrieve Metadata</p>
                  <code className="text-[10px] font-mono text-vit-500 block">GET /api/tachyon/files/{'{key}'}</code>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-full bg-purple-500/10 text-purple-500 font-bold flex items-center justify-center mx-auto text-xs">3</div>
                  <p className="text-xs font-bold text-slate-900 dark:text-white">Download Stream</p>
                  <code className="text-[10px] font-mono text-vit-500 block">GET /api/tachyon/download/{'{file_id}'}</code>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-full bg-rose-500/10 text-rose-500 font-bold flex items-center justify-center mx-auto text-xs">4</div>
                  <p className="text-xs font-bold text-slate-900 dark:text-white">Purge File</p>
                  <code className="text-[10px] font-mono text-vit-500 block">DELETE /api/tachyon/files/{'{key}'}</code>
                </div>
              </div>
            </div>

            {/* Tachyon Specific Endpoints List */}
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-slate-900 dark:text-white">Tachyon Operations ({tachyonEndpoints.length})</h3>
              <div className="space-y-3">
                {tachyonEndpoints.map(ep => (
                  <div key={ep.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={cn('text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border', METHOD_BADGES[ep.method].bg, METHOD_BADGES[ep.method].text, METHOD_BADGES[ep.method].border)}>
                          {ep.method}
                        </span>
                        <code className="font-mono text-xs font-bold text-slate-900 dark:text-white">{ep.path}</code>
                      </div>
                      <p className="text-xs text-slate-500">{ep.summary}</p>
                    </div>

                    <button
                      onClick={() => {
                        setActiveTab('api')
                        setSelectedEndpointId(ep.id)
                      }}
                      className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-vit-500 hover:text-white text-xs font-semibold transition-colors self-start sm:self-auto"
                    >
                      Inspect Endpoint
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 4. AUTHENTICATION & SECURITY TAB */}
        {activeTab === 'auth' && (
          <div className="space-y-8">
            <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950 via-slate-900 to-slate-950 border border-emerald-800/40 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase">
                <Shield className="w-4 h-4" /> Identity & Access Management
              </div>
              <h2 className="text-2xl font-extrabold text-white">Authentication Architecture</h2>
              <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                VIT Network uses dual API Key header validation (`X-API-Key`) and OAuth2/JWT Bearer Token authentication (`Authorization: Bearer [token]`).
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-6">
              <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Key className="w-5 h-5 text-amber-500" /> API Keys (X-API-Key)
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Ideal for server-to-server integrations and background workers. Include your active API key in the `X-API-Key` HTTP header.
                </p>
                <div className="p-3 rounded-lg bg-slate-950 text-amber-400 font-mono text-xs">
                  X-API-Key: vit_live_key_sample_12345
                </div>
              </div>

              <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Lock className="w-5 h-5 text-vit-500" /> JWT Bearer Tokens
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  For user-authenticated frontend applications. Request a JWT token via `/api/auth/login` and include it in the `Authorization` header.
                </p>
                <div className="p-3 rounded-lg bg-slate-950 text-vit-400 font-mono text-xs">
                  Authorization: Bearer eyJhbGciOiJIUzI1Ni...
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 5. SCHEMA EXPLORER TAB */}
        {activeTab === 'schemas' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Schema Explorer</h2>
                <p className="text-xs text-slate-500">Browse {schemasList.length} documented Pydantic / OpenAPI object schemas.</p>
              </div>

              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  value={schemaSearch}
                  onChange={(e) => setSchemaSearch(e.target.value)}
                  placeholder="Search schema names..."
                  className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-vit-500"
                />
              </div>
            </div>

            <div className="grid lg:grid-cols-12 gap-8">
              {/* Schema Name List */}
              <div className="lg:col-span-4 max-h-[70vh] overflow-y-auto space-y-1 pr-1 border border-slate-200 dark:border-slate-800 rounded-2xl p-2 bg-white dark:bg-slate-900">
                {schemasList.map(item => (
                  <button
                    key={item.name}
                    onClick={() => setSelectedSchemaName(item.name)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-xl text-xs font-mono truncate transition-all',
                      selectedSchemaName === item.name
                        ? 'bg-vit-500 text-white font-bold shadow-sm'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    )}
                  >
                    {item.name}
                  </button>
                ))}
              </div>

              {/* Schema Inspector */}
              <div className="lg:col-span-8">
                {selectedSchemaName && spec?.components?.schemas?.[selectedSchemaName] ? (
                  <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-6">
                    <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
                      <h3 className="font-mono text-lg font-bold text-slate-900 dark:text-white">
                        {selectedSchemaName}
                      </h3>
                      <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold">
                        {spec.components.schemas[selectedSchemaName].type || 'object'}
                      </span>
                    </div>

                    {/* Properties */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold uppercase text-slate-400">Properties</h4>
                      <div className="space-y-2">
                        {Object.entries<any>(spec.components.schemas[selectedSchemaName].properties || {}).map(([propName, propObj]) => (
                          <div key={propName} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1">
                            <div className="flex items-center justify-between text-xs font-mono">
                              <span className="font-bold text-slate-900 dark:text-white">{propName}</span>
                              <span className="text-vit-500">{propObj.type || 'any'}</span>
                            </div>
                            {propObj.description && (
                              <p className="text-[11px] text-slate-500">{propObj.description}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Mock JSON */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold uppercase text-slate-400">Sample Payload</h4>
                      <pre className="p-4 rounded-xl bg-slate-950 text-emerald-400 font-mono text-xs overflow-x-auto max-h-64">
                        {JSON.stringify(generateMockFromSchema(spec.components.schemas[selectedSchemaName], spec), null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="p-12 text-center border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900">
                    <Database className="w-12 h-12 text-slate-400 mx-auto mb-3" />
                    <h3 className="font-bold text-slate-900 dark:text-white">Select a Schema</h3>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                      Choose any schema from the left panel to inspect properties, data types, and mock JSON payloads.
                    </p>
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
