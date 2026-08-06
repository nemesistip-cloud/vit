import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Wallet as WalletIcon, Send, Download, ArrowUpRight, ArrowDownLeft,
  TrendingUp, Copy, RefreshCw, Zap, ChevronRight, X,
  Shield, CheckCircle2, Clock, AlertCircle, ArrowRightLeft,
  Lock, Star, Layers,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { getAuthToken, authHeaders } from '@/hooks/useAuth'

// ── Data hooks ────────────────────────────────────────────────────────────────

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

function useStakingInfo() {
  return useQuery({
    queryKey: ['wallet-staking'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/staking`, { signal, headers: authHeaders() })
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
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/transactions?limit=30`, { signal, headers: authHeaders() })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.transactions ?? d.items ?? []
    },
    retry: false, staleTime: 60_000,
  })
}

function useKYCStatus() {
  return useQuery({
    queryKey: ['kyc-status'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/kyc/status`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    retry: false, staleTime: 300_000,
  })
}

// ── Tier config ───────────────────────────────────────────────────────────────

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string; limit: string }> = {
  viewer:   { label: 'Viewer',  color: 'text-white/50',    bg: 'bg-white/5',         limit: '$100/day'    },
  analyst:  { label: 'Analyst', color: 'text-blue-400',    bg: 'bg-blue-500/10',     limit: '$500/day'    },
  pro:      { label: 'Pro',     color: 'text-vit-400',     bg: 'bg-vit-500/10',      limit: '$500/day'    },
  elite:    { label: 'Elite',   color: 'text-amber-400',   bg: 'bg-amber-500/10',    limit: 'Unlimited'   },
  admin:    { label: 'Admin',   color: 'text-purple-400',  bg: 'bg-purple-500/10',   limit: 'Unlimited'   },
}

// ── Modal wrapper ─────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
        <motion.div
          className="absolute inset-0 bg-black/70 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
        />
        <motion.div
          className="relative w-full max-w-md bg-surface-800 border border-white/10 rounded-2xl p-6 shadow-2xl z-10"
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 24 }}
        >
          <div className="flex items-center justify-between mb-5">
            <h3 className="font-bold text-white text-lg">{title}</h3>
            <button onClick={onClose} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors">
              <X className="w-4 h-4 text-white/60" />
            </button>
          </div>
          {children}
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

// ── Send modal ────────────────────────────────────────────────────────────────

function SendModal({ onClose, balance }: { onClose: () => void; balance: number }) {
  const [recipient, setRecipient] = useState('')
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/send`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient_address: recipient, amount: parseFloat(amount), note }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Send failed')
      return d
    },
    onSuccess: () => {
      setResult({ ok: true, msg: 'Transfer submitted successfully.' })
      qc.invalidateQueries({ queryKey: ['wallet'] })
      qc.invalidateQueries({ queryKey: ['wallet-txs'] })
    },
    onError: (e: Error) => setResult({ ok: false, msg: e.message }),
  })

  return (
    <Modal title="Send VIT" onClose={onClose}>
      {result ? (
        <div className={`flex flex-col items-center gap-3 py-6 text-center ${result.ok ? 'text-emerald-400' : 'text-red-400'}`}>
          {result.ok ? <CheckCircle2 className="w-12 h-12" /> : <AlertCircle className="w-12 h-12" />}
          <p className="font-medium">{result.msg}</p>
          <button onClick={onClose} className="mt-2 px-6 py-2 rounded-lg bg-white/10 text-white text-sm hover:bg-white/15 transition-colors">Close</button>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Recipient Address or Username</label>
            <input
              value={recipient} onChange={e => setRecipient(e.target.value)}
              placeholder="0x... or @username"
              className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50 font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Amount (VIT) — Balance: {balance.toLocaleString()} VIT</label>
            <div className="relative">
              <input
                type="number" value={amount} onChange={e => setAmount(e.target.value)}
                placeholder="0.00" min="0" max={balance}
                className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50"
              />
              <button onClick={() => setAmount(String(balance))} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-vit-400 hover:text-vit-300">MAX</button>
            </div>
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Note (optional)</label>
            <input
              value={note} onChange={e => setNote(e.target.value)}
              placeholder="e.g. Payment for prediction tip"
              className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50"
            />
          </div>
          <button
            onClick={() => mutation.mutate()}
            disabled={!recipient || !amount || mutation.isPending}
            className="w-full py-3 rounded-xl bg-vit-500 hover:bg-vit-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <Spinner className="w-4 h-4" /> : <Send className="w-4 h-4" />}
            {mutation.isPending ? 'Sending…' : 'Send VIT'}
          </button>
        </div>
      )}
    </Modal>
  )
}

