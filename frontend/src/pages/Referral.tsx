import { useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Share2, Copy, CheckCircle2, Users, Zap, Trophy, Gift,
  ArrowRight, TrendingUp, Star, ExternalLink, Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import { useNavigate } from 'react-router-dom'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ReferralCode {
  code: string
  link: string
  signup_bonus_vit: number
  deposit_commission_pct: number
  subscription_commission_pct: number
}

interface ReferralStats {
  total: number
  pending_bonuses: number
  referrals: Array<{ username: string; joined_at?: string; bonus_paid: boolean }>
}

interface LeaderboardEntry {
  rank: number
  username: string
  referrals: number
  earned_vit: number
}

// ── API hooks ─────────────────────────────────────────────────────────────────

function useMyCode(enabled: boolean) {
  return useQuery<ReferralCode>({
    queryKey: ['referral-code'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/referral/my-code`, { signal, headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load referral code')
      return r.json()
    },
    enabled,
  })
}

function useReferralStats(enabled: boolean) {
  return useQuery<ReferralStats>({
    queryKey: ['referral-stats'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/referral/stats`, { signal, headers: authHeaders() })
      if (!r.ok) throw new Error('Failed to load stats')
      return r.json()
    },
    enabled,
  })
}

function useLeaderboard() {
  return useQuery<{ leaderboard: LeaderboardEntry[] }>({
    queryKey: ['referral-leaderboard'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/referral/leaderboard?limit=10`, { signal })
      if (!r.ok) throw new Error('Failed to load leaderboard')
      return r.json()
    },
    staleTime: 60_000,
  })
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy}
      className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
        copied
          ? 'bg-green-400/10 text-green-300 border-green-400/30'
          : 'bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white')}>
      {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied!' : label}
    </button>
  )
}

function StatCard({ icon, label, value, accent = false }: { icon: ReactNode; label: string; value: string | number; accent?: boolean }) {
  return (
    <div className={cn('rounded-xl p-4 border flex items-start gap-3', accent ? 'bg-vit-400/10 border-vit-400/20' : 'bg-white/5 border-white/10')}>
      <div className={cn('p-2 rounded-lg', accent ? 'bg-vit-400/15 text-vit-300' : 'bg-white/10 text-white/60')}>{icon}</div>
      <div>
        <p className="text-xs text-white/40 mb-0.5">{label}</p>
        <p className={cn('text-xl font-bold', accent ? 'text-vit-300' : 'text-white')}>{value}</p>
      </div>
    </div>
  )
}

const HOW_IT_WORKS = [
  { step: '01', title: 'Share your code',    desc: 'Send your unique referral link to friends, followers, or your community.' },
  { step: '02', title: 'Friend signs up',    desc: 'They register on VitNetwork using your code and receive a 50 VIT welcome bonus.' },
  { step: '03', title: 'Earn rewards',       desc: 'Earn 10% commission on every deposit and subscription your referee makes — forever.' },
]

const REWARD_TIERS = [
  { icon: <Gift className="w-5 h-5" />,       label: 'Sign-up Bonus',      value: '50 VIT', desc: 'Paid when your referee completes registration', color: 'text-green-300 bg-green-400/10' },
  { icon: <Zap className="w-5 h-5" />,        label: 'Deposit Commission', value: '10%',    desc: 'Of every fiat deposit your referee makes',     color: 'text-vit-300 bg-vit-400/10' },
  { icon: <TrendingUp className="w-5 h-5" />, label: 'Subscription Share', value: '10%',    desc: 'Of any subscription plan your referee takes',  color: 'text-blue-300 bg-blue-400/10' },
]

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Referral() {
  const isAuth   = !!getAuthToken()
  const navigate = useNavigate()

  const { data: codeData, isLoading: codeLoading } = useMyCode(isAuth)
  const { data: stats }                             = useReferralStats(isAuth)
  const { data: lbData, isLoading: lbLoading }     = useLeaderboard()
  const board = lbData?.leaderboard ?? []

  return (
    <div className="min-h-screen bg-[#07090f] text-white pt-20 pb-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">

        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 text-vit-400 text-sm font-semibold mb-3">
            <Share2 className="w-4 h-4" /> Referral & Affiliate
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">Earn While You Share</h1>
          <p className="text-white/50 max-w-xl">
            Invite friends to VitNetwork and earn VIT on every deposit and subscription they make — no cap, no expiry.
          </p>
        </div>

        {/* Referral code — auth gate */}
        {!isAuth ? (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 border border-white/10 rounded-2xl p-8 text-center mb-10">
            <Share2 className="w-10 h-10 mx-auto mb-3 text-vit-400 opacity-70" />
            <h2 className="text-xl font-semibold text-white mb-2">Get your referral code</h2>
            <p className="text-white/40 mb-5 text-sm">Sign in to access your unique referral link and start earning.</p>
            <button onClick={() => navigate('/login')}
              className="px-6 py-2.5 bg-vit-400 hover:bg-vit-300 text-black font-semibold rounded-xl transition-colors inline-flex items-center gap-2">
              Sign in <ArrowRight className="w-4 h-4" />
            </button>
          </motion.div>
        ) : codeLoading ? (
          <div className="flex items-center justify-center py-12"><Spinner className="w-8 h-8" /></div>
        ) : codeData ? (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-vit-400/10 via-transparent to-transparent border border-vit-400/20 rounded-2xl p-6 mb-8">
            <div className="flex items-start justify-between mb-6">
              <div>
                <p className="text-xs text-white/40 mb-1 uppercase tracking-wider">Your Referral Code</p>
                <p className="text-4xl font-mono font-bold text-vit-300 tracking-widest">{codeData.code}</p>
              </div>
              <div className="p-3 bg-vit-400/10 rounded-xl border border-vit-400/20">
                <Share2 className="w-6 h-6 text-vit-400" />
              </div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 flex items-center gap-3 mb-4">
              <ExternalLink className="w-4 h-4 text-white/30 flex-shrink-0" />
              <p className="text-sm text-white/50 font-mono truncate flex-1">{codeData.link}</p>
              <CopyButton text={codeData.link} label="Copy link" />
            </div>
            <div className="flex flex-wrap gap-3">
              <CopyButton text={codeData.code} label="Copy code" />
              <a href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(`Join me on VitNetwork — AI-powered sports predictions. Use my code ${codeData.code} for 50 VIT free! ${codeData.link}`)}`}
                target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-sky-500/10 text-sky-300 border border-sky-400/20 hover:bg-sky-500/20 transition-colors">
                <Share2 className="w-3.5 h-3.5" /> Share on X
              </a>
              <a href={`https://t.me/share/url?url=${encodeURIComponent(codeData.link)}&text=${encodeURIComponent(`Join VitNetwork with my code ${codeData.code} — get 50 VIT free!`)}`}
                target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-300 border border-blue-400/20 hover:bg-blue-500/20 transition-colors">
                <Share2 className="w-3.5 h-3.5" /> Share on Telegram
              </a>
            </div>
          </motion.div>
        ) : null}

        {/* Stats */}
        {isAuth && stats && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-10">
            <StatCard icon={<Users className="w-4 h-4" />}  label="Total Referrals"  value={stats.total}                  accent />
            <StatCard icon={<Gift className="w-4 h-4" />}    label="VIT Earned"       value={`${stats.total * 50} VIT`} />
            <StatCard icon={<Clock className="w-4 h-4" />}   label="Pending Bonuses"  value={stats.pending_bonuses} />
          </div>
        )}

        {/* How it works */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-white mb-5">How it Works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {HOW_IT_WORKS.map(s => (
              <div key={s.step} className="bg-white/[0.03] border border-white/10 rounded-xl p-5 relative overflow-hidden">
                <p className="text-5xl font-black text-white/5 absolute top-2 right-3 leading-none select-none">{s.step}</p>
                <div className="w-7 h-7 rounded-full bg-vit-400/10 border border-vit-400/20 flex items-center justify-center mb-3">
                  <span className="text-xs font-bold text-vit-400">{s.step}</span>
                </div>
                <h3 className="font-semibold text-white mb-1">{s.title}</h3>
                <p className="text-sm text-white/40">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Reward tiers */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-white mb-5">Reward Structure</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {REWARD_TIERS.map(tier => (
              <div key={tier.label} className="bg-white/[0.03] border border-white/10 rounded-xl p-5">
                <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center mb-3', tier.color)}>{tier.icon}</div>
                <p className="text-2xl font-black text-white mb-1">{tier.value}</p>
                <p className="text-sm font-semibold text-white/80 mb-1">{tier.label}</p>
                <p className="text-xs text-white/40">{tier.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Referral history */}
        {isAuth && stats && stats.referrals.length > 0 && (
          <div className="mb-10">
            <h2 className="text-lg font-semibold text-white mb-4">Your Referrals</h2>
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
              <div className="grid grid-cols-3 px-4 py-2.5 text-xs font-semibold text-white/30 border-b border-white/10 uppercase tracking-wider">
                <span>User</span><span className="text-center">Joined</span><span className="text-right">Bonus</span>
              </div>
              <div className="divide-y divide-white/5">
                {stats.referrals.map((ref, i) => (
                  <div key={i} className="grid grid-cols-3 px-4 py-3 items-center">
                    <span className="text-sm text-white font-medium">{ref.username}</span>
                    <span className="text-xs text-white/40 text-center">{ref.joined_at ? new Date(ref.joined_at).toLocaleDateString() : '—'}</span>
                    <span className={cn('text-xs text-right font-medium', ref.bonus_paid ? 'text-green-400' : 'text-amber-400')}>
                      {ref.bonus_paid ? '✓ Paid' : 'Pending'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Leaderboard */}
        <div>
          <div className="flex items-center gap-2 mb-5">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white">Top Referrers</h2>
          </div>
          {lbLoading ? (
            <div className="flex items-center justify-center py-12"><Spinner className="w-8 h-8" /></div>
          ) : board.length === 0 ? (
            <div className="text-center py-12 bg-white/[0.03] border border-white/10 rounded-2xl text-white/30">
              <Trophy className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p>No referrals yet. Be the first!</p>
            </div>
          ) : (
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
              <div className="grid grid-cols-4 px-4 py-2.5 text-xs font-semibold text-white/30 border-b border-white/10 uppercase tracking-wider">
                <span>#</span><span>User</span><span className="text-right">Referrals</span><span className="text-right">VIT Earned</span>
              </div>
              <div className="divide-y divide-white/5">
                {board.map(entry => (
                  <div key={entry.rank} className={cn('grid grid-cols-4 px-4 py-3 items-center', entry.rank <= 3 && 'bg-amber-400/[0.03]')}>
                    <div className="flex items-center gap-2">
                      {entry.rank === 1 ? <Star className="w-4 h-4 text-amber-400 fill-amber-400" /> :
                       entry.rank === 2 ? <Star className="w-4 h-4 text-slate-400 fill-slate-400" /> :
                       entry.rank === 3 ? <Star className="w-4 h-4 text-amber-700 fill-amber-700" /> :
                       <span className="text-xs text-white/30 w-4 text-center">{entry.rank}</span>}
                    </div>
                    <span className={cn('text-sm font-semibold', entry.rank <= 3 ? 'text-white' : 'text-white/70')}>{entry.username}</span>
                    <span className="text-sm text-white/70 text-right">{entry.referrals}</span>
                    <span className="text-sm font-mono text-vit-300 text-right">{entry.earned_vit.toLocaleString()} VIT</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
