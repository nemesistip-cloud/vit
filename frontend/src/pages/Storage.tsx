import { useState } from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Upload, Download, RefreshCw, Search, FileIcon, Database, Activity } from 'lucide-react'
import { useStorageHealth } from '@/hooks/useHealth'
import { useStorageList, useTachyonStatus } from '@/hooks/useStorage'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { formatBytes } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '@/lib/api'
import type { StorageObject } from '@/lib/api'

export default function Storage() {
  const { data: health,  isLoading: healthLoading } = useStorageHealth()
  const { data: tachyon, isLoading: tachyonLoading } = useTachyonStatus()
  const { data: listData, isLoading: listLoading }   = useStorageList()
  const [search, setSearch] = useState('')
  const qc = useQueryClient()

  // Normalise object list from whichever shape the API returns
  const rawObjects: StorageObject[] = listData?.objects ?? listData?.manifests ?? []
  const filtered = rawObjects.filter((o: any) => {
    const key = o.key ?? o.filename ?? o.file_id ?? ''
    return key.toLowerCase().includes(search.toLowerCase())
  })

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health', 'storage'] })
    qc.invalidateQueries({ queryKey: ['storage'] })
  }

  const isLoading = healthLoading || tachyonLoading

  // Prefer tachyon status for metrics; fall back to health
  const manifestCount = tachyon?.manifest_count ?? health?.objectCount
  const totalBytes    = tachyon?.total_bytes    ?? health?.used
  const activeNodes   = tachyon?.active_nodes

  return (
    <div className="pt-24 pb-16">
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
              Decentralised object storage — Tachyon coordination plane. Data sourced directly from vit-storage.
            </p>
          </motion.div>
          <button
            onClick={refresh}
            disabled={isLoading || listLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${(isLoading || listLoading) ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Status',        value: health?.status        ?? '—',                               icon: Activity  },
            { label: 'Objects',       value: manifestCount != null ? manifestCount : '—',                 icon: FileIcon  },
            { label: 'Total Storage', value: totalBytes    != null ? formatBytes(totalBytes) : '—',       icon: HardDrive },
            { label: 'Active Nodes',  value: activeNodes   != null ? activeNodes : (health?.version ?? '—'), icon: Database  },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Tachyon Status Card */}
        {tachyon && (
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="rounded-xl border border-white/10 bg-white/5 p-6 mb-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Database className="w-4 h-4 text-vit-400" /> Tachyon Coordination Plane
              </h2>
              <StatusBadge status={tachyon.status} size="sm" pulse />
            </div>
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { label: 'Module',         value: tachyon.module   ?? '—' },
                { label: 'Version',        value: tachyon.version  ?? '—' },
                { label: 'Active Nodes',   value: tachyon.active_nodes  != null ? String(tachyon.active_nodes)  : '—' },
                { label: 'Manifests',      value: tachyon.manifest_count != null ? String(tachyon.manifest_count) : '—' },
                { label: 'Total Stored',   value: tachyon.total_bytes != null ? formatBytes(tachyon.total_bytes) : '—' },
                { label: 'Storage State',  value: tachyon.status ?? '—' },
              ].map(m => (
                <div key={m.label} className="bg-white/5 rounded-lg p-4">
                  <p className="text-xs text-white/40 mb-1">{m.label}</p>
                  <p className="text-base font-semibold text-white font-mono">{m.value}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Object Browser */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="rounded-xl border border-white/10 bg-white/5 p-6"
        >
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-white">Object Browser</h2>
              <StatusBadge status={health?.status} size="sm" pulse />
            </div>
            <div className="flex items-center gap-3">
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
              <a
                href={`${ENDPOINTS.storage}/api/v1/upload`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors"
              >
                <Upload className="w-4 h-4" />
                Upload
              </a>
            </div>
          </div>

          {listLoading ? (
            <div className="flex items-center justify-center py-16"><Spinner className="w-8 h-8" /></div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16">
              <HardDrive className="w-10 h-10 text-white/20 mx-auto mb-3" />
              <p className="text-white/40 text-sm">
                {rawObjects.length === 0
                  ? 'No objects found — the storage bucket may be empty or the manifest endpoint is not yet available.'
                  : 'No objects match your search.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    {['Key / Filename', 'Size', 'Type', 'Date', 'Actions'].map(h => (
                      <th key={h} className="text-left text-white/40 font-medium pb-3 pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((obj: any, i) => {
                    const key       = obj.key ?? obj.filename ?? obj.file_id ?? `object-${i}`
                    const sizeBytes = obj.size ?? obj.size_bytes ?? 0
                    const ct        = obj.contentType ?? obj.content_type ?? '—'
                    const date      = obj.lastModified ?? obj.created_at
                    const dlUrl     = obj.url ?? `${ENDPOINTS.storage}/api/v1/download/${obj.file_id ?? key}`
                    return (
                      <tr key={key} className="border-b border-white/5 last:border-0 group">
                        <td className="py-3 pr-4 font-mono text-vit-300 text-xs truncate max-w-[200px]">{key}</td>
                        <td className="py-3 pr-4 text-white/60">{formatBytes(sizeBytes)}</td>
                        <td className="py-3 pr-4 text-white/40 text-xs">{ct}</td>
                        <td className="py-3 pr-4 text-white/40 text-xs">
                          {date ? new Date(date).toLocaleDateString() : '—'}
                        </td>
                        <td className="py-3 pr-4">
                          <a
                            href={dlUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-white/10 text-white/50 hover:text-white"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