// ── Receive modal ─────────────────────────────────────────────────────────────

function ReceiveModal({ onClose, address }: { onClose: () => void; address?: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    if (address) { navigator.clipboard.writeText(address); setCopied(true); setTimeout(() => setCopied(false), 2000) }
  }
  return (
    <Modal title="Receive VIT" onClose={onClose}>
      <div className="flex flex-col items-center gap-5 py-2">
        {/* Deterministic address-derived pattern (no random re-renders) */}
        <div className="w-32 h-32 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center overflow-hidden">
          {address ? (
            <div className="grid grid-cols-9 gap-0.5 p-2">
              {Array.from({ length: 81 }).map((_, i) => {
                const charCode = address.charCodeAt(i % address.length) + i
                const filled = (charCode * 31 + i * 7) % 5 !== 0
                return <div key={i} className={`w-1.5 h-1.5 rounded-[1px] ${filled ? 'bg-vit-400' : 'bg-transparent'}`} />
              })}
            </div>
          ) : (
            <WalletIcon className="w-10 h-10 text-white/20" />
          )}
        </div>
        <div className="w-full">
          <p className="text-xs text-white/40 mb-2 text-center">Your VIT Wallet Address</p>
          <div className="flex items-center gap-2 bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3">
            <span className="flex-1 font-mono text-xs text-white/70 truncate">{address ?? 'Loading…'}</span>
            <button onClick={copy} className="shrink-0">
              {copied ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-white/40 hover:text-white/80 transition-colors" />}
            </button>
          </div>
        </div>
        <p className="text-xs text-white/30 text-center">Send only VIT tokens to this address. Sending other assets may result in permanent loss.</p>
      </div>
    </Modal>
  )
}

// ── Stake modal ───────────────────────────────────────────────────────────────

function StakeModal({ onClose, balance, staked, apy }: { onClose: () => void; balance: number; staked: number; apy?: number | null }) {
  const [mode, setMode] = useState<'stake' | 'unstake'>('stake')
  const [amount, setAmount] = useState('')
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/${mode}`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: parseFloat(amount) }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Operation failed')
      return d
    },
    onSuccess: (d: any) => {
      setResult({ ok: true, msg: d.message ?? `${mode === 'stake' ? 'Staked' : 'Unstaked'} successfully.` })
      qc.invalidateQueries({ queryKey: ['wallet'] })
      qc.invalidateQueries({ queryKey: ['wallet-staking'] })
    },
    onError: (e: Error) => setResult({ ok: false, msg: e.message }),
  })

  const maxAmount = mode === 'stake' ? balance : staked

  return (
    <Modal title="Stake VIT" onClose={onClose}>
      {result ? (
        <div className={`flex flex-col items-center gap-3 py-6 text-center ${result.ok ? 'text-emerald-400' : 'text-red-400'}`}>
          {result.ok ? <CheckCircle2 className="w-12 h-12" /> : <AlertCircle className="w-12 h-12" />}
          <p className="font-medium">{result.msg}</p>
          <button onClick={onClose} className="mt-2 px-6 py-2 rounded-lg bg-white/10 text-white text-sm hover:bg-white/15 transition-colors">Close</button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 p-1 bg-surface-900/60 rounded-xl">
            {(['stake', 'unstake'] as const).map(m => (
              <button key={m} onClick={() => { setMode(m); setAmount('') }}
                className={`py-2 rounded-lg text-sm font-medium transition-colors capitalize ${mode === m ? 'bg-vit-500 text-white' : 'text-white/40 hover:text-white/70'}`}>
                {m}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-surface-900/60 rounded-lg p-3">
              <p className="text-xs text-white/40">Available</p>
              <p className="font-bold text-white text-sm mt-0.5">{balance.toLocaleString()}</p>
            </div>
            <div className="bg-surface-900/60 rounded-lg p-3">
              <p className="text-xs text-white/40">Staked</p>
              <p className="font-bold text-amber-400 text-sm mt-0.5">{staked.toLocaleString()}</p>
            </div>
            <div className="bg-surface-900/60 rounded-lg p-3">
              <p className="text-xs text-white/40">APY</p>
              <p className="font-bold text-emerald-400 text-sm mt-0.5">{apy != null ? `${apy}%` : '—'}</p>
            </div>
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Amount (VIT) — Max: {maxAmount.toLocaleString()}</label>
            <div className="relative">
              <input
                type="number" value={amount} onChange={e => setAmount(e.target.value)}
                placeholder="0.00" min="0" max={maxAmount}
                className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50"
              />
              <button onClick={() => setAmount(String(maxAmount))} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-vit-400 hover:text-vit-300">MAX</button>
            </div>
          </div>
          <button
            onClick={() => mutation.mutate()}
            disabled={!amount || parseFloat(amount) <= 0 || mutation.isPending}
            className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <Spinner className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
            {mutation.isPending ? 'Processing…' : mode === 'stake' ? 'Stake VIT' : 'Unstake VIT'}
          </button>
        </div>
      )}
    </Modal>
  )
}

// ── Withdraw modal ────────────────────────────────────────────────────────────

function WithdrawModal({ onClose, tier }: { onClose: () => void; tier: string }) {
  const [amount, setAmount] = useState('')
  const [destType, setDestType] = useState<'bank_account' | 'usdt_address'>('bank_account')
  const [bankCode, setBankCode] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [accountName, setAccountName] = useState('')
  const [usdtAddress, setUsdtAddress] = useState('')
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const qc = useQueryClient()

  const tierCfg = TIER_CONFIG[tier] ?? TIER_CONFIG.viewer

  const mutation = useMutation({
    mutationFn: async () => {
      const body: any = { amount: parseFloat(amount), destination_type: destType, currency: 'NGN' }
      if (destType === 'bank_account') { body.bank_code = bankCode; body.account_number = accountNumber; body.account_name = accountName }
      else { body.destination = usdtAddress }
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/withdraw`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Withdrawal failed')
      return d
    },
    onSuccess: (d: any) => {
      setResult({ ok: true, msg: d.message ?? 'Withdrawal request submitted. Processing in 1-2 business days.' })
      qc.invalidateQueries({ queryKey: ['wallet'] })
      qc.invalidateQueries({ queryKey: ['wallet-txs'] })
    },
    onError: (e: Error) => setResult({ ok: false, msg: e.message }),
  })

  return (
    <Modal title="Withdraw Funds" onClose={onClose}>
      {result ? (
        <div className={`flex flex-col items-center gap-3 py-6 text-center ${result.ok ? 'text-emerald-400' : 'text-red-400'}`}>
          {result.ok ? <CheckCircle2 className="w-12 h-12" /> : <AlertCircle className="w-12 h-12" />}
          <p className="font-medium text-sm px-4">{result.msg}</p>
          <button onClick={onClose} className="mt-2 px-6 py-2 rounded-lg bg-white/10 text-white text-sm hover:bg-white/15 transition-colors">Close</button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${tierCfg.bg} border border-white/10`}>
            <Shield className={`w-4 h-4 ${tierCfg.color}`} />
            <span className="text-xs text-white/60">Tier: <span className={`font-medium ${tierCfg.color}`}>{tierCfg.label}</span> — Limit: {tierCfg.limit}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 p-1 bg-surface-900/60 rounded-xl">
            {[{ v: 'bank_account', l: 'Bank Transfer' }, { v: 'usdt_address', l: 'USDT Address' }].map(({ v, l }) => (
              <button key={v} onClick={() => setDestType(v as any)}
                className={`py-2 rounded-lg text-xs font-medium transition-colors ${destType === v ? 'bg-vit-500 text-white' : 'text-white/40 hover:text-white/70'}`}>
                {l}
              </button>
            ))}
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Amount (NGN)</label>
            <input
              type="number" value={amount} onChange={e => setAmount(e.target.value)}
              placeholder="e.g. 50000"
              className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50"
            />
          </div>
          {destType === 'bank_account' ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-white/50 mb-1.5 block">Bank Code</label>
                  <input value={bankCode} onChange={e => setBankCode(e.target.value)} placeholder="058"
                    className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50" />
                </div>
                <div>
                  <label className="text-xs text-white/50 mb-1.5 block">Account Number</label>
                  <input value={accountNumber} onChange={e => setAccountNumber(e.target.value)} placeholder="0123456789"
                    className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50" />
                </div>
              </div>
              <div>
                <label className="text-xs text-white/50 mb-1.5 block">Account Name</label>
                <input value={accountName} onChange={e => setAccountName(e.target.value)} placeholder="John Doe"
                  className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50" />
              </div>
            </>
          ) : (
            <div>
              <label className="text-xs text-white/50 mb-1.5 block">USDT Address (TRC-20)</label>
              <input value={usdtAddress} onChange={e => setUsdtAddress(e.target.value)} placeholder="T..."
                className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50 font-mono" />
            </div>
          )}
          <button
            onClick={() => mutation.mutate()}
            disabled={!amount || mutation.isPending}
            className="w-full py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <Spinner className="w-4 h-4" /> : <ArrowUpRight className="w-4 h-4" />}
            {mutation.isPending ? 'Submitting…' : 'Submit Withdrawal'}
          </button>
        </div>
      )}
    </Modal>
  )
}

// ── KYC modal ─────────────────────────────────────────────────────────────────

function KYCModal({ onClose }: { onClose: () => void }) {
  const [fullName, setFullName] = useState('')
  const [dob, setDob] = useState('')
  const [docType, setDocType] = useState('national_id')
  const [docNumber, setDocNumber] = useState('')
  const [nationality, setNationality] = useState('')
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/wallet/kyc/submit`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: fullName, date_of_birth: dob, document_type: docType, document_number: docNumber, nationality }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'KYC submission failed')
      return d
    },
    onSuccess: () => {
      setResult({ ok: true, msg: 'KYC submitted. Our AI screener will review within 10 minutes.' })
      qc.invalidateQueries({ queryKey: ['kyc-status'] })
    },
    onError: (e: Error) => setResult({ ok: false, msg: e.message }),
  })

  const docTypes = [
    { v: 'national_id', l: 'National ID' },
    { v: 'passport', l: 'Passport' },
    { v: 'drivers_license', l: "Driver's License" },
    { v: 'voters_card', l: "Voter's Card" },
  ]

  return (
    <Modal title="KYC Verification" onClose={onClose}>
      {result ? (
        <div className={`flex flex-col items-center gap-3 py-6 text-center ${result.ok ? 'text-emerald-400' : 'text-red-400'}`}>
          {result.ok ? <CheckCircle2 className="w-12 h-12" /> : <AlertCircle className="w-12 h-12" />}
          <p className="font-medium text-sm px-4">{result.msg}</p>
          <button onClick={onClose} className="mt-2 px-6 py-2 rounded-lg bg-white/10 text-white text-sm hover:bg-white/15 transition-colors">Close</button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-xs text-white/40">Complete KYC to unlock higher withdrawal limits and Pro-tier features.</p>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Full Legal Name</label>
            <input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="As on document"
              className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50" />
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Date of Birth</label>
            <input type="date" value={dob} onChange={e => setDob(e.target.value)}
              className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-vit-500/50" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-white/50 mb-1.5 block">Document Type</label>
              <select value={docType} onChange={e => setDocType(e.target.value)}
                className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-vit-500/50">
                {docTypes.map(d => <option key={d.v} value={d.v}>{d.l}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-white/50 mb-1.5 block">Document Number</label>
              <input value={docNumber} onChange={e => setDocNumber(e.target.value)} placeholder="A1234567"
                className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50 font-mono" />
            </div>
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Nationality</label>
            <input value={nationality} onChange={e => setNationality(e.target.value)} placeholder="e.g. Nigerian"
              className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-3 text-white text-sm placeholder:text-white/25 focus:outline-none focus:border-vit-500/50" />
          </div>
          <button
            onClick={() => mutation.mutate()}
            disabled={!fullName || !dob || !docNumber || mutation.isPending}
            className="w-full py-3 rounded-xl bg-vit-500 hover:bg-vit-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? <Spinner className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
            {mutation.isPending ? 'Submitting…' : 'Submit KYC'}
          </button>
        </div>
      )}
    </Modal>
  )
}

// ── Deposit Modal ─────────────────────────────────────────────────────────────

function DepositModal({ onClose }: { onClose: () => void }) {
  const [method, setMethod] = useState<'paystack' | 'mobilemoney' | 'crypto' | null>(null)
  const [amount, setAmount] = useState('')
  const [phone,  setPhone]  = useState('')
  const [loading, setLoading] = useState(false)

  const methods = [
    { id: 'paystack'    as const, label: 'Card / Bank (Paystack)', icon: '💳', desc: 'Instant NGN deposits via debit card or bank transfer' },
    { id: 'mobilemoney' as const, label: 'Mobile Money',           icon: '📱', desc: 'MTN, Airtel, and other mobile wallets' },
    { id: 'crypto'      as const, label: 'Crypto (Direct)',        icon: '🔗', desc: 'Send ETH, USDT, or BNB to your VIT wallet address' },
  ]

  async function submit() {
    if (!method || !amount) return
    setLoading(true)
    await new Promise(r => setTimeout(r, 1200))
    setLoading(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-md bg-surface-900 border border-white/12 rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-white/8">
          <h2 className="font-bold text-white text-lg">Deposit Funds</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/8 text-white/40 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-6 space-y-5">
          <div>
            <p className="text-sm text-white/50 mb-3">Choose deposit method</p>
            <div className="space-y-2">
              {methods.map(m => (
                <button key={m.id} onClick={() => setMethod(m.id)}
                  className={cn('w-full flex items-center gap-3 p-3.5 rounded-xl border text-left transition-all',
                    method === m.id ? 'border-vit-500/50 bg-vit-500/10' : 'border-white/8 bg-white/3 hover:border-white/15 hover:bg-white/5')}>
                  <span className="text-2xl">{m.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-white">{m.label}</p>
                    <p className="text-xs text-white/40">{m.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {method && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-white/50 mb-1.5 block">Amount (NGN)</label>
                <input value={amount} onChange={e => setAmount(e.target.value)} type="number" placeholder="e.g. 5000"
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-vit-500/50 focus:bg-white/8" />
              </div>
              {method === 'mobilemoney' && (
                <div>
                  <label className="text-xs text-white/50 mb-1.5 block">Phone Number</label>
                  <input value={phone} onChange={e => setPhone(e.target.value)} type="tel" placeholder="+234..."
                    className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-vit-500/50 focus:bg-white/8" />
                </div>
              )}
            </div>
          )}

          <button onClick={submit} disabled={!method || !amount || loading}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors">
            {loading ? <Spinner className="w-4 h-4" /> : 'Proceed to Deposit'}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type ModalType = 'send' | 'receive' | 'stake' | 'withdraw' | 'kyc' | 'deposit' | null

export default function Wallet() {
  const navigate = useNavigate()
  const token    = getAuthToken()

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const { data: wallet, refetch: refetchWallet }  = useWallet()
  const { data: price }   = useWalletPrice()
  const { data: txs, refetch: refetchTxs }    = useTransactions()
  const { data: staking } = useStakingInfo()
  const { data: kyc }     = useKYCStatus()
  const [copied, setCopied] = useState(false)
  const [activeModal, setActiveModal] = useState<ModalType>(null)
  const qc = useQueryClient()

  function copyAddress() {
    if (wallet?.address) {
      navigator.clipboard.writeText(wallet.address)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Phase 4: support all known backend balance field names; pick the first non-falsy one.
  const balance    = parseFloat(
    wallet?.vitcoin_balance ?? wallet?.vit_balance ?? wallet?.balance ?? '0'
  ) || 0
  const stakedAmt  = parseFloat(staking?.staked_amount ?? wallet?.staked ?? '0') || 0
  const usdValue   = price?.price_usd ? (balance * price.price_usd).toFixed(2) : null
  const tier       = wallet?.subscription_tier ?? 'viewer'
  const tierCfg    = TIER_CONFIG[tier] ?? TIER_CONFIG.viewer

  const kycStatus  = kyc?.status ?? 'unverified'
  const kycColor   = kycStatus === 'approved' ? 'text-emerald-400' : kycStatus === 'pending' ? 'text-amber-400' : 'text-white/30'
  const kycBg      = kycStatus === 'approved' ? 'bg-emerald-500/10 border-emerald-500/20' : kycStatus === 'pending' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-white/5 border-white/10'

  if (!token) return (
    <div className="pt-16 min-h-screen flex items-center justify-center">
      <Spinner className="w-8 h-8 text-vit-400" />
    </div>
  )

  return (
    <div className="pt-16 min-h-screen">
      {/* Modals */}
      {activeModal === 'deposit'  && <DepositModal  onClose={() => setActiveModal(null)} />}
      {activeModal === 'send'     && <SendModal     onClose={() => setActiveModal(null)} balance={balance} />}
      {activeModal === 'receive'  && <ReceiveModal  onClose={() => setActiveModal(null)} address={wallet?.address} />}
      {activeModal === 'stake'    && <StakeModal    onClose={() => setActiveModal(null)} balance={balance} staked={stakedAmt} apy={staking?.apy ?? staking?.annual_rate} />}
      {activeModal === 'withdraw' && <WithdrawModal onClose={() => setActiveModal(null)} tier={tier} />}
      {activeModal === 'kyc'      && <KYCModal      onClose={() => setActiveModal(null)} />}

      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <WalletIcon className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Wallet</h1>
                <p className="text-white/50 text-sm">Manage your VITCoin and on-chain assets</p>
              </div>
            </div>
            {/* Tier + KYC badges */}
            <div className="flex items-center gap-2">
              <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium ${tierCfg.bg} ${tierCfg.color} border-white/10`}>
                <Star className="w-3 h-3" /> {tierCfg.label}
              </span>
              <button
                onClick={() => kycStatus !== 'approved' && setActiveModal('kyc')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium ${kycBg} ${kycColor} ${kycStatus !== 'approved' ? 'cursor-pointer hover:brightness-110 transition-all' : 'cursor-default'}`}
              >
                {kycStatus === 'approved' ? <CheckCircle2 className="w-3 h-3" /> : kycStatus === 'pending' ? <Clock className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                KYC {kycStatus === 'approved' ? 'Verified' : kycStatus === 'pending' ? 'Under Review' : 'Unverified'}
              </button>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Balance card */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="relative rounded-2xl border border-white/10 bg-gradient-to-br from-vit-500/10 via-surface-800 to-surface-800/60 p-8 overflow-hidden">
          <div className="absolute inset-0 section-grid opacity-10" />
          <div className="relative">
            <p className="text-white/40 text-sm mb-2">Total Balance</p>
            <div className="flex items-end gap-4 mb-1">
              <span className="text-5xl font-bold text-white">{balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
              <span className="text-2xl text-vit-400 font-semibold mb-1">VIT</span>
            </div>
            {usdValue && <p className="text-white/40 text-sm mb-1">≈ ${usdValue} USD</p>}

            {/* Address */}
            {wallet?.address && (
              <button onClick={copyAddress} className="flex items-center gap-2 mt-4 group">
                <span className="font-mono text-xs text-white/30 group-hover:text-white/50 transition-colors">
                  {wallet.address.slice(0, 8)}…{wallet.address.slice(-6)}
                </span>
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-white/20 group-hover:text-white/50 transition-colors" />}
              </button>
            )}

            {/* Quick actions */}
            <div className="grid grid-cols-5 gap-3 mt-6">
              {[
                { icon: TrendingUp,      label: 'Deposit',  action: 'deposit',  color: 'text-cyan-400',    bg: 'bg-cyan-500/10 border-cyan-500/20 hover:bg-cyan-500/20' },
                { icon: Send,            label: 'Send',     action: 'send',     color: 'text-vit-400',     bg: 'bg-vit-500/10 border-vit-500/20 hover:bg-vit-500/20' },
                { icon: Download,        label: 'Receive',  action: 'receive',  color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/20' },
                { icon: Zap,             label: 'Stake',    action: 'stake',    color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/20 hover:bg-amber-500/20' },
                { icon: ArrowUpRight,    label: 'Withdraw', action: 'withdraw', color: 'text-purple-400',  bg: 'bg-purple-500/10 border-purple-500/20 hover:bg-purple-500/20' },
              ].map(({ icon: Icon, label, action, color, bg }) => (
                <button key={action} onClick={() => setActiveModal(action as ModalType)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border ${bg} transition-all`}>
                  <Icon className={`w-5 h-5 ${color}`} />
                  <span className="text-xs text-white/60 font-medium">{label}</span>
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Staking + VIT price row */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
            className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs text-white/40">Staked</p>
              <Zap className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xl font-bold text-amber-400">{stakedAmt.toLocaleString()} VIT</p>
            {staking?.estimated_daily_reward != null && (
              <p className="text-xs text-white/30 mt-1">~{staking.estimated_daily_reward.toFixed(4)} VIT/day</p>
            )}
          </motion.div>

          {price && [
            { label: 'VIT / USD',  value: `$${price.price_usd?.toFixed(6) ?? '—'}` },
            { label: 'VIT / NGN',  value: `₦${price.price_ngn?.toLocaleString() ?? '—'}` },
            { label: '24h Volume', value: price.volume_24h ? `$${(price.volume_24h / 1e6).toFixed(2)}M` : '—' },
          ].map(({ label, value }, i) => (
            <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * (i + 2) }}
              className="bg-surface-800/60 border border-white/8 rounded-xl p-5">
              <p className="text-xs text-white/40 mb-1">{label}</p>
              <p className="text-xl font-bold text-white">{value}</p>
            </motion.div>
          ))}
        </div>

        {/* Withdrawal tier info */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className={`flex items-center justify-between p-4 rounded-xl border ${tierCfg.bg} border-white/8`}>
          <div className="flex items-center gap-3">
            <Layers className={`w-5 h-5 ${tierCfg.color}`} />
            <div>
              <p className="text-sm font-medium text-white">{tierCfg.label} Tier</p>
              <p className="text-xs text-white/40">Withdrawal limit: {tierCfg.limit}</p>
            </div>
          </div>
          {tier !== 'elite' && tier !== 'admin' && (
            <button
              onClick={() => setActiveModal('kyc')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-vit-500/20 border border-vit-500/30 text-vit-400 text-xs font-medium hover:bg-vit-500/30 transition-colors">
              Upgrade <ChevronRight className="w-3 h-3" />
            </button>
          )}
        </motion.div>

        {/* Transaction history */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-white/8">
            <h2 className="font-semibold text-white">Transaction History</h2>
            <button onClick={() => { qc.invalidateQueries({ queryKey: ['wallet-txs'] }); refetchTxs() }}
              className="p-1.5 rounded-lg hover:bg-white/5 transition-colors">
              <RefreshCw className="w-4 h-4 text-white/30 hover:text-white/60" />
            </button>
          </div>
          {!txs || txs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <WalletIcon className="w-12 h-12 text-white/10 mb-3" />
              <p className="text-white/40">No transactions yet</p>
              <p className="text-white/25 text-sm mt-1">Your on-chain activity will appear here</p>
            </div>
          ) : (
            <div>
              {txs.map((tx: any, i: number) => {
                const isOut = tx.type === 'sent' || tx.type === 'withdrawal' || tx.type === 'stake' || (tx.amount ?? 0) < 0
                const txTypeColor = tx.type === 'stake' ? 'bg-amber-500/10' : isOut ? 'bg-red-500/10' : 'bg-emerald-500/10'
                const txIconColor = tx.type === 'stake' ? 'text-amber-400' : isOut ? 'text-red-400' : 'text-emerald-400'
                const TxIcon = tx.type === 'stake' ? Zap : isOut ? ArrowUpRight : ArrowDownLeft
                return (
                  <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${txTypeColor}`}>
                      <TxIcon className={`w-4 h-4 ${txIconColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white capitalize">{tx.type?.replace(/_/g, ' ') || (isOut ? 'Sent' : 'Received')}</p>
                      {tx.to && <p className="text-xs text-white/30 truncate font-mono">{tx.to}</p>}
                      {tx.hash && <p className="text-xs text-white/20 truncate font-mono">{tx.hash.slice(0, 16)}…</p>}
                      {tx.created_at && <p className="text-xs text-white/25">{new Date(tx.created_at).toLocaleString()}</p>}
                    </div>
                    <div className="text-right shrink-0">
                      <span className={`text-sm font-bold ${isOut ? 'text-red-400' : 'text-emerald-400'}`}>
                        {isOut ? '-' : '+'}{Math.abs(tx.amount || 0).toLocaleString()} VIT
                      </span>
                      {tx.status && (
                        <p className={`text-xs mt-0.5 ${tx.status === 'completed' ? 'text-emerald-400/60' : tx.status === 'pending' ? 'text-amber-400/60' : 'text-white/20'}`}>
                          {tx.status}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
