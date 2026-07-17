import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Shield, Server, CheckCircle2, XCircle, Clock, Zap,
  TrendingUp, AlertCircle, ChevronRight, Users, Star,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Validator {
  id: number | string
  node_id?: string
  operator: string
  stake_amount: number
  commission_rate?: number
  uptime_pct?: number
  blocks_validated?: number
  status: 'active' | 'inactive' | 'slashed' | 'pending' | string
  joined_at?: string
  last_seen?: string
}

interface MyValidator {
  status: string
  stake_amount: number
  pending_rewards?: number
  slashing_history?: { reason: string; amount: number; at: string }[]
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useValidators() {
  return useQuery<Validator[]>({
    queryKey: ['validators-active'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/validators/active`, { signal })
      if (!r.ok) return []
      const d = await r.json()
      return Array.isArray(d) ? d : d.validators ?? d.items ?? []
    },
    staleTime: 60_000,
    refetchInterval: 120_000,
  })
}

function useMyValidator() {
  return useQuery<MyValidator | null>({
    queryKey: ['my-validator'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/validators/me`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    enabled: !!getAuthToken(),
    retry: false,
    staleTime: 60_000,
  })
}

// ── Status pill ───────────────────────────────────────────────────────────────

const STATUS: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
  active:   { label: 'Active',   cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25', icon: CheckCircle2 },
  pending:  { label: 'Pending',  cls: 'bg-amber-500/15 text-amber-400 border-amber-500/25',       icon: Clock        },
  inactive: { label: 'Inactive', cls: 'bg-white/8 text-white/40 border-white/10',                icon: XCircle      },
  slashed:  { label: 'Slashed',  cls: 'bg-red-500/15 text-red-400 border-red-500/25',            icon: AlertCircle  },
}

function StatusPill({ status }: { status: string }) {
  const s = STATUS[status] ?? STATUS.inactive
  const Icon = s.icon
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border', s.cls)}>
      <Icon className="w-3 h-3" />
      {s.label}
    </span>
  )
}

// ── Validator row ─────────────────────────────────────────────────────────────

function ValidatorRow({ v, i }: { v: Validator; i: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04 }}
      className="flex items-center gap-4 p-4 rounded-xl bg-surface-800/50 border border-white/6 hover:border-white/12 transition-colors"
    >
      {/* Rank */}
      <div className="w-7 text-center text-xs font-mono text-white/30 shrink-0">{i + 1}</div>

      {/* Operator */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{v.operator}</p>
        {v.node_id && <p className="text-[11px] text-white/30 font-mono truncate">{v.node_id}</p>}
      </div>

      {/* Stats */}
      <div className="hidden sm:flex items-center gap-6 text-right shrink-0">
        <div>
          <p className="text-xs text-white/35">Stake</p>
          <p className="text-sm font-semibold text-white">{v.stake_amount.toLocaleString()} VIT</p>
        </div>
        {v.uptime_pct != null && (
          <div>
            <p className="text-xs text-white/35">Uptime</p>
            <p className={cn('text-sm font-semibold', v.uptime_pct >= 99 ? 'text-emerald-400' : v.uptime_pct >= 95 ? 'text-amber-400' : 'text-red-400')}>
              {v.uptime_pct.toFixed(1)}%
            </p>
          </div>
        )}
        {v.commission_rate != null && (
          <div>
            <p className="text-xs text-white/35">Commission</p>
            <p className="text-sm font-semibold text-white/70">{(v.commission_rate * 100).toFixed(1)}%</p>
          </div>
        )}
        {v.blocks_validated != null && (
          <div>
            <p className="text-xs text-white/35">Blocks</p>
            <p className="text-sm font-semibold text-white/70">{v.blocks_validated.toLocaleString()}</p>
          </div>
        )}
      </div>

      <StatusPill status={v.status} />
    </motion.div>
  )
}

// ── Apply panel ───────────────────────────────────────────────────────────────

