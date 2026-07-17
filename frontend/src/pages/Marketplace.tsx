import { useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Store, Search, Star, Zap, Shield, TrendingUp, Users, ArrowUpRight,
  ChevronRight, Plus, X, CheckCircle2, Clock, AlertCircle, Code2,
  BarChart3, Package, Repeat2, DollarSign, Filter, BadgeCheck,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ModelListing {
  id: number
  name: string
  slug: string
  description: string
  category: string
  price_per_call: string
  model_key: string | null
  gcs_uri: string | null
  is_active: boolean
}

interface ModelDetail extends ModelListing {
  approval_status: string
  is_verified: boolean
  usage_count: number
  rating_avg: number | null
  rating_count: number
  total_staked: string
  staker_count: number
  total_revenue: string
  creator_revenue: string
  tags: string | null
}

interface MarketStats {
  active_models: number
  total_calls: number
  top_category: string
  categories: Record<string, number>
  protocol_fee_pct: number
}

interface P2POffer {
  id: string | number
  offer_type: 'buy' | 'sell'
  asset: string
  amount: number | string
  price_per_unit: number | string
  min_order: number | string
  max_order: number | string
  payment_methods: string[]
  status: string
  created_at?: string
  username?: string
}

// ── API hooks ─────────────────────────────────────────────────────────────────

function useMarketStats() {
  return useQuery<MarketStats>({
    queryKey: ['market-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/marketplace/stats`, { signal })
      if (!r.ok) throw new Error('Failed to load stats')
      return r.json()
    },
    staleTime: 60_000,
  })
}

function useModels(category: string) {
  return useQuery<ModelListing[]>({
    queryKey: ['marketplace-models', category],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/marketplace/models`, { signal })
      if (!r.ok) throw new Error('Failed to load models')
      const all: ModelListing[] = await r.json()
      return category === 'all' ? all : all.filter(m => m.category === category)
    },
    staleTime: 30_000,
  })
}

function useModelDetail(slug: string | null) {
  return useQuery<ModelDetail>({
    queryKey: ['model-detail', slug],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/marketplace/models/${slug}`, { signal })
      if (!r.ok) throw new Error('Model not found')
      return r.json()
    },
    enabled: !!slug,
  })
}

