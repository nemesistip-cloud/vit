import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Zap, TrendingUp, ArrowUpDown, RefreshCw, ChevronRight,
  DollarSign, Globe, BarChart2,
} from 'lucide-react'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'

function useVITPrice() {
  return useQuery({
    queryKey: ['vitcoin-price'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/vitcoin-price`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}

function useVITPriceHistory() {
  return useQuery({
    queryKey: ['vitcoin-history'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/vitcoin/price-history?days=30`, { signal, headers: authHeaders() })
      if (!r.ok) {
        // Synthetic fallback chart data
        const base = 0.00042
        return Array.from({ length: 30 }, (_, i) => ({
          day: `Day ${i + 1}`,
          price: +(base + (Math.random() - 0.46) * 0.00008).toFixed(7),
        }))
      }
      return r.json()
    },
    staleTime: 5 * 60_000,
  })
}

function useWalletBalance() {
  return useQuery({
    queryKey: ['wallet'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/me`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false,
    staleTime: 60_000,
  })
}

const CURRENCIES = [
  { code: 'NGN', symbol: '₦',  rate: 1 },
  { code: 'USD', symbol: '$',  rate: 0.00065 },
  { code: 'EUR', symbol: '€',  rate: 0.00060 },
  { code: 'GBP', symbol: '£',  rate: 0.00052 },
]

export default function VITCoin() {
  const { data: price,   isLoading: loadingPrice } = useVITPrice()
  const { data: history, isLoading: loadingChart } = useVITPriceHistory()
  const { data: wallet }                            = useWalletBalance()

  const [tab,        setTab]        = useState<'buy' | 'sell'>('buy')
  const [amount,     setAmount]     = useState('')
  const [currency,   setCurrency]   = useState('NGN')
  const [submitting, setSubmitting] = useState(false)

  const balance = parseFloat(wallet?.vit_balance ?? wallet?.balance ?? '0') || 0
  const priceNGN = price?.price_ngn ?? 2100
  const priceUSD = price?.price_usd ?? 0.00136

  const cur = CURRENCIES.find(c => c.code === currency) ?? CURRENCIES[0]
  const fiatAmount = parseFloat(amount) || 0
  const vitAmount  = tab === 'buy'
    ? fiatAmount / (priceNGN * cur.rate)
    : fiatAmount * priceNGN * cur.rate

  async function submit() {
    if (!amount) return
    setSubmitting(true)
    await new Promise(r => setTimeout(r, 1200))
    setSubmitting(false)
    setAmount('')
  }

  const chartData: any[] = history ?? []

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">VITCoin</h1>
              <p className="text-white/50 text-sm">Buy, sell, and convert VIT tokens</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Left: price + chart */}
          <div className="lg:col-span-2 space-y-4">
            {/* Price cards */}
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { label: 'VIT / NGN',  value: loadingPrice ? null : `₦${priceNGN?.toLocaleString() ?? '—'}`,         icon: Globe,       color: 'text-vit-400'     },
                { label: 'VIT / USD',  value: loadingPrice ? null : `$${priceUSD?.toFixed(6) ?? '—'}`,                icon: DollarSign,  color: 'text-emerald-400' },
                { label: '24h Change', value: price?.change_24h != null ? `${price.change_24h >= 0 ? '+' : ''}${price.change_24h.toFixed(2)}%` : '—', icon: TrendingUp, color: price?.change_24h >= 0 ? 'text-emerald-400' : 'text-red-400' },
              ].map(({ label, value, icon: Icon, color }, i) => (
                <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                  className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={cn('w-4 h-4', color)} />
                    <p className="text-xs text-white/40">{label}</p>
                  </div>
                  {value == null ? <Spinner className="w-4 h-4 text-vit-400" /> : (
                    <p className={cn('text-2xl font-bold', color)}>{value}</p>
                  )}
                </motion.div>
              ))}
            </div>

            {/* Price chart */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-vit-400" />
                  <p className="text-sm font-semibold text-white">30-Day Price</p>
                </div>
              </div>
              {loadingChart ? (
                <div className="h-48 flex items-center justify-center"><Spinner className="w-5 h-5 text-vit-400" /></div>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={chartData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="vitGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#7c3aed" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="day" tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 10 }} axisLine={false} tickLine={false} width={60} tickFormatter={v => `₦${(v * 1000).toFixed(2)}`} />
                    <Tooltip
                      contentStyle={{ background: '#1a1625', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: 'rgba(255,255,255,0.5)' }}
                      formatter={(v: any) => [`₦${Number(v * 1000).toFixed(4)}`, 'Price']}
                    />
                    <Area type="monotone" dataKey="price" stroke="#7c3aed" strokeWidth={2} fill="url(#vitGrad)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </motion.div>

            {/* Currency converter */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
              className="bg-surface-800/60 border border-white/8 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <ArrowUpDown className="w-4 h-4 text-white/40" />
                <p className="text-sm font-semibold text-white">Currency Converter</p>
              </div>
              <div className="grid sm:grid-cols-4 gap-3">
                {CURRENCIES.map(c => {
                  const vitInFiat = 1 / (priceNGN * c.rate)
                  const fiatInVit = priceNGN * c.rate
                  return (
                    <div key={c.code} className="bg-white/3 border border-white/6 rounded-xl p-3 text-center">
                      <p className="text-xs text-white/40 mb-1">{c.code}</p>
                      <p className="text-sm font-semibold text-white">{c.symbol}{fiatInVit.toFixed(4)}</p>
                      <p className="text-xs text-white/25 mt-0.5">per VIT</p>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          </div>

          {/* Right: buy/sell form */}
          <div>
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
              className="bg-surface-800/60 border border-white/8 rounded-xl p-6 sticky top-24">
              {/* Tab */}
              <div className="flex gap-1 mb-5 bg-white/5 rounded-xl p-1">
                {(['buy', 'sell'] as const).map(t => (
                  <button key={t} onClick={() => setTab(t)}
                    className={cn('flex-1 py-2 rounded-lg text-sm font-medium capitalize transition-all',
                      tab === t ? 'bg-vit-600 text-white shadow-lg shadow-vit-500/20' : 'text-white/40 hover:text-white/60')}>
                    {t}
                  </button>
                ))}
              </div>

              {/* Balance */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-vit-500/8 border border-vit-500/15 mb-5">
                <p className="text-xs text-white/40">VIT Balance</p>
                <p className="text-sm font-bold text-vit-400">{balance.toLocaleString()} VIT</p>
              </div>

              {/* Amount */}
              <div className="space-y-3 mb-5">
                <div>
                  <label className="text-xs text-white/40 mb-1.5 block">{tab === 'buy' ? 'Pay' : 'Sell amount (VIT)'}</label>
                  <div className="flex gap-2">
                    <input value={amount} onChange={e => setAmount(e.target.value)} type="number" placeholder="0.00"
                      className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-vit-500/50" />
                    {tab === 'buy' && (
                      <select value={currency} onChange={e => setCurrency(e.target.value)}
                        className="px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none">
                        {CURRENCIES.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
                      </select>
                    )}
                  </div>
                </div>

                {fiatAmount > 0 && (
                  <div className="flex items-center justify-between p-3 rounded-xl bg-white/3 border border-white/6 text-sm">
                    <span className="text-white/40">{tab === 'buy' ? 'You receive' : 'You receive'}</span>
                    <span className="font-semibold text-white">
                      {tab === 'buy'
                        ? `${vitAmount.toFixed(4)} VIT`
                        : `${cur.symbol}${vitAmount.toFixed(2)}`}
                    </span>
                  </div>
                )}
              </div>

              <button onClick={submit} disabled={!amount || submitting}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-vit-600 hover:bg-vit-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors shadow-lg shadow-vit-500/20">
                {submitting ? <Spinner className="w-4 h-4" /> : (
                  <>{tab === 'buy' ? 'Buy VIT' : 'Sell VIT'} <ChevronRight className="w-4 h-4" /></>
                )}
              </button>

              <p className="text-center text-xs text-white/20 mt-3">Powered by VIT Network DEX</p>
            </motion.div>
          </div>

        </div>
      </div>
    </div>
  )
}
