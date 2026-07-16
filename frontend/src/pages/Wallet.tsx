import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Wallet as WalletIcon, Send, Download, ArrowUpRight, ArrowDownLeft,
  TrendingUp, TrendingDown, Copy, RefreshCw, Lock, Zap, ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { getAuthToken, authHeaders } from '@/hooks/useAuth'

function useWallet() {
  return useQuery({
    queryKey: ['wallet'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/me`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false, staleTime: 60_000,
  })
}

function useWalletPrice() {
  return useQuery({
    queryKey: ['vit-price'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/dashboard/vitcoin-price`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    staleTime: 30_000, refetchInterval: 30_000,
  })
}

function useTransactions() {
  return useQuery({
    queryKey: ['wallet-txs'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/transactions?limit=20`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.transactions ?? d.items ?? []
    },
    retry: false, staleTime: 60_000,
  })
}

function ComingSoonOverlay({ label }: { label: string }) {
  return (
    <div className="absolute inset-0 rounded-xl flex flex-col items-center justify-center bg-surface-900/80 backdrop-blur-sm z-10">
      <Lock className="w-6 h-6 text-white/30 mb-2" />
      <p className="text-sm text-white/40 font-medium">{label}</p>
      <p className="text-xs text-white/20 mt-1">Coming soon</p>
    </div>
  )
}

export default function Wallet() {
  const navigate = useNavigate()
  const token    = getAuthToken()

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const { data: wallet }  = useWallet()
  const { data: price }   = useWalletPrice()
  const { data: txs }     = useTransactions()
  const [copied, setCopied] = useState(false)

  function copyAddress() {
    if (wallet?.address) {
      navigator.clipboard.writeText(wallet.address)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (!token) return <div className="pt-16 min-h-screen flex items-center justify-center"><Spinner className="w-8 h-8 text-vit-400" /></div>

  return (
    <div className="pt-16 min-h-screen">
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <WalletIcon className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Wallet</h1>
              <p className="text-white/50 text-sm">Manage your VITCoin and on-chain assets</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Balance card */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="relative rounded-2xl border border-white/10 bg-gradient-to-br from-vit-500/10 via-surface-800 to-surface-800/60 p-8 overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-vit-500/5 -translate-y-1/2 translate-x-1/2" />
          <div className="relative">
            <p className="text-white/50 text-sm mb-1">Total Balance</p>
            <div className="flex items-end gap-3 mb-2">
              <span className="text-5xl font-bold text-white">
                {wallet?.balance ?? wallet?.vit_balance ?? '0'}
              </span>
              <span className="text-xl text-vit-400 font-medium mb-1">VIT</span>
            </div>
            {price?.price_usd != null && (
              <p className="text-white/40 text-sm mb-4">
                ≈ ${((wallet?.balance ?? 0) * price.price_usd).toFixed(2)} USD
                <span className={cn('ml-2 text-xs font-medium', price.change_24h >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                  {price.change_24h >= 0 ? '+' : ''}{price.change_24h?.toFixed(2)}% (24h)
                </span>
              </p>
            )}
            {wallet?.address && (
              <button onClick={copyAddress}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-white/50 hover:text-white hover:bg-white/10 transition-colors">
                <span className="font-mono">{wallet.address.slice(0, 12)}…{wallet.address.slice(-6)}</span>
                <Copy className="w-3 h-3" />
                {copied && <span className="text-emerald-400">Copied!</span>}
              </button>
            )}
          </div>
        </motion.div>

        {/* Quick actions */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { icon: Send, label: 'Send', color: 'text-vit-400', bg: 'bg-vit-500/10 border-vit-500/20' },
            { icon: Download, label: 'Receive', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
            { icon: Zap, label: 'Stake', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
            { icon: ArrowUpRight, label: 'Bridge', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
          ].map(({ icon: Icon, label, color, bg }) => (
            <div key={label} className="relative">
              <button className={`w-full flex flex-col items-center gap-2 p-5 rounded-xl border ${bg} hover:brightness-110 transition-all opacity-60`}>
                <Icon className={`w-6 h-6 ${color}`} />
                <span className="text-sm font-medium text-white">{label}</span>
              </button>
              <ComingSoonOverlay label={label} />
            </div>
          ))}
        </div>

        {/* Price info */}
        {price && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'VIT / USD', value: price.price_usd ? `$${price.price_usd.toFixed(4)}` : '—' },
              { label: 'VIT / NGN', value: price.price_ngn ? `₦${price.price_ngn.toFixed(2)}` : '—' },
              { label: '24h Volume', value: price.volume_24h ? `$${(price.volume_24h / 1e6).toFixed(2)}M` : '—' },
              { label: 'Market Cap', value: price.market_cap ? `$${(price.market_cap / 1e6).toFixed(1)}M` : '—' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-surface-800/60 border border-white/8 rounded-xl p-4">
                <p className="text-xs text-white/40 mb-1">{label}</p>
                <p className="text-lg font-bold text-white">{value}</p>
              </div>
            ))}
          </motion.div>
        )}

        {/* Transaction history */}
        <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-white/8">
            <h2 className="font-semibold text-white">Transaction History</h2>
            <RefreshCw className="w-4 h-4 text-white/30 cursor-pointer hover:text-white/60" />
          </div>
          {!txs || txs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <WalletIcon className="w-12 h-12 text-white/10 mb-3" />
              <p className="text-white/40">No transactions yet</p>
              <p className="text-white/25 text-sm mt-1">Your transaction history will appear here</p>
            </div>
          ) : (
            <div>
              {txs.map((tx: any, i: number) => {
                const isOut = tx.type === 'sent' || tx.amount < 0
                return (
                  <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${isOut ? 'bg-red-500/10' : 'bg-emerald-500/10'}`}>
                      {isOut ? <ArrowUpRight className="w-4 h-4 text-red-400" /> : <ArrowDownLeft className="w-4 h-4 text-emerald-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white capitalize">{tx.type || (isOut ? 'Sent' : 'Received')}</p>
                      {tx.to && <p className="text-xs text-white/30 truncate font-mono">{tx.to}</p>}
                      {tx.created_at && <p className="text-xs text-white/25">{new Date(tx.created_at).toLocaleString()}</p>}
                    </div>
                    <span className={`text-sm font-bold ${isOut ? 'text-red-400' : 'text-emerald-400'}`}>
                      {isOut ? '-' : '+'}{Math.abs(tx.amount || 0)} VIT
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
