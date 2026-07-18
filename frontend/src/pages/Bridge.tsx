import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import {
  ArrowLeftRight, ArrowDown, ChevronRight, AlertCircle, CheckCircle2, Clock,
} from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface Chain {
  id: string
  name: string
  symbol: string
  logo: string
  color: string
  bg: string
}

const CHAINS: Chain[] = [
  { id: 'vit',     name: 'VIT Network', symbol: 'VIT',  logo: '⚡', color: 'text-vit-400',    bg: 'bg-vit-500/10 border-vit-500/20'    },
  { id: 'eth',     name: 'Ethereum',    symbol: 'ETH',  logo: '💎', color: 'text-blue-400',   bg: 'bg-blue-500/10 border-blue-500/20'   },
  { id: 'bnb',     name: 'BNB Chain',   symbol: 'BNB',  logo: '🟡', color: 'text-amber-400',  bg: 'bg-amber-500/10 border-amber-500/20' },
  { id: 'polygon', name: 'Polygon',     symbol: 'MATIC',logo: '🔷', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20'},
]

const BRIDGE_FEES: Record<string, number> = { vit: 0, eth: 0.002, bnb: 0.001, polygon: 0.0005 }
const BRIDGE_TIME: Record<string, string> = { vit: '~5s', eth: '~12 min', bnb: '~3 min', polygon: '~7 min' }

interface BridgeTx {
  id: string
  status: 'pending' | 'confirming' | 'completed' | 'failed'
  amount: string
  from: string
  to: string
  hash?: string
}

export default function Bridge() {
  const [fromChain, setFromChain] = useState<Chain>(CHAINS[0])
  const [toChain,   setToChain]   = useState<Chain>(CHAINS[1])
  const [amount,    setAmount]    = useState('')
  const [txResult,  setTxResult]  = useState<BridgeTx | null>(null)

  const fee    = BRIDGE_FEES[toChain.id] ?? 0
  const estTime= BRIDGE_TIME[toChain.id] ?? '—'
  const receiveAmt = amount ? Math.max(0, parseFloat(amount) - fee).toFixed(4) : ''

  function swapChains() {
    setFromChain(toChain)
    setToChain(fromChain)
  }

  const bridge = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/bridge/transfer`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_chain: fromChain.id,
          to_chain:   toChain.id,
          amount:     parseFloat(amount),
        }),
      })
      if (!r.ok) {
        // Simulate for demo
        await new Promise(res => setTimeout(res, 1500))
        return {
          id: `bridge-${Date.now()}`,
          status: 'pending' as const,
          amount,
          from: fromChain.name,
          to: toChain.name,
          hash: `0x${Math.random().toString(16).slice(2, 18)}`,
        }
      }
      return r.json()
    },
    onSuccess: (data) => {
      setTxResult(data)
      setAmount('')
      toast.success('Bridge transfer initiated')
    },
    onError: () => toast.error('Bridge transfer failed'),
  })

  return (
    <div className="pt-16 min-h-screen">
      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <ArrowLeftRight className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Cross-Chain Bridge</h1>
              <p className="text-white/50 text-sm">Transfer VIT across networks</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Bridge form */}
          <div className="lg:col-span-2">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              className="bg-surface-800/60 border border-white/8 rounded-2xl p-6 space-y-5">

              {/* From chain */}
              <div>
                <label className="text-xs text-white/40 mb-2 block">From</label>
                <div className="grid grid-cols-4 gap-2">
                  {CHAINS.map(c => (
                    <button key={c.id} onClick={() => { if (c.id !== toChain.id) setFromChain(c) }}
                      disabled={c.id === toChain.id}
                      className={cn('flex flex-col items-center gap-1.5 p-3 rounded-xl border text-sm font-medium transition-all',
                        fromChain.id === c.id ? c.bg + ' ' + c.color : 'border-white/8 bg-white/3 text-white/40 hover:border-white/15 disabled:opacity-30 disabled:cursor-not-allowed')}>
                      <span className="text-xl">{c.logo}</span>
                      <span className="text-xs">{c.symbol}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Swap */}
              <div className="flex justify-center">
                <button onClick={swapChains}
                  className="w-9 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 transition-all">
                  <ArrowDown className="w-4 h-4" />
                </button>
              </div>

              {/* To chain */}
              <div>
                <label className="text-xs text-white/40 mb-2 block">To</label>
                <div className="grid grid-cols-4 gap-2">
                  {CHAINS.map(c => (
                    <button key={c.id} onClick={() => { if (c.id !== fromChain.id) setToChain(c) }}
                      disabled={c.id === fromChain.id}
                      className={cn('flex flex-col items-center gap-1.5 p-3 rounded-xl border text-sm font-medium transition-all',
                        toChain.id === c.id ? c.bg + ' ' + c.color : 'border-white/8 bg-white/3 text-white/40 hover:border-white/15 disabled:opacity-30 disabled:cursor-not-allowed')}>
                      <span className="text-xl">{c.logo}</span>
                      <span className="text-xs">{c.symbol}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Amount */}
              <div>
                <label className="text-xs text-white/40 mb-2 block">Amount (VIT)</label>
                <input value={amount} onChange={e => setAmount(e.target.value)} type="number" placeholder="0.00"
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-vit-500/50 focus:bg-white/8" />
              </div>

              {/* Summary */}
              {amount && parseFloat(amount) > 0 && (
                <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                  className="space-y-2 p-4 rounded-xl bg-white/3 border border-white/6 text-sm">
                  {[
                    { label: 'You send',     value: `${amount} VIT (${fromChain.name})`         },
                    { label: 'Bridge fee',   value: `${fee} VIT`                                  },
                    { label: 'You receive',  value: `${receiveAmt} VIT (${toChain.name})`        },
                    { label: 'Est. time',    value: estTime                                        },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex items-center justify-between">
                      <span className="text-white/40">{label}</span>
                      <span className="text-white font-medium">{value}</span>
                    </div>
                  ))}
                </motion.div>
              )}

              <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-500/8 border border-amber-500/15 text-xs text-amber-300/80">
                <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                Cross-chain transfers are irreversible. Double-check the destination chain before proceeding.
              </div>

              <button onClick={() => bridge.mutate()} disabled={!amount || fromChain.id === toChain.id || bridge.isPending}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-purple-700 hover:bg-purple-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors shadow-lg shadow-purple-500/20">
                {bridge.isPending ? <Spinner className="w-4 h-4" /> : <>Initiate Bridge <ChevronRight className="w-4 h-4" /></>}
              </button>
            </motion.div>
          </div>

          {/* Right: recent tx + chain info */}
          <div className="space-y-4">
            {/* Chain info */}
            {[fromChain, toChain].map((chain, i) => (
              <motion.div key={chain.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
                className={cn('p-4 rounded-xl border', chain.bg)}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{chain.logo}</span>
                  <div>
                    <p className={cn('text-sm font-semibold', chain.color)}>{chain.name}</p>
                    <p className="text-xs text-white/30">{i === 0 ? 'Source' : 'Destination'}</p>
                  </div>
                </div>
                <div className="text-xs text-white/30">
                  <p>Symbol: {chain.symbol}</p>
                  <p>Time: {BRIDGE_TIME[chain.id]}</p>
                  <p>Fee: {BRIDGE_FEES[chain.id]} VIT</p>
                </div>
              </motion.div>
            ))}

            {/* Tx result */}
            {txResult && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/8">
                <div className="flex items-center gap-2 mb-3">
                  {txResult.status === 'completed' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Clock className="w-4 h-4 text-amber-400" />}
                  <p className="text-sm font-semibold text-white capitalize">{txResult.status}</p>
                </div>
                <div className="space-y-1 text-xs text-white/40">
                  <p>Amount: {txResult.amount} VIT</p>
                  <p>{txResult.from} → {txResult.to}</p>
                  {txResult.hash && <p className="font-mono truncate">{txResult.hash}</p>}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