function ApplyPanel() {
  const qc = useQueryClient()
  const [stake, setStake] = useState('')
  const [agreed, setAgreed] = useState(false)

  const mutation = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/validators/apply`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ stake_amount: parseFloat(stake) }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? 'Application failed')
      return d
    },
    onSuccess: () => {
      toast.success('Validator application submitted')
      qc.invalidateQueries({ queryKey: ['my-validator'] })
      setStake('')
      setAgreed(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="bg-surface-800/60 border border-vit-500/20 rounded-2xl p-6 space-y-5">
      <div className="flex items-center gap-2.5">
        <Server className="w-5 h-5 text-vit-400" />
        <h3 className="font-semibold text-white">Apply to become a Validator</h3>
      </div>

      <ul className="space-y-2 text-sm text-white/55">
        <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />Minimum stake: 10,000 VIT</li>
        <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />Earn block rewards + commission from delegators</li>
        <li className="flex gap-2"><AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />Stake is subject to slashing for malicious behaviour</li>
      </ul>

      <div>
        <label className="block text-xs font-medium text-white/50 mb-1.5">Stake amount (VIT)</label>
        <input
          type="number"
          min="10000"
          step="1000"
          value={stake}
          onChange={e => setStake(e.target.value)}
          placeholder="10000"
          className="w-full bg-surface-900/60 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm placeholder-white/25 focus:outline-none focus:border-vit-500/60 focus:ring-1 focus:ring-vit-500/20 transition-colors"
        />
      </div>

      <label className="flex items-start gap-2.5 cursor-pointer">
        <input
          type="checkbox"
          checked={agreed}
          onChange={e => setAgreed(e.target.checked)}
          className="mt-0.5 accent-vit-500"
        />
        <span className="text-xs text-white/45">
          I understand the validator responsibilities, slashing conditions, and agree to run a reliable node.
        </span>
      </label>

      <button
        onClick={() => mutation.mutate()}
        disabled={!stake || parseFloat(stake) < 10000 || !agreed || mutation.isPending}
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-vit-600 text-white font-semibold text-sm hover:bg-vit-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRight className="w-4 h-4" />
        {mutation.isPending ? 'Submitting…' : 'Submit Application'}
      </button>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Validators() {
  const { data: validators = [], isLoading } = useValidators()
  const { data: myValidator } = useMyValidator()

  const active  = validators.filter(v => v.status === 'active').length
  const totalStake = validators.reduce((s, v) => s + (v.stake_amount || 0), 0)

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-center gap-2.5 mb-2">
            <Shield className="w-5 h-5 text-vit-400" />
            <h1 className="text-2xl font-bold text-white">Validators</h1>
          </div>
          <p className="text-white/45 text-sm">Secure the VIT Network by staking and running a validator node.</p>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Active Validators', value: active,                             icon: Shield,   color: 'text-emerald-400' },
            { label: 'Total Validators',  value: validators.length,                  icon: Users,    color: 'text-vit-400'     },
            { label: 'Total Staked',      value: `${(totalStake/1e6).toFixed(1)}M VIT`, icon: Star, color: 'text-amber-400'  },
            { label: 'Avg Uptime',
              value: validators.length
                ? `${(validators.reduce((s,v) => s+(v.uptime_pct??0),0)/validators.length).toFixed(1)}%`
                : '—',
              icon: TrendingUp, color: 'text-sky-400',
            },
          ].map(s => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="bg-surface-800/50 border border-white/8 rounded-xl p-4"
            >
              <s.icon className={cn('w-4 h-4 mb-2', s.color)} />
              <p className={cn('text-lg font-bold', s.color)}>{s.value}</p>
              <p className="text-xs text-white/35">{s.label}</p>
            </motion.div>
          ))}
        </div>

        {/* My validator status */}
        {myValidator && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-5 rounded-xl bg-vit-500/8 border border-vit-500/25"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Your validator</p>
                <p className="text-xs text-white/45 mt-0.5">Stake: {myValidator.stake_amount?.toLocaleString()} VIT</p>
              </div>
              <div className="text-right">
                <StatusPill status={myValidator.status} />
                {myValidator.pending_rewards != null && (
                  <p className="text-xs text-emerald-400 mt-1.5">+{myValidator.pending_rewards.toFixed(2)} VIT pending</p>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* Validator list */}
        <div className="mb-8">
          <h2 className="font-semibold text-white mb-4">Active Validator Set</h2>
          {isLoading ? (
            <div className="flex justify-center py-12"><Spinner className="w-8 h-8" /></div>
          ) : validators.length === 0 ? (
            <div className="text-center py-12 text-white/40 text-sm">No validators data available</div>
          ) : (
            <div className="space-y-2">
              {validators.map((v, i) => <ValidatorRow key={v.id ?? i} v={v} i={i} />)}
            </div>
          )}
        </div>

        {/* Apply */}
        {getAuthToken() && !myValidator && <ApplyPanel />}
        {!getAuthToken() && (
          <div className="flex items-center gap-2.5 p-4 rounded-xl bg-white/3 border border-white/8 text-sm text-white/50">
            <Zap className="w-4 h-4 text-vit-400 shrink-0" />
            Sign in to apply as a validator and manage your node.
          </div>
        )}
      </div>
    </div>
  )
}
