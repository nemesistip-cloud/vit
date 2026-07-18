import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftRight, Plus, X, RefreshCw, Search,
  ChevronDown, CheckCircle2, Clock, AlertCircle,
} from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface Listing {
  id: number
  seller_username: string
  amount_vit: number
  price_ngn: number
  min_buy?: number
  status: 'open' | 'matched' | 'completed' | 'cancelled'
  created_at: string
}

function useListings() {
  return useQuery<Listing[]>({
    queryKey: ['p2p-listings'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/exchange/listings?status=open`, {
        signal, headers: authHeaders(),
      })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.items ?? []
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

const STATUS_STYLES: Record<string, string> = {
  open:      'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  matched:   'bg-amber-500/10  text-amber-400  border-amber-500/20',
  completed: 'bg-white/5       text-white/30   border-white/10',
  cancelled: 'bg-red-500/10    text-red-400    border-red-500/20',
}

function CreateModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [amount, setAmount]   = useState('')
  const [price,  setPrice]    = useState('')
  const [minBuy, setMinBuy]   = useState('')

  const create = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/exchange/listings`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount_vit: +amount, price_ngn: +price, min_buy: minBuy ? +minBuy : undefined }),
      })
      if (!r.ok) throw new Error('Failed to create listing')
      return r.json()
    },
    onSuccess: () => {
      toast.success('Listing created')
      qc.invalidateQueries({ queryKey: ['p2p-listings'] })
      onClose()
    },
    onError: () => toast.error('Failed to create listing'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-md bg-surface-900 border border-white/12 rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-white/8">
          <h2 className="font-bold text-white">Create P2P Listing</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/8 text-white/40 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-6 space-y-4">
          {[
            { label: 'Amount (VIT)',      value: amount,  set: setAmount,  placeholder: '1000' },
            { label: 'Price per VIT (₦)', value: price,   set: setPrice,   placeholder: '2100' },
            { label: 'Min buy (VIT)',      value: minBuy,  set: setMinBuy,  placeholder: 'Optional' },
          ].map(({ label, value, set, placeholder }) => (
            <div key={label}>
              <label className="text-xs text-white/50 mb-1.5 block">{label}</label>
              <input value={value} onChange={e => set(e.target.value)} type="number" placeholder={placeholder}
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-vit-500/50" />
            </div>
          ))}
          {amount && price && (
            <div className="p-3 rounded-xl bg-emerald-500/8 border border-emerald-500/15 text-sm flex items-center justify-between">
              <span className="text-white/50">Total value</span>
              <span className="font-semibold text-emerald-400">₦{(+amount * +price).toLocaleString()}</span>
            </div>
          )}
          <button onClick={() => create.mutate()} disabled={!amount || !price || create.isPending}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-vit-600 hover:bg-vit-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors">
            {create.isPending ? <Spinner className="w-4 h-4" /> : 'Create Listing'}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default function Exchange() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [searchQ,    setSearchQ]    = useState('')

  const { data: listings = [], isLoading, refetch } = useListings()

  const match = useMutation({
    mutationFn: async (id: number) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/exchange/listings/${id}/match`, {
        method: 'POST', headers: authHeaders(),
      })
      if (!r.ok) throw new Error('Failed to match')
      return r.json()
    },
    onSuccess: () => { toast.success('Trade matched!'); qc.invalidateQueries({ queryKey: ['p2p-listings'] }) },
    onError:   () => toast.error('Failed to match listing'),
  })

  const filtered = listings.filter(l =>
    !searchQ || l.seller_username?.toLowerCase().includes(searchQ.toLowerCase())
  )

  return (
    <div className="pt-16 min-h-screen">
      <AnimatePresence>{showCreate && <CreateModal onClose={() => setShowCreate(false)} />}</AnimatePresence>

      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <ArrowLeftRight className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">P2P Exchange</h1>
                <p className="text-white/50 text-sm">Trade VIT directly with other users</p>
              </div>
            </div>
            <button onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vit-600 hover:bg-vit-500 text-white text-sm font-medium transition-colors shadow-lg shadow-vit-500/20">
              <Plus className="w-4 h-4" /> Create Listing
            </button>
          </motion.div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* Search + refresh */}
        <div className="flex items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/25" />
            <input value={searchQ} onChange={e => setSearchQ(e.target.value)} placeholder="Search seller…"
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-white/20" />
          </div>
          <button onClick={() => refetch()}
            className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-white/40 hover:text-white hover:border-white/20 transition-all">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Table */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-20"><Spinner className="w-6 h-6 text-vit-400" /></div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-2">
              <ArrowLeftRight className="w-10 h-10 text-white/10" />
              <p className="text-white/30 text-sm">No open listings</p>
              <button onClick={() => setShowCreate(true)}
                className="mt-2 flex items-center gap-1.5 px-4 py-2 rounded-lg bg-vit-600/20 border border-vit-500/20 text-vit-400 text-sm hover:bg-vit-600/30 transition-colors">
                <Plus className="w-3.5 h-3.5" /> Create first listing
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/8">
                    {['Seller', 'Amount (VIT)', 'Price/VIT', 'Total (₦)', 'Min Buy', 'Status', ''].map(h => (
                      <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-5 py-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(l => (
                    <tr key={l.id} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                      <td className="px-5 py-3.5 text-white text-sm font-medium">@{l.seller_username}</td>
                      <td className="px-5 py-3.5 text-vit-400 font-semibold">{l.amount_vit?.toLocaleString()}</td>
                      <td className="px-5 py-3.5 text-white/60 text-sm">₦{l.price_ngn?.toLocaleString()}</td>
                      <td className="px-5 py-3.5 text-white/60 text-sm">₦{(l.amount_vit * l.price_ngn)?.toLocaleString()}</td>
                      <td className="px-5 py-3.5 text-white/40 text-sm">{l.min_buy ? `${l.min_buy} VIT` : '—'}</td>
                      <td className="px-5 py-3.5">
                        <span className={cn('text-xs px-2 py-0.5 rounded-full border', STATUS_STYLES[l.status] ?? STATUS_STYLES.cancelled)}>
                          {l.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        {l.status === 'open' && (
                          <button onClick={() => match.mutate(l.id)} disabled={match.isPending}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-vit-600/20 border border-vit-500/20 text-vit-400 text-xs font-medium hover:bg-vit-600/30 transition-colors disabled:opacity-40">
                            {match.isPending ? <Spinner className="w-3 h-3" /> : 'Buy'}
                          </button>
                        )}
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