function useMyListings(enabled: boolean) {
  return useQuery<ModelListing[]>({
    queryKey: ['my-listings'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/marketplace/my-listings`, { signal, headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load your listings')
      return r.json()
    },
    enabled,
  })
}

function useP2POffers() {
  return useQuery<P2POffer[]>({
    queryKey: ['p2p-offers'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/wallet/p2p/offers`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const data = await r.json()
      return Array.isArray(data) ? data : (data.offers ?? [])
    },
    staleTime: 20_000,
  })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const CATEGORIES = ['all', 'prediction', 'analysis', 'arbitrage', 'nlp', 'scoring'] as const

const CATEGORY_COLORS: Record<string, string> = {
  prediction: 'bg-vit-400/15 text-vit-300 border-vit-400/20',
  analysis:   'bg-blue-400/15 text-blue-300 border-blue-400/20',
  arbitrage:  'bg-amber-400/15 text-amber-300 border-amber-400/20',
  nlp:        'bg-purple-400/15 text-purple-300 border-purple-400/20',
  scoring:    'bg-green-400/15 text-green-300 border-green-400/20',
}

const OFFER_TYPE_STYLES = {
  buy:  { pill: 'bg-green-400/10 text-green-300 border-green-400/20', label: 'BUY'  },
  sell: { pill: 'bg-red-400/10 text-red-300 border-red-400/20',       label: 'SELL' },
}

const APPROVAL_STYLES: Record<string, { pill: string; icon: ReactNode }> = {
  pending:   { pill: 'bg-amber-400/10 text-amber-300',  icon: <Clock className="w-3 h-3" /> },
  approved:  { pill: 'bg-green-400/10 text-green-300',  icon: <CheckCircle2 className="w-3 h-3" /> },
  rejected:  { pill: 'bg-red-400/10 text-red-300',      icon: <X className="w-3 h-3" /> },
  suspended: { pill: 'bg-white/10 text-white/40',       icon: <AlertCircle className="w-3 h-3" /> },
}

function catPill(cat: string) {
  return CATEGORY_COLORS[cat] ?? 'bg-white/10 text-white/50 border-white/10'
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub }: { icon: ReactNode; label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-start gap-3">
      <div className="p-2 bg-vit-400/10 rounded-lg text-vit-400">{icon}</div>
      <div>
        <p className="text-xs text-white/40 mb-0.5">{label}</p>
        <p className="text-lg font-bold text-white">{value}</p>
        {sub && <p className="text-xs text-white/30 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function ModelCard({ model, onSelect }: { model: ModelListing; onSelect: (slug: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/5 border border-white/10 rounded-xl p-5 hover:border-vit-400/40 hover:bg-white/[0.07] transition-all cursor-pointer group"
      onClick={() => onSelect(model.slug)}
    >
      <div className="flex items-start justify-between mb-3">
        <span className={cn('text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border', catPill(model.category))}>
          {model.category}
        </span>
        {model.is_active && <BadgeCheck className="w-4 h-4 text-vit-400" />}
      </div>
      <h3 className="font-semibold text-white mb-1 group-hover:text-vit-300 transition-colors line-clamp-1">{model.name}</h3>
      <p className="text-sm text-white/50 line-clamp-2 mb-4">{model.description || 'No description provided.'}</p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 text-vit-400 font-mono text-sm">
          <Zap className="w-3.5 h-3.5" />{model.price_per_call} VIT / call
        </div>
        <button className="flex items-center gap-1 text-xs text-white/50 group-hover:text-vit-300 transition-colors">
          Details <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </motion.div>
  )
}

function ModelDetailModal({ slug, onClose }: { slug: string; onClose: () => void }) {
  const { data: model, isLoading } = useModelDetail(slug)
  const navigate = useNavigate()
  const isAuth = !!getAuthToken()
  const [callInput, setCallInput] = useState('{}')
  const [callResult, setCallResult] = useState<string | null>(null)
  const [showCall, setShowCall] = useState(false)

  const callMutation = useMutation({
    mutationFn: async () => {
      let parsed: Record<string, unknown> = {}
      try { parsed = JSON.parse(callInput) } catch { throw new Error('Invalid JSON input') }
      const r = await fetch(`${ENDPOINTS.gateway}/api/marketplace/models/${slug}/call`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_data: parsed }),
      })
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as { detail?: string }).detail ?? 'Call failed') }
      return r.json()
    },
    onSuccess: (data) => setCallResult(JSON.stringify(data, null, 2)),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative bg-[#0d0f1a] border border-white/15 rounded-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto shadow-2xl"
      >
        <div className="p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12"><Spinner className="w-8 h-8" /></div>
          ) : !model ? (
            <p className="text-center text-white/40 py-12">Model not found.</p>
          ) : (
            <>
              <div className="flex items-start justify-between mb-5">
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={cn('text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border', catPill(model.category))}>
                      {model.category}
                    </span>
                    {model.is_verified && (
                      <span className="flex items-center gap-1 text-[10px] text-vit-400 bg-vit-400/10 px-2 py-0.5 rounded-full border border-vit-400/20">
                        <BadgeCheck className="w-3 h-3" /> Verified
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold text-white">{model.name}</h2>
                  {model.tags && <p className="text-xs text-white/30 mt-1">{model.tags.split(',').map(t => `#${t.trim()}`).join(' ')}</p>}
                </div>
                <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-white transition-colors flex-shrink-0">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <p className="text-sm text-white/60 mb-5 leading-relaxed">{model.description || 'No description provided.'}</p>

              <div className="grid grid-cols-2 gap-3 mb-5">
                {[
                  { label: 'Price per Call', value: <span className="font-mono font-bold text-vit-300">{model.price_per_call} VIT</span> },
                  { label: 'Total Calls',    value: model.usage_count.toLocaleString() },
                  { label: 'Rating',         value: model.rating_avg != null ? (
                    <span className="flex items-center gap-1"><Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />{model.rating_avg} <span className="text-white/30 text-xs">({model.rating_count})</span></span>
                  ) : '—' },
                  { label: 'Staked VIT',     value: parseFloat(model.total_staked).toLocaleString() },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-white/5 rounded-xl p-3 border border-white/10">
                    <p className="text-xs text-white/40 mb-1">{label}</p>
                    <p className="font-bold text-white text-sm">{value}</p>
                  </div>
                ))}
              </div>

              {!showCall ? (
                isAuth ? (
                  <button onClick={() => setShowCall(true)}
                    className="w-full py-3 bg-vit-400 hover:bg-vit-300 text-black font-semibold rounded-xl transition-colors flex items-center justify-center gap-2">
                    <Zap className="w-4 h-4" /> Use This Model
                  </button>
                ) : (
                  <button onClick={() => { onClose(); navigate('/login') }}
                    className="w-full py-3 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-xl transition-colors">
                    Sign in to use this model
                  </button>
                )
              ) : (
                <div>
                  <div className="h-px bg-white/10 mb-4" />
                  <p className="text-sm font-semibold text-white mb-2">Input (JSON)</p>
                  <textarea
                    value={callInput}
                    onChange={e => setCallInput(e.target.value)}
                    rows={4}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-vit-400/50 resize-none mb-3"
                    placeholder='{ "match_id": 123 }'
                  />
                  {callMutation.error && <p className="text-red-400 text-sm mb-3">{(callMutation.error as Error).message}</p>}
                  {callResult && <pre className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-vit-300 font-mono overflow-x-auto mb-3">{callResult}</pre>}
                  <div className="flex gap-3">
                    <button onClick={() => callMutation.mutate()} disabled={callMutation.isPending}
                      className="flex-1 py-2.5 bg-vit-400 hover:bg-vit-300 text-black font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60">
                      {callMutation.isPending ? <Spinner className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                      Run · {model.price_per_call} VIT
                    </button>
                    <button onClick={() => { setShowCall(false); setCallResult(null) }}
                      className="px-4 py-2.5 bg-white/10 hover:bg-white/15 text-white/70 rounded-xl transition-colors">
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </motion.div>
    </div>
  )
}

function P2POfferRow({ offer }: { offer: P2POffer }) {
  const style = OFFER_TYPE_STYLES[offer.offer_type] ?? OFFER_TYPE_STYLES.sell
  return (
    <div className="flex items-center gap-4 px-4 py-3.5 hover:bg-white/5 transition-colors rounded-xl">
      <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full border w-12 text-center', style.pill)}>{style.label}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{Number(offer.amount).toLocaleString()} {offer.asset}</p>
        <p className="text-xs text-white/40">{Number(offer.price_per_unit).toFixed(4)} USDT/VIT · min {Number(offer.min_order).toLocaleString()} max {Number(offer.max_order).toLocaleString()}</p>
      </div>
      <div className="text-right hidden sm:block">
        <p className="text-xs text-white/40">{(offer.payment_methods ?? []).join(', ') || 'Any'}</p>
        {offer.username && <p className="text-xs text-white/30">{offer.username}</p>}
      </div>
      <button className="px-3 py-1.5 text-xs font-semibold bg-vit-400/10 hover:bg-vit-400/20 text-vit-300 border border-vit-400/20 rounded-lg transition-colors whitespace-nowrap">
        Trade
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'browse', label: 'Browse Models', icon: <Store className="w-4 h-4" /> },
  { id: 'mine',   label: 'My Listings',   icon: <Package className="w-4 h-4" /> },
  { id: 'p2p',    label: 'P2P Trading',   icon: <Repeat2 className="w-4 h-4" /> },
] as const

type Tab = typeof TABS[number]['id']

export default function Marketplace() {
  const [tab, setTab]               = useState<Tab>('browse')
  const [category, setCategory]     = useState('all')
  const [search, setSearch]         = useState('')
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const isAuth = !!getAuthToken()

  const { data: stats, isLoading: statsLoading }   = useMarketStats()
  const { data: models = [], isLoading: modelsLoading } = useModels(category)
  const { data: myListings = [], isLoading: myLoading } = useMyListings(tab === 'mine' && isAuth)
  const { data: p2pOffers = [], isLoading: p2pLoading } = useP2POffers()

  const filtered = models.filter(m =>
    !search || m.name.toLowerCase().includes(search.toLowerCase()) ||
    (m.description ?? '').toLowerCase().includes(search.toLowerCase())
  )

  const buyOffers  = p2pOffers.filter(o => o.offer_type === 'buy')
  const sellOffers = p2pOffers.filter(o => o.offer_type === 'sell')

  return (
    <div className="min-h-screen bg-[#07090f] text-white pt-20 pb-16">
      {selectedSlug && <ModelDetailModal slug={selectedSlug} onClose={() => setSelectedSlug(null)} />}

      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-vit-400 text-sm font-semibold mb-3">
            <Store className="w-4 h-4" /> AI Marketplace
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">Decentralised Intelligence</h1>
          <p className="text-white/50 max-w-xl">Trade, deploy, and profit from AI prediction models. 15% protocol fee fuels the DAO treasury.</p>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {statsLoading ? (
            <div className="col-span-4 flex justify-center py-6"><Spinner className="w-6 h-6" /></div>
          ) : stats ? (
            <>
              <StatCard icon={<Store className="w-4 h-4" />}      label="Active Models"   value={stats.active_models}               sub="approved & live" />
              <StatCard icon={<Zap className="w-4 h-4" />}         label="Total API Calls" value={stats.total_calls.toLocaleString()} sub="all time" />
              <StatCard icon={<TrendingUp className="w-4 h-4" />}  label="Top Category"    value={stats.top_category}                sub="by model count" />
              <StatCard icon={<DollarSign className="w-4 h-4" />}  label="Protocol Fee"    value={`${stats.protocol_fee_pct}%`}      sub="to DAO treasury" />
            </>
          ) : null}
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1 mb-6 w-fit">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                tab === t.id ? 'bg-vit-400 text-black shadow-sm' : 'text-white/50 hover:text-white hover:bg-white/5')}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* ── Browse ── */}
        {tab === 'browse' && (
          <div>
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search models…"
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-vit-400/50" />
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Filter className="w-4 h-4 text-white/30" />
                {CATEGORIES.map(c => (
                  <button key={c} onClick={() => setCategory(c)}
                    className={cn('px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
                      category === c ? 'bg-vit-400 text-black border-vit-400' : 'bg-white/5 text-white/50 border-white/10 hover:border-white/30 hover:text-white')}>
                    {c === 'all' ? 'All' : c.charAt(0).toUpperCase() + c.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {modelsLoading ? (
              <div className="flex items-center justify-center py-20"><Spinner className="w-8 h-8" /></div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-20 text-white/30">
                <Store className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No models found{search ? ` for "${search}"` : ''}.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map(m => <ModelCard key={m.id} model={m} onSelect={setSelectedSlug} />)}
              </div>
            )}
          </div>
        )}

        {/* ── My Listings ── */}
        {tab === 'mine' && (
          <div>
            {!isAuth ? (
              <div className="text-center py-20 text-white/40">
                <Package className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>Sign in to manage your model listings.</p>
              </div>
            ) : myLoading ? (
              <div className="flex items-center justify-center py-20"><Spinner className="w-8 h-8" /></div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-white/50 text-sm">{myListings.length} listing{myListings.length !== 1 ? 's' : ''}</p>
                  <button className="flex items-center gap-2 px-4 py-2 bg-vit-400/10 hover:bg-vit-400/20 text-vit-300 border border-vit-400/20 rounded-xl text-sm font-medium transition-colors">
                    <Plus className="w-4 h-4" /> Submit a Model
                  </button>
                </div>
                {myListings.length === 0 ? (
                  <div className="text-center py-16 bg-white/[0.03] border border-white/10 rounded-2xl">
                    <Package className="w-10 h-10 mx-auto mb-3 opacity-30 text-white" />
                    <p className="text-white/40 mb-2">No listings yet.</p>
                    <p className="text-sm text-white/30">Submit a model to earn VIT on every API call.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {myListings.map(m => {
                      const statusKey = (m as ModelDetail).approval_status ?? 'pending'
                      const style = APPROVAL_STYLES[statusKey] ?? APPROVAL_STYLES.pending
                      return (
                        <div key={m.id} className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center gap-4">
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-white line-clamp-1">{m.name}</p>
                            <p className="text-xs text-white/40 mt-0.5">{m.category} · {m.price_per_call} VIT/call</p>
                          </div>
                          <span className={cn('flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full', style.pill)}>
                            {style.icon}{statusKey.charAt(0).toUpperCase() + statusKey.slice(1)}
                          </span>
                          <button onClick={() => setSelectedSlug(m.slug)}
                            className="p-2 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                            <ArrowUpRight className="w-4 h-4" />
                          </button>
                        </div>
                      )
                    })}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── P2P Trading ── */}
        {tab === 'p2p' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-white">Peer-to-Peer VIT Trading</h2>
                <p className="text-sm text-white/40 mt-0.5">Trade VIT directly with other users via escrow</p>
              </div>
              {isAuth && (
                <button className="flex items-center gap-2 px-4 py-2 bg-vit-400/10 hover:bg-vit-400/20 text-vit-300 border border-vit-400/20 rounded-xl text-sm font-medium transition-colors">
                  <Plus className="w-4 h-4" /> Create Offer
                </button>
              )}
            </div>

            {p2pLoading ? (
              <div className="flex items-center justify-center py-20"><Spinner className="w-8 h-8" /></div>
            ) : p2pOffers.length === 0 ? (
              <div className="text-center py-20 text-white/40">
                <Repeat2 className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No open offers. Be the first to create one.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {[{ label: 'Buy Orders', offers: buyOffers, color: 'bg-green-400' }, { label: 'Sell Orders', offers: sellOffers, color: 'bg-red-400' }].map(({ label, offers, color }) => (
                  <div key={label} className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10">
                      <div className={cn('w-2 h-2 rounded-full', color)} />
                      <p className="text-sm font-semibold text-white">{label}</p>
                      <span className="ml-auto text-xs text-white/30">{offers.length} offers</span>
                    </div>
                    <div className="divide-y divide-white/5">
                      {offers.length === 0
                        ? <p className="text-center text-white/30 text-sm py-8">No {label.toLowerCase()}</p>
                        : offers.map(o => <P2POfferRow key={o.id} offer={o} />)}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 bg-white/[0.03] border border-white/10 rounded-2xl p-4">
              {[
                { icon: <Shield className="w-4 h-4 text-vit-400" />,   title: 'Escrow Protected',   desc: 'VIT held in smart contract until payment confirmed' },
                { icon: <Users className="w-4 h-4 text-vit-400" />,    title: 'Dispute Resolution', desc: 'DAO arbitrators resolve contested trades' },
                { icon: <BarChart3 className="w-4 h-4 text-vit-400" />, title: '0% Fee',            desc: 'No platform fee on P2P trades during Phase VI' },
                { icon: <Code2 className="w-4 h-4 text-vit-400" />,    title: 'Commerce API',       desc: 'Full REST API for automated P2P trading bots' },
              ].map(({ icon, title, desc }) => (
                <div key={title} className="flex items-start gap-2 text-sm">
                  <div className="mt-0.5 flex-shrink-0">{icon}</div>
                  <div>
                    <p className="font-medium text-white">{title}</p>
                    <p className="text-white/40 text-xs mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
