import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Layers, Hash, Clock, ArrowRight, Search, RefreshCw,
  TrendingUp, Cpu, Activity, AlertCircle, ChevronRight,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { StatusBadge } from '@/components/ui/StatusBadge'

function useChainHeight() {
  return useQuery({
    queryKey: ['chain-height'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/chain/height`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 10_000, refetchInterval: 15_000,
  })
}

function useRecentBlocks() {
  return useQuery({
    queryKey: ['recent-blocks'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/chain/recent-blocks?limit=10`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.blocks ?? []
    },
    staleTime: 10_000, refetchInterval: 20_000,
  })
}

function useChainMetrics() {
  return useQuery({
    queryKey: ['chain-metrics'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/chain/metrics`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 30_000,
  })
}

function useNetworkAnalytics() {
  return useQuery({
    queryKey: ['network-analytics'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/blockchain/analytics/network`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 60_000,
  })
}

function MetricCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value?: string | number | null; sub?: string; color: string
}) {
  return (
    <div className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-white/40 uppercase tracking-wide font-medium">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
      {sub && <div className="text-xs text-white/35 mt-1">{sub}</div>}
    </div>
  )
}

export default function Explorer() {
  const [search, setSearch] = useState('')
  const { data: heightData, refetch }         = useChainHeight()
  const { data: blocks, isLoading: blocksLoading } = useRecentBlocks()
  const { data: metrics }                     = useChainMetrics()
  const { data: network }                     = useNetworkAnalytics()

  const height  = heightData?.height ?? -1
  const hasChain = height >= 0

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    // TODO: navigate to block/tx/address detail
  }

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                <Layers className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">VIT Chain Explorer</h1>
                <p className="text-white/50 text-sm">Browse blocks, transactions, and addresses on VIT Network (Chain ID: 7764)</p>
              </div>
            </div>
            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-3">
              <div className="relative flex-1 max-w-2xl">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search by block height, tx hash, or address..."
                  className="w-full pl-9 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-500/50 transition-colors"
                />
              </div>
              <button type="submit" className="px-5 py-3 rounded-xl bg-vit-500 hover:bg-vit-400 text-white text-sm font-medium transition-colors flex items-center gap-2">
                <Search className="w-4 h-4" /> Search
              </button>
            </form>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Chain not yet seeded banner */}
        {!hasChain && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="flex items-center gap-4 p-5 rounded-xl border border-amber-500/30 bg-amber-500/5">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-300">Genesis Block Pending</p>
              <p className="text-xs text-amber-400/60 mt-0.5">The VIT chain hasn't produced a genesis block yet. The blockchain subsystem is initializing.</p>
            </div>
          </motion.div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard icon={Layers}   label="Chain Height"    value={hasChain ? height.toLocaleString() : 'Pending'}    sub="Latest block"        color="bg-cyan-500/20" />
          <MetricCard icon={Activity} label="Total TXs"       value={metrics?.total_transactions ?? network?.total_transactions}  sub="All time"        color="bg-vit-500/20" />
          <MetricCard icon={TrendingUp} label="VIT Staked"    value={network?.total_staked ?? metrics?.total_staked}    sub="Across all validators" color="bg-amber-500/20" />
          <MetricCard icon={Cpu}      label="Active Validators" value={network?.active_validators ?? metrics?.validator_count} sub="PoS validators"  color="bg-emerald-500/20" />
        </div>

        {/* Add to MetaMask */}
        <div className="flex items-center justify-between p-5 rounded-xl border border-white/10 bg-white/3">
          <div>
            <p className="text-sm font-medium text-white">Add VIT Network to MetaMask</p>
            <p className="text-xs text-white/40 mt-0.5">Chain ID: 7764 · Currency: VIT · RPC: {ENDPOINTS.gateway}/api/chain/rpc</p>
          </div>
          <button className="px-4 py-2 rounded-lg bg-orange-500/20 border border-orange-500/30 text-orange-400 text-sm font-medium hover:bg-orange-500/30 transition-colors flex items-center gap-2">
            <span>🦊</span> Add Network
          </button>
        </div>

        {/* Recent Blocks */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" /> Recent Blocks
            </h2>
            <button onClick={() => refetch()} className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white transition-colors">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
          </div>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
            {blocksLoading ? (
              <div className="flex items-center justify-center py-16"><Spinner className="w-6 h-6 text-vit-400" /></div>
            ) : !blocks || blocks.length === 0 ? (
              <div className="text-center py-16">
                <Layers className="w-12 h-12 text-white/10 mx-auto mb-3" />
                <p className="text-white/40">No blocks yet</p>
                <p className="text-white/25 text-sm mt-1">The chain will produce blocks once the genesis block is seeded.</p>
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/8">
                    <th className="text-left text-xs text-white/40 uppercase tracking-wide px-6 py-4">Height</th>
                    <th className="text-left text-xs text-white/40 uppercase tracking-wide px-6 py-4 hidden sm:table-cell">Hash</th>
                    <th className="text-left text-xs text-white/40 uppercase tracking-wide px-6 py-4 hidden md:table-cell">Validator</th>
                    <th className="text-right text-xs text-white/40 uppercase tracking-wide px-6 py-4">TXs</th>
                    <th className="text-right text-xs text-white/40 uppercase tracking-wide px-6 py-4">Age</th>
                  </tr>
                </thead>
                <tbody>
                  {blocks.map((block: any, i: number) => (
                    <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                      className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                      <td className="px-6 py-4">
                        <span className="text-sm font-medium text-vit-400">#{block.height ?? block.block_number ?? i}</span>
                      </td>
                      <td className="px-6 py-4 hidden sm:table-cell">
                        <span className="text-xs font-mono text-white/40">
                          {(block.hash || block.block_hash || '').slice(0, 16)}…
                        </span>
                      </td>
                      <td className="px-6 py-4 hidden md:table-cell">
                        <span className="text-xs font-mono text-white/40">
                          {block.validator ? `${block.validator.slice(0, 12)}…` : '—'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm text-white/60">{block.tx_count ?? block.transaction_count ?? 0}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-xs text-white/35">
                          {block.timestamp ? timeAgo(block.timestamp) : '—'}
                        </span>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
