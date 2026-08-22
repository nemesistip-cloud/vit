import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Lock, Zap, TrendingUp, Clock, X, ChevronRight, AlertCircle,
} from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface VaultDef {
  id: string
  name: string
  apy: number
  lockDays: number
  minStake: number
  color: string
  icon: React.ElementType
  description: string
}

const VAULTS: VaultDef[] = [
  { id: 'flex',    name: 'Flex Vault',    apy: 6,   lockDays: 0,   minStake: 100,   color: 'text-blue-400',    icon: Zap,         description: 'No lock-up, withdraw anytime. Earn baseline APY.' },
  { id: 'silver',  name: 'Silver Vault',  apy: 12,  lockDays: 30,  minStake: 500,   color: 'text-white/60',    icon: Lock,        description: '30-day lock for boosted yields.' },
  { id: 'gold',    name: 'Gold Vault',    apy: 20,  lockDays: 90,  minStake: 2000,  color: 'text-amber-400',   icon: TrendingUp,  description: '90-day lock for premium compounding rewards.' },
  { id: 'elite',   name: 'Elite Vault',   apy: 32,  lockDays: 180, minStake: 10000, color: 'text-vit-400',     icon: Clock,       description: '6-month lock, reserved for Elite-tier holders.' },
]

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

function StakeModal({ vault, onClose }: { vault: VaultDef; onClose: () => void }) {
  const qc = useQueryClient()
  const [amount, setAmount] = useState('')
  const { data: wallet } = useWalletBalance()
  const balance = parseFloat(wallet?.vit_balance ?? wallet?.balance ?? '0') || 0

  const stake = useMutation({
    mutationFn: async () => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/vaults/stake`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault_id: vault.id, amount: +amount }),
      })
      if (!r.ok) throw new Error('Stake failed')
      return r.json()
    },
    onSuccess: () => {
      toast.success(`Staked in ${vault.name}`)
      qc.invalidateQueries({ queryKey: ['vault-positions', 'wallet'] })
      onClose()
    },
    onError: () => toast.error('Staking failed'),
  })

  const dailyReward = amount ? ((+amount * vault.apy) / 100 / 365).toFixed(4) : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-md bg-surface-900 border border-white/12 rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-white/8">
          <div>
            <h2 className="font-bold text-white">{vault.name}</h2>
            <p className="text-xs text-white/40 mt-0.5">{vault.apy}% APY · {vault.lockDays === 0 ? 'No lock' : `${vault.lockDays}-day lock`}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/8 text-white/40 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between p-3 rounded-xl bg-white/3 border border-white/6 text-sm">
            <span className="text-white/40">Available balance</span>
            <span className="text-white font-medium">{balance.toLocaleString()} VIT</span>
          </div>

          <div>
            <label className="text-xs text-white/50 mb-1.5 block">Stake amount (VIT) — min {vault.minStake.toLocaleString()}</label>
            <div className="flex gap-2">
              <input value={amount} onChange={e => setAmount(e.target.value)} type="number" placeholder={vault.minStake.toString()}
                className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:border-vit-500/50" />
              <button onClick={() => setAmount(Math.floor(balance).toString())}
                className="px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/50 hover:text-white text-xs transition-colors">
                MAX
              </button>
            </div>
          </div>

          {dailyReward && (
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-emerald-500/8 border border-emerald-500/15 text-center">
                <p className="text-xs text-white/40">Daily reward</p>
                <p className="text-sm font-bold text-emerald-400">{dailyReward} VIT</p>
              </div>
              <div className="p-3 rounded-xl bg-vit-500/8 border border-vit-500/15 text-center">
                <p className="text-xs text-white/40">Annual yield</p>
                <p className="text-sm font-bold text-vit-400">{(+amount * vault.apy / 100).toFixed(2)} VIT</p>
              </div>
            </div>
          )}

          {vault.lockDays > 0 && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-500/8 border border-amber-500/15 text-xs text-amber-300/80">
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              Tokens are locked for {vault.lockDays} days after staking.
            </div>
          )}

          <button onClick={() => stake.mutate()} disabled={!amount || +amount < vault.minStake || stake.isPending}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-vit-600 hover:bg-vit-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors shadow-lg shadow-vit-500/20">
            {stake.isPending ? <Spinner className="w-4 h-4" /> : <>Stake Now <ChevronRight className="w-4 h-4" /></>}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default function Vaults() {
  const [stakeVault, setStakeVault] = useState<VaultDef | null>(null)
  const loadingPositions = false
  const posArr: any[] = []

  return (
    <div className="pt-16 min-h-screen">
      <AnimatePresence>{stakeVault && <StakeModal vault={stakeVault} onClose={() => setStakeVault(null)} />}</AnimatePresence>

      {/* Header */}
      <div className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Lock className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Staking Vaults</h1>
              <p className="text-white/50 text-sm">Earn passive VIT rewards by staking your tokens</p>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Vault cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {VAULTS.map((vault, i) => {
            const Icon = vault.icon
            return (
              <motion.div key={vault.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                className="bg-surface-800/60 border border-white/8 rounded-2xl p-5 flex flex-col hover:border-white/15 transition-all">
                <div className="flex items-center gap-2.5 mb-4">
                  <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center">
                    <Icon className={cn('w-4 h-4', vault.color)} />
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm">{vault.name}</p>
                    <p className="text-white/30 text-xs">{vault.lockDays === 0 ? 'Flexible' : `${vault.lockDays}-day lock`}</p>
                  </div>
                </div>
                <p className={cn('text-3xl font-bold mb-1', vault.color)}>{vault.apy}%</p>
                <p className="text-xs text-white/30 mb-3">APY</p>
                <p className="text-xs text-white/40 leading-relaxed flex-1 mb-4">{vault.description}</p>
                <div className="text-xs text-white/25 mb-4">Min stake: {vault.minStake.toLocaleString()} VIT</div>
                <button onClick={() => setStakeVault(vault)}
                  className="w-full py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/70 hover:bg-vit-600/20 hover:border-vit-500/30 hover:text-vit-400 text-sm font-medium transition-all">
                  Stake
                </button>
              </motion.div>
            )
          })}
        </div>

        {/* My positions */}
        <div>
          <h2 className="text-sm font-semibold text-white/50 uppercase tracking-wider mb-4">My Positions</h2>
          <div className="bg-surface-800/60 border border-white/8 rounded-xl overflow-hidden">
            {loadingPositions ? (
              <div className="flex justify-center py-12"><Spinner className="w-5 h-5 text-vit-400" /></div>
            ) : posArr.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-2">
                <Lock className="w-10 h-10 text-white/10" />
                <p className="text-white/30 text-sm">No active positions</p>
                <p className="text-white/20 text-xs">Stake into a vault to start earning</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/8">
                      {['Vault', 'Staked', 'APY', 'Earned', 'Unlock Date', 'Status'].map(h => (
                        <th key={h} className="text-left text-xs font-medium text-white/35 uppercase tracking-wide px-5 py-3">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {posArr.map((pos: any, i: number) => (
                      <tr key={pos.id ?? i} className="border-b border-white/5 last:border-0 hover:bg-white/3 transition-colors">
                        <td className="px-5 py-3.5 text-white font-medium capitalize">{pos.vault_id ?? pos.vault_name ?? '—'}</td>
                        <td className="px-5 py-3.5 text-amber-400 font-semibold">{Number(pos.amount ?? 0).toLocaleString()} VIT</td>
                        <td className="px-5 py-3.5 text-emerald-400">{pos.apy ?? '—'}%</td>
                        <td className="px-5 py-3.5 text-vit-400">{Number(pos.earned ?? 0).toFixed(4)} VIT</td>
                        <td className="px-5 py-3.5 text-white/40 text-xs">{pos.unlock_date ? new Date(pos.unlock_date).toLocaleDateString() : 'Anytime'}</td>
                        <td className="px-5 py-3.5">
                          <span className={cn('text-xs px-2 py-0.5 rounded-full border',
                            pos.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-white/5 text-white/30 border-white/10')}>
                            {pos.status ?? 'active'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
