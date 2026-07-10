import { useState } from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Upload, Download, Trash2, RefreshCw, Search, FileIcon } from 'lucide-react'
import { useStorageHealth } from '@/hooks/useHealth'
import { useStorageList } from '@/hooks/useStorage'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { StatCard } from '@/components/StatCard'
import { Spinner } from '@/components/ui/Spinner'
import { formatBytes } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '@/lib/api'

export default function Storage() {
  const { data: health, isLoading: healthLoading } = useStorageHealth()
  const { data: listData, isLoading: listLoading }   = useStorageList()
  const [search, setSearch] = useState('')
  const qc = useQueryClient()

  const objects = listData?.objects ?? []
  const filtered = objects.filter((o: any) =>
    o.key?.toLowerCase().includes(search.toLowerCase()),
  )

  function refresh() {
    qc.invalidateQueries({ queryKey: ['health', 'storage'] })
    qc.invalidateQueries({ queryKey: ['storage'] })
  }

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
              Decentralized object storage. Data sourced directly from the vit-storage service.
            </p>
          </motion.div>
          <button onClick={refresh} disabled={healthLoading || listLoading} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm transition-all">
            <RefreshCw className={`w-4 h-4 ${(healthLoading || listLoading) ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            { label: 'Status',       value: health?.status ?? '—',                                          icon: HardDrive },
            { label: 'Objects',      value: health?.objectCount ?? listData?.total ?? objects.length ?? '—', icon: FileIcon },
            { label: 'Used Storage', value: health?.used != null ? formatBytes(health.used) : '—',           icon: HardDrive },
            { label: 'Capacity',     value: health?.capacity != null ? formatBytes(health.capacity) : '—',   icon: HardDrive },
          ].map((s, i) => <StatCard key={s.label} {...s} index={i} />)}
        </div>

        {/* Object Browser */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
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
              {/* Upload */}
              <a
                href={`${ENDPOINTS.storage}/api/objects`}
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
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-8 h-8" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16">
              <HardDrive className="w-10 h-10 text-white/20 mx-auto mb-3" />
              <p className="text-white/40 text-sm">
                {objects.length === 0
                  ? 'No objects found in vit-storage — the bucket may be empty or the API path may differ.'
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
                      <td className="py-3 pr-4 text-white/40 text-xs">{obj.lastModified ? new Date(obj.lastModified).toLocaleDateString() : '—'}</td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {obj.url && (
                            <a href={obj.url} target="_blank" rel="noopener noreferrer"
                              className="p-1.5 rounded hover:bg-white/10 text-white/50 hover:text-white transition-colors">
                              <Download className="w-3.5 h-3.5" />
                            </a>
                          )}
                          <button className="p-1.5 rounded hover:bg-red-500/10 text-white/50 hover:text-red-400 transition-colors">
                            <Trash2 className="w-3.5 h-3.5" />
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
