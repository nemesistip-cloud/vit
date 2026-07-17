import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Coins, TrendingUp, Lock, Unlock, Gift, BarChart3,
  X, Plus, ChevronRight, AlertTriangle, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Pool {
  id: string
  name: string
  token_a: string
  token_b?: string
  tvl_usd: number
  apy: number
  volume_24h: number
  fee_tier: number
  protocol: string
  category: 'liquidity' | 'staking' | 'yield'
  risk: 'low' | 'medium' | 'high'
  lock_days?: number
}

interface Position {
  id: string
  pool_id: string
  pool_name: string
  amount: number
  token: string
  apy: number
  lock_days: number
  locked_until?: number
  staked_at: number
  last_claim_at: number
  accrued_yield: number
  status: string
}

interface DeFiStats {
  total_tvl_usd: number
  total_volume_24h: number
  average_apy: number
  active_pools: number
  active_positions: number
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

const BASE = () => `${ENDPOINTS.gateway}/api/defi`

function usePools(category?: string) {
  return useQuery({
    queryKey: ['defi-pools', category],
    queryFn: async ({ signal }) => {
      const url = `${BASE()}/pools${category ? `?category=${category}` : ''}`
      const r = await fetch(url, { signal })
      return r.ok ? r.json() : { pools: [] }
    },
    staleTime: 60_000,
  })
}

function usePositions() {
  return useQuery({
    queryKey: ['defi-positions'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/positions`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : { positions: [] }
    },
    refetchInterval: 30_000,
  })
}

function useDeFiStats() {
  return useQuery({
    queryKey: ['defi-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${BASE()}/stats`, { signal })
      return r.ok ? (r.json() as Promise<DeFiStats>) : null
    },
    staleTime: 30_000,
  })
}

// ── Risk badge ────────────────────────────────────────────────────────────────

const RISK_STYLES = {
  low:    'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  medium: 'bg-amber-500/15   text-amber-400   border-amber-500/30',
  high:   'bg-red-500/15     text-red-400     border-red-500/30',
}

const CATEGORY_ICON = {
  liquidity: Coins,
  staking:   Lock,
  yield:     Zap,
}

// ── Stake modal ───────────────────────────────────────────────────────────────

