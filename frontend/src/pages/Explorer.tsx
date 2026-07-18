import { useState, type ElementType, type FormEvent } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Layers, Search, RefreshCw,
  Activity, ChevronRight,
  Box, Zap, Network, Database, Clock,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'

// ── Data hooks ────────────────────────────────────────────────────────────────

function useChainHeight() {
  return useQuery({
    queryKey: ['chain-height'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/chain/height`, { signal })
      return r.ok ? r.json() : null
    },
    staleTime: 10_000,
    refetchInterval: 15_000,
    retry: false,
  })
}

function useRecentBlocks() {
  return useQuery({
    queryKey: ['recent-blocks'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/chain/recent-blocks?limit=10`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : (d?.blocks ?? [])
    },
    staleTime: 10_000,
    refetchInterval: 20_000,
    retry: false,
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
    retry: false,
  })
}

function useRecentTxns() {
  return useQuery({
    queryKey: ['recent-txns'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/chain/transactions?limit=8`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : (d?.transactions ?? [])
    },
    staleTime: 10_000,
    refetchInterval: 20_000,
    retry: false,
  })
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MetricCard({
  icon: Icon, label, value, sub, color,
}: {
  icon: ElementType; label: string; value?: string | number | null; sub?: string; color: string
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

function BlockRow({ block, i }: { block: Record<string, unknown>; i: number }) {
  const height = block?.height ?? block?.number ?? block?.index ?? '—'
  const hash   = String(block?.hash ?? block?.block_hash ?? '').slice(0, 16)
  const txns   = block?.transaction_count ?? block?.tx_count ?? block?.transactions ?? 0
  const ts     = block?.timestamp ?? block?.created_at ?? null

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.05 }}
      className="flex items-center gap-4 px-4 py-3 rounded-xl bg-white/3 border border-white/5 hover:border-cyan-500/20 hover:bg-white/5 transition-all group"
    >
      <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center flex-shrink-0">
        <Box className="w-4 h-4 text-cyan-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">Block #{String(height)}</span>
          {hash && (
            <span className="text-xs text-white/30 font-mono">{hash}…</span>
          )}
        </div>
        <div className="text-xs text-white/35 mt-0.5">
          {typeof txns === 'number' ? `${txns} transaction${txns !== 1 ? 's' : ''}` : '— txns'} 
          {ts && <span className="ml-2">&middot; {timeAgo(ts)}</span>}
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-cyan-400 transition-colors flex-shrink-0" />
    </motion.div>
  )
}

function TxnRow({ txn, i }: { txn: Record<string, unknown>; i: number }) {
  const hash  = String(txn?.hash ?? txn?.tx_hash ?? txn?.id ?? '').slice(0, 20)
  const type  = String(txn?.type ?? txn?.tx_type ?? 'transfer')
  const value = txn?.amount ?? txn?.value ?? null
  const ts    = txn?.timestamp ?? txn?.created_at ?? null

  const typeColor: Record<string, string> = {
    transfer: 'text-vit-400 bg-vit-500/10',
    stake: 'text-emerald-400 bg-emerald-500/10',
    reward: 'text-amber-400 bg-amber-500/10',
    prediction: 'text-purple-400 bg-purple-500/10',
  }
  const colorClass = typeColor[type.toLowerCase()] ?? 'text-white/40 bg-white/5'

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.05 }}
      className="flex items-center gap-4 px-4 py-3 rounded-xl bg-white/3 border border-white/5 hover:border-vit-500/20 hover:bg-white/5 transition-all group"
    >
      <div className="w-8 h-8 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center flex-shrink-0">
        <Zap className="w-4 h-4 text-vit-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {hash && <span className="text-xs text-white/50 font-mono">{hash}…</span>}
          <span className={cn('text-[10px] px-1.5 py-0.5 rounded font-medium capitalize', colorClass)}>{type}</span>
        </div>
        <div className="text-xs text-white/35 mt-0.5">
          {value != null ? `${value} VIT` : ''}
          {ts && <span className="ml-2">&middot; {timeAgo(ts)}</span>}
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-vit-400 transition-colors flex-shrink-0" />
    </motion.div>
  )
}

function GenesisState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-4">
        <Database className="w-8 h-8 text-cyan-400/50" />
      </div>
      <p className="text-white/50 text-sm font-medium mb-1">Awaiting Genesis Block</p>
      <p className="text-white/25 text-xs max-w-xs">
        VIT Chain (ID: 7764) is initialising. Blocks will appear here once the validator network reaches consensus.
      </p>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Explorer() {
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'blocks' | 'transactions'>('blocks')

  const { data: heightData, refetch, isFetching } = useChainHeight()
  const { data: blocks = [],  isLoading: blocksLoading  } = useRecentBlocks()
  const { data: metrics }                                  = useChainMetrics()
  const { data: txns = [],    isLoading: txnsLoading    } = useRecentTxns()

  const height    = (heightData?.height ?? heightData?.block_height ?? -1) as number
  const hasChain  = height >= 0
  const chainId   = heightData?.chain_id ?? 7764
  const tps       = metrics?.tps ?? metrics?.transactions_per_second ?? null
  const totalTxns = metrics?.total_transactions ?? metrics?.tx_count ?? null
  const validators = metrics?.active_validators ?? metrics?.validator_count ?? null
  const avgBlock  = metrics?.avg_block_time ?? null

  function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!search.trim()) return
    // Block height lookup
    if (/^\d+$/.test(search.trim())) {
      window.open(`${ENDPOINTS.gateway}/api/explorer/blocks/${search.trim()}`, '_blank')
    } else {
      window.open(`${ENDPOINTS.gateway}/api/explorer/search?q=${encodeURIComponent(search.trim())}`, '_blank')
    }
  }

  return (
    <div className="pt-16 min-h-screen">
      {/* Header ──────────────────────────────────────────────────────────── */}
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
                <p className="text-white/50 text-sm">
                  Browse blocks, transactions, and addresses &middot; Chain ID: {chainId}
                </p>
              </div>
              <div className="ml-auto flex items-center gap-3">
                <div className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border',
                  hasChain
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                )}>
                  <span className={cn(
                    'w-1.5 h-1.5 rounded-full',
                    hasChain ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                  )} />
                  {hasChain ? `Block #${height.toLocaleString()}` : 'Awaiting genesis'}
                </div>
                <button
                  onClick={() => refetch()}
                  className="p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/8 transition-colors"
                >
                  <RefreshCw className={cn('w-4 h-4 text-white/40', isFetching && 'animate-spin')} />
                </button>
              </div>
            </div>

            {/* Search ──────────────────────────────────────────────────── */}
            <form onSubmit={handleSearch} className="flex gap-3">
              <div className="relative flex-1 max-w-2xl">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search by block height, tx hash, or address…"
                  className="w-full pl-9 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-500/50 transition-colors"
                />
              </div>
              <button
                type="submit"
                className="px-5 py-3 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-sm font-medium hover:bg-cyan-500/20 transition-colors"
              >
                Search
              </button>
            </form>
          </motion.div>
        </div>
      </div>

      {/* Metrics ─────────────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard icon={Layers}   label="Chain Height"  value={hasChain ? height.toLocaleString() : '—'}  sub="Latest block"             color="bg-cyan-500/15" />
          <MetricCard icon={Zap}      label="TPS"           value={tps != null ? Number(tps).toFixed(2) : '—'}  sub="Transactions/sec"       color="bg-vit-500/15"  />
          <MetricCard icon={Activity} label="Total Txns"    value={totalTxns != null ? Number(totalTxns).toLocaleString() : '—'} sub="All time" color="bg-emerald-500/15" />
          <MetricCard icon={Network}  label="Validators"    value={validators ?? '—'} sub="Active nodes"                       color="bg-purple-500/15" />
        </div>

        {/* Avg block time banner */}
        {avgBlock != null && (
          <div className="flex items-center gap-2 mb-6 p-3 rounded-xl bg-white/3 border border-white/6">
            <Clock className="w-4 h-4 text-white/30" />
            <span className="text-xs text-white/50">Avg block time: <span className="text-white/70 font-medium">{avgBlock}s</span></span>
          </div>
        )}

        {/* Content tabs ────────────────────────────────────────────────── */}
        <div className="flex items-center gap-1 p-1 bg-white/5 border border-white/8 rounded-xl w-fit mb-6">
          {(['blocks', 'transactions'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all',
                activeTab === tab
                  ? 'bg-white/10 text-white shadow-sm'
                  : 'text-white/40 hover:text-white/60'
              )}
            >
              {tab === 'blocks' ? (
                <span className="flex items-center gap-1.5"><Box className="w-3.5 h-3.5" /> Blocks</span>
              ) : (
                <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> Transactions</span>
              )}
            </button>
          ))}
        </div>

        {/* Blocks list ─────────────────────────────────────────────────── */}
        {activeTab === 'blocks' && (
          <div className="space-y-2">
            {blocksLoading ? (
              <div className="flex justify-center py-12"><Spinner /></div>
            ) : Array.isArray(blocks) && blocks.length > 0 ? (
              blocks.map((block, i) => (
                <BlockRow key={String((block as Record<string, unknown>)?.hash ?? i)} block={block as Record<string, unknown>} i={i} />
              ))
            ) : (
              <GenesisState />
            )}
          </div>
        )}

        {/* Transactions list ───────────────────────────────────────────── */}
        {activeTab === 'transactions' && (
          <div className="space-y-2">
            {txnsLoading ? (
              <div className="flex justify-center py-12"><Spinner /></div>
            ) : Array.isArray(txns) && txns.length > 0 ? (
              txns.map((txn, i) => (
                <TxnRow key={String((txn as Record<string, unknown>)?.hash ?? (txn as Record<string, unknown>)?.id ?? i)} txn={txn as Record<string, unknown>} i={i} />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-12 h-12 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center mb-3">
                  <Zap className="w-6 h-6 text-vit-400/50" />
                </div>
                <p className="text-white/50 text-sm font-medium mb-1">No transactions yet</p>
                <p className="text-white/25 text-xs">Transactions will appear as users stake, predict, and earn rewards.</p>
              </div>
            )}
          </div>
        )}

        {/* Chain info footer ───────────────────────────────────────────── */}
        <div className="mt-10 pt-6 border-t border-white/6 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: 'Network',      value: 'VIT Mainnet L2' },
            { label: 'Chain ID',     value: String(chainId) },
            { label: 'Consensus',    value: 'Proof-of-Stake + Storage' },
          ].map(({ label, value }) => (
            <div key={label} className="p-4 rounded-xl bg-white/3 border border-white/6">
              <p className="text-xs text-white/30 uppercase tracking-wide mb-1">{label}</p>
              <p className="text-sm font-medium text-white/70">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
