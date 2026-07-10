const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL ?? 'https://vitnetwork-nls4.onrender.com'
const AI_URL      = import.meta.env.VITE_AI_URL      ?? 'https://vit-ai.onrender.com'
const STORAGE_URL = import.meta.env.VITE_STORAGE_URL ?? 'https://vit-storage-4trt.onrender.com'

export const ENDPOINTS = {
  gateway: GATEWAY_URL.replace(/\/$/, ''),
  ai:      AI_URL.replace(/\/$/, ''),
  storage: STORAGE_URL.replace(/\/$/, ''),
}

// ---------- helpers ----------

async function get<T>(url: string, signal?: AbortSignal): Promise<T> {
  const start   = performance.now()
  const res     = await fetch(url, { signal })
  const latency = Math.round(performance.now() - start)
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`)
  const data = await res.json()
  if (Array.isArray(data)) return data as unknown as T
  return { ...data, _latency: latency } as T
}

// ---------- gateway (vitnetwork-nls4.onrender.com) ----------
// Verified live routes: GET /health  GET /system/status  GET /ping
// GET /api/obs/* (status, metrics, diagnostics, alerts, audit)
// GET /api/chain/* (latest, height, recent-blocks, metrics)
// GET /api/explorer/* (blocks, transactions)

export interface GatewayHealth {
  status: string
  version?: string
  models_loaded?: number
  db_connected?: boolean
  clv_tracking_enabled?: boolean
  agents?: unknown
  ai_providers?: unknown
  uptime?: number
  environment?: string
  _latency?: number
}

export interface GatewaySystemStatus {
  status?: string
  environment?: string
  version?: string
  uptime?: number
  db_connected?: boolean
  redis?: { status: string; latency?: number }
  postgres?: { status: string; latency?: number }
  [key: string]: unknown
}

export interface ChainMetrics {
  block_height?: number
  total_transactions?: number
  active_validators?: number
  tps?: number
  [key: string]: unknown
}

export const gatewayApi = {
  health:       (s?: AbortSignal) => get<GatewayHealth>(`${ENDPOINTS.gateway}/health`, s),
  systemStatus: (s?: AbortSignal) => get<GatewaySystemStatus>(`${ENDPOINTS.gateway}/system/status`, s),
  obsStatus:    (s?: AbortSignal) => get<Record<string, unknown>>(`${ENDPOINTS.gateway}/api/obs/status`, s),
  obsDiag:      (s?: AbortSignal) => get<Record<string, unknown>>(`${ENDPOINTS.gateway}/api/obs/diagnostics`, s),
  chainMetrics: (s?: AbortSignal) => get<ChainMetrics>(`${ENDPOINTS.gateway}/api/chain/metrics`, s),
  chainLatest:  (s?: AbortSignal) => get<Record<string, unknown>>(`${ENDPOINTS.gateway}/api/chain/latest`, s),
  chainHeight:  (s?: AbortSignal) => get<{ height: number }>(`${ENDPOINTS.gateway}/api/chain/height`, s),
  recentBlocks: (s?: AbortSignal) => get<unknown[]>(`${ENDPOINTS.gateway}/api/chain/recent-blocks`, s),
}

// ---------- AI (vit-ai.onrender.com, prefix /api/v1) ----------
// Verified live routes: GET /health  GET /version
// GET /api/v1/models  GET /api/v1/ai/status  GET /api/v1/ai/providers
// GET /api/v1/ensemble/status  GET /api/v1/datasets  GET /api/v1/features
// POST /api/v1/infer|predict|chat|classify|summarize|embed|ensemble

export interface AIHealth {
  status: string
  _latency?: number
}

export interface AIKernelStatus {
  status?: string
  version?: string
  loaded_models_count?: number
  mode?: string
  uptime?: string | number
  total_inferences?: number
  error_rate?: string | number
  avg_latency?: string | number
  [key: string]: unknown
}

export interface EnsembleStatus {
  status?: string
  active_models?: number
  [key: string]: unknown
}

export interface Model {
  id: string
  name?: string
  provider?: string
  status?: string
  version?: string
  latest_version?: string
  description?: string
  task?: string
}

export interface Dataset {
  id: string
  name?: string
  size?: number
  [key: string]: unknown
}

export const aiApi = {
  health:         (s?: AbortSignal) => get<AIHealth>(`${ENDPOINTS.ai}/health`, s),
  version:        (s?: AbortSignal) => get<{ version: string }>(`${ENDPOINTS.ai}/version`, s),
  aiStatus:       (s?: AbortSignal) => get<AIKernelStatus>(`${ENDPOINTS.ai}/api/v1/ai/status`, s),
  // providers returns string[] e.g. ["internal","ensemble"]
  providers:      (s?: AbortSignal) => get<string[]>(`${ENDPOINTS.ai}/api/v1/ai/providers`, s),
  models:         (s?: AbortSignal) => get<Model[]>(`${ENDPOINTS.ai}/api/v1/models`, s),
  ensembleStatus: (s?: AbortSignal) => get<EnsembleStatus>(`${ENDPOINTS.ai}/api/v1/ensemble/status`, s),
  datasets:       (s?: AbortSignal) => get<Dataset[]>(`${ENDPOINTS.ai}/api/v1/datasets`, s),
  features:       (s?: AbortSignal) => get<unknown[]>(`${ENDPOINTS.ai}/api/v1/features`, s),
}

// ---------- Storage (vit-storage-4trt.onrender.com) ----------
// Verified live routes: GET /health  GET /api/v1/status
// GET /api/v1/files  GET /api/v1/files/{id}
// POST /api/v1/upload  GET /api/v1/download/{id}
// S3-compat: PUT/GET/DELETE /api/v1/s3/{bucket}/{key}

export interface StorageHealth {
  status: string
  version?: string
  plane?: string
  database?: string
  redis?: string
  timestamp?: string
  subsystems?: Record<string, { healthy: boolean; quarantined?: boolean; usage_pct?: number }>
  _latency?: number
}

export interface TachyonStatus {
  status: string
  module?: string
  version?: string
  active_nodes?: number
  manifest_count?: number
  total_bytes?: number
  providers?: Record<string, { healthy: boolean; quarantined?: boolean; usage_pct?: number }>
  _latency?: number
}

export interface StorageFile {
  file_id?: string
  filename?: string
  key?: string
  size_bytes?: number
  size?: number
  content_type?: string
  contentType?: string
  created_at?: string
  lastModified?: string
  url?: string
}

export const storageApi = {
  health:        (s?: AbortSignal) => get<StorageHealth>(`${ENDPOINTS.storage}/health`, s),
  tachyonStatus: (s?: AbortSignal) => get<TachyonStatus>(`${ENDPOINTS.storage}/api/v1/status`, s),
  // /api/v1/files is the verified endpoint (not /manifests or /objects)
  files:         (s?: AbortSignal) => get<StorageFile[]>(`${ENDPOINTS.storage}/api/v1/files`, s),
  fileById:      (id: string, s?: AbortSignal) => get<StorageFile>(`${ENDPOINTS.storage}/api/v1/files/${id}`, s),
  metrics:       (s?: AbortSignal) => get<unknown>(`${ENDPOINTS.storage}/metrics`, s),
}