function StakeModal({ pool, onClose }: { pool: Pool; onClose: () => void }) {
  const qc = useQueryClient()
  const [amount, setAmount] = useState('')
  const [lockDays, setLockDays] = useState(pool.lock_days ?? 0)
  const [err, setErr] = useState('')

  const stake = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/stake`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: pool.id, amount: parseFloat(amount), lock_days: lockDays }),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed') }
      return r.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['defi-positions'] })
      qc.invalidateQueries({ queryKey: ['defi-stats'] })
      onClose()
    },
    onError: (e: Error) => setErr(e.message),
  })

  const expectedYield = parseFloat(amount) && lockDays
    ? ((parseFloat(amount) * (pool.apy / 100) * (lockDays / 365))).toFixed(4)
    : null

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-md bg-surface-900 border border-white/10 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/8">
          <div>
            <h2 className="font-semibold text-white">{pool.name}</h2>
            <p className="text-xs text-white/40">{pool.protocol} · {pool.apy}% APY</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Amount ({pool.token_a})</label>
            <input
              type="number"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50"
            />
          </div>

          {!pool.lock_days && (
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">Lock Period (days, optional)</label>
              <input
                type="number"
                value={lockDays}
                onChange={e => setLockDays(Number(e.target.value))}
                min={0}
                max={365}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-vit-500/50"
              />
            </div>
          )}

          {expectedYield && (
            <div className="bg-vit-500/10 border border-vit-500/20 rounded-xl p-3">
              <p className="text-xs text-white/50 mb-0.5">Estimated yield</p>
              <p className="text-lg font-bold text-vit-300">{expectedYield} {pool.token_a}</p>
              <p className="text-xs text-white/30">over {lockDays} days at {pool.apy}% APY</p>
            </div>
          )}

          {err && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {err}
            </div>
          )}

          <button
            onClick={() => stake.mutate()}
            disabled={!amount || parseFloat(amount) <= 0 || stake.isPending}
            className="w-full py-2.5 bg-vit-500 hover:bg-vit-600 text-white rounded-xl font-medium text-sm transition-colors disabled:opacity-40"
          >
            {stake.isPending ? <Spinner className="w-4 h-4 mx-auto" /> : `Stake ${pool.token_a}`}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Pool card ─────────────────────────────────────────────────────────────────

function PoolCard({ pool }: { pool: Pool }) {
  const [showStake, setShowStake] = useState(false)
  const Icon = CATEGORY_ICON[pool.category] ?? Coins

  return (
    <>
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 hover:border-white/15 transition-all group">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-vit-500/15 border border-vit-500/25 rounded-lg">
              <Icon className="w-4 h-4 text-vit-400" />
            </div>
            <div>
              <p className="font-semibold text-sm text-white">{pool.name}</p>
              <p className="text-xs text-white/40">{pool.protocol}</p>
            </div>
          </div>
          <span className={cn('px-2 py-0.5 rounded-full text-xs border', RISK_STYLES[pool.risk])}>
            {pool.risk} risk
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="text-center">
            <p className="text-lg font-bold text-emerald-400">{pool.apy}%</p>
            <p className="text-xs text-white/40">APY</p>
          </div>
          <div className="text-center">
            <p className="text-sm font-bold text-white">${(pool.tvl_usd / 1_000_000).toFixed(2)}M</p>
            <p className="text-xs text-white/40">TVL</p>
          </div>
          <div className="text-center">
            <p className="text-sm font-bold text-white/70">${(pool.volume_24h / 1000).toFixed(0)}K</p>
            <p className="text-xs text-white/40">Vol 24h</p>
          </div>
        </div>

        {pool.lock_days && (
          <div className="flex items-center gap-1.5 mb-3 text-xs text-amber-400">
            <Lock className="w-3 h-3" />
            {pool.lock_days}-day lock required
          </div>
        )}

        <button
          onClick={() => setShowStake(true)}
          className="w-full flex items-center justify-center gap-2 py-2 bg-vit-500/15 hover:bg-vit-500/25 text-vit-300 border border-vit-500/25 rounded-lg text-sm font-medium transition-all"
        >
          <Plus className="w-3.5 h-3.5" />
          Stake / Deposit
          <ChevronRight className="w-3.5 h-3.5 opacity-60" />
        </button>
      </div>

      <AnimatePresence>
        {showStake && <StakeModal pool={pool} onClose={() => setShowStake(false)} />}
      </AnimatePresence>
    </>
  )
}

// ── My positions ──────────────────────────────────────────────────────────────

function PositionRow({ pos }: { pos: Position }) {
  const qc = useQueryClient()

  const claim = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/claim`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ position_id: pos.id }),
      })
      if (!r.ok) throw new Error('Failed to claim')
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['defi-positions'] }),
  })

  const unstake = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${BASE()}/unstake`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ position_id: pos.id }),
      })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed') }
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['defi-positions'] }),
  })

  const isLocked = pos.locked_until && Date.now() / 1000 < pos.locked_until

  return (
    <div className="flex items-center justify-between p-3 bg-white/3 border border-white/8 rounded-xl">
      <div>
        <p className="text-sm font-medium text-white">{pos.pool_name}</p>
        <p className="text-xs text-white/40">{pos.amount} {pos.token} · {pos.apy}% APY</p>
      </div>
      <div className="flex items-center gap-2">
        <div className="text-right mr-2">
          <p className="text-xs text-white/40">Accrued</p>
          <p className="text-sm font-bold text-emerald-400">+{pos.accrued_yield?.toFixed(4)} {pos.token}</p>
        </div>
        <button
          onClick={() => claim.mutate()}
          disabled={claim.isPending || (pos.accrued_yield ?? 0) < 0.000001}
          className="flex items-center gap-1 px-2.5 py-1.5 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/25 rounded-lg text-xs font-medium transition-colors disabled:opacity-30"
        >
          <Gift className="w-3 h-3" />
          Claim
        </button>
        <button
          onClick={() => unstake.mutate()}
          disabled={unstake.isPending || !!isLocked}
          title={isLocked ? 'Still locked' : 'Withdraw'}
          className={cn(
            'flex items-center gap-1 px-2.5 py-1.5 border rounded-lg text-xs font-medium transition-colors disabled:opacity-30',
            isLocked
              ? 'bg-white/5 text-white/30 border-white/10'
              : 'bg-red-500/10 hover:bg-red-500/20 text-red-400 border-red-500/20',
          )}
        >
          {isLocked ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
          {isLocked ? 'Locked' : 'Withdraw'}
        </button>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DeFi() {
  const navigate = useNavigate()
  const [tab, setTab]           = useState<'pools' | 'positions'>('pools')
  const [category, setCategory] = useState<string | undefined>(undefined)

  useEffect(() => {
    if (!getAuthToken()) navigate('/login')
  }, [navigate])

  const { data: poolsData, isLoading: poolsLoading } = usePools(category)
  const { data: posData,   isLoading: posLoading   } = usePositions()
  const { data: stats }                               = useDeFiStats()

  const pools: Pool[]      = poolsData?.pools ?? []
  const positions: Position[] = posData?.positions ?? []

  const CATS = [
    { id: undefined,     label: 'All'       },
    { id: 'staking',     label: 'Staking'   },
    { id: 'liquidity',   label: 'Liquidity' },
    { id: 'yield',       label: 'Yield'     },
  ]

  return (
    <div className="min-h-screen bg-surface-950 pt-24 pb-16">
      <div className="max-w-4xl mx-auto px-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 bg-emerald-500/15 border border-emerald-500/25 rounded-xl">
              <Coins className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">DeFi Yield & Pools</h1>
              <p className="text-white/50 text-sm">Stake VIT, provide liquidity, earn yield</p>
            </div>
          </div>

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {[
                { label: 'Total TVL',      value: `$${(stats.total_tvl_usd / 1_000_000).toFixed(2)}M`, color: 'text-white' },
                { label: 'Volume 24h',     value: `$${(stats.total_volume_24h / 1000).toFixed(0)}K`,   color: 'text-white' },
                { label: 'Average APY',    value: `${stats.average_apy.toFixed(1)}%`,                 color: 'text-emerald-400' },
                { label: 'Active Pools',   value: stats.active_pools,                                  color: 'text-white' },
                { label: 'My Positions',   value: stats.active_positions,                              color: 'text-vit-400' },
              ].map(s => (
                <div key={s.label} className="bg-white/3 border border-white/8 rounded-xl p-3 text-center">
                  <p className={cn('text-lg font-bold', s.color)}>{s.value}</p>
                  <p className="text-xs text-white/40">{s.label}</p>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white/3 border border-white/8 rounded-xl p-1 max-w-xs">
          {(['pools', 'positions'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'flex-1 py-2 rounded-lg text-sm font-medium transition-all capitalize',
                tab === t ? 'bg-vit-500/20 text-vit-300 border border-vit-500/30' : 'text-white/50 hover:text-white/80',
              )}
            >
              {t === 'positions' ? `My Positions (${positions.length})` : 'Pools'}
            </button>
          ))}
        </div>

        {/* Pools tab */}
        {tab === 'pools' && (
          <>
            <div className="flex gap-2 mb-4 flex-wrap">
              {CATS.map(c => (
                <button
                  key={String(c.id)}
                  onClick={() => setCategory(c.id)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
                    category === c.id
                      ? 'bg-vit-500/20 text-vit-300 border-vit-500/30'
                      : 'bg-white/3 text-white/50 border-white/10 hover:border-white/20 hover:text-white/70',
                  )}
                >
                  {c.label}
                </button>
              ))}
            </div>

            {poolsLoading && <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {pools.map(pool => <PoolCard key={pool.id} pool={pool} />)}
            </div>
          </>
        )}

        {/* Positions tab */}
        {tab === 'positions' && (
          <>
            {posLoading && <div className="flex justify-center py-12"><Spinner className="w-6 h-6 text-vit-400" /></div>}
            {!posLoading && positions.length === 0 && (
              <div className="text-center py-16">
                <Coins className="w-10 h-10 text-white/20 mx-auto mb-3" />
                <p className="text-white/40 text-sm">No active positions. Stake into a pool to start earning.</p>
                <button onClick={() => setTab('pools')} className="mt-4 px-4 py-2 bg-vit-500/20 text-vit-400 border border-vit-500/30 rounded-xl text-sm hover:bg-vit-500/30 transition-colors">
                  Browse Pools
                </button>
              </div>
            )}
            <div className="space-y-3">
              {positions.map(pos => <PositionRow key={pos.id} pos={pos} />)}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
