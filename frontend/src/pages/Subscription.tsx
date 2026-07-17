import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  CheckCircle2, Zap, BarChart3, Shield, Star, Crown, AlertCircle,
  ChevronRight, Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ENDPOINTS } from '@/lib/api'
import { authHeaders, getAuthToken } from '@/hooks/useAuth'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Plan {
  id: string
  name: string
  price_usd: number
  price_monthly?: number
  tier: string
  features: string[]
  highlight?: boolean
  description?: string
}

// ── Default plans (shown when /api/subscription/plans is unavailable) ─────────

const DEFAULT_PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price_usd: 0,
    tier: 'viewer',
    description: 'Get started with the basics.',
    features: [
      'Access to public matches',
      'Basic leaderboard view',
      'Community forum access',
      'VIT wallet (receive only)',
    ],
  },
  {
    id: 'analyst',
    name: 'Analyst',
    price_usd: 19,
    tier: 'analyst',
    description: 'For serious predictors.',
    features: [
      'Everything in Free',
      'AI match predictions',
      'Confidence & EV scores',
      'Prediction history',
      'Analytics Studio access',
      'Wallet send & receive',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price_usd: 49,
    tier: 'pro',
    highlight: true,
    description: 'Full platform access.',
    features: [
      'Everything in Analyst',
      'In-Play live markets',
      'DeFi pools & staking',
      'Governance voting',
      'Marketplace — buy signals',
      'Priority support',
      'API access (1K req/day)',
    ],
  },
  {
    id: 'elite',
    name: 'Elite',
    price_usd: 149,
    tier: 'elite',
    description: 'For institutional participants.',
    features: [
      'Everything in Pro',
      'Unlimited API access',
      'Enterprise webhooks',
      'Custom data bundles',
      'Dedicated account manager',
      'Marketplace — sell signals',
      'Validator node eligibility',
    ],
  },
]

const TIER_ICON: Record<string, React.ElementType> = {
  viewer:  Shield,
  analyst: BarChart3,
  pro:     Zap,
  elite:   Crown,
}

const TIER_COLOR: Record<string, string> = {
  viewer:  'text-white/50',
  analyst: 'text-blue-400',
  pro:     'text-vit-400',
  elite:   'text-amber-400',
}

const TIER_BORDER: Record<string, string> = {
  viewer:  'border-white/8',
  analyst: 'border-blue-500/25',
  pro:     'border-vit-500/40',
  elite:   'border-amber-500/30',
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function usePlans() {
  return useQuery<Plan[]>({
    queryKey: ['subscription-plans'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/subscription/plans`, { signal })
      if (!r.ok) return DEFAULT_PLANS
      const d = await r.json()
      return Array.isArray(d) ? d : d.plans ?? DEFAULT_PLANS
    },
    staleTime: 300_000,
    placeholderData: DEFAULT_PLANS,
  })
}

function useCurrentSub() {
  return useQuery({
    queryKey: ['my-subscription'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/subscription/me`, { signal, headers: authHeaders() })
      return r.ok ? r.json() : null
    },
    enabled: !!getAuthToken(),
    retry: false,
    staleTime: 60_000,
  })
}

// ── Plan Card ─────────────────────────────────────────────────────────────────

function PlanCard({
  plan,
  current,
  onUpgrade,
  pending,
}: {
  plan: Plan
  current?: string
  onUpgrade: (id: string) => void
  pending: boolean
}) {
  const Icon     = TIER_ICON[plan.tier] ?? Star
  const isCurrent = current === plan.tier || current === plan.id
  const isHigher = plan.price_usd > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'relative flex flex-col rounded-2xl border p-6 transition-all',
        TIER_BORDER[plan.tier],
        plan.highlight
          ? 'bg-vit-500/8 shadow-lg shadow-vit-500/10'
          : 'bg-surface-800/50',
      )}
    >
      {plan.highlight && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-vit-600 text-white text-xs font-semibold shadow">
          Most popular
        </div>
      )}

      <div className="flex items-center gap-2.5 mb-3">
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center bg-white/5', TIER_COLOR[plan.tier])}>
          <Icon className="w-4 h-4" />
        </div>
        <h3 className="font-bold text-white">{plan.name}</h3>
      </div>

      <div className="mb-2">
        <span className={cn('text-3xl font-bold', TIER_COLOR[plan.tier])}>
          {plan.price_usd === 0 ? 'Free' : `$${plan.price_usd}`}
        </span>
        {plan.price_usd > 0 && <span className="text-white/35 text-sm ml-1">/month</span>}
      </div>

      {plan.description && (
        <p className="text-xs text-white/40 mb-5">{plan.description}</p>
      )}

      <ul className="space-y-2.5 flex-1 mb-6">
        {plan.features.map(f => (
          <li key={f} className="flex items-start gap-2 text-sm text-white/70">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            {f}
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-white/5 text-white/50 text-sm font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          Current plan
        </div>
      ) : (
        <button
          onClick={() => onUpgrade(plan.id)}
          disabled={pending || !getAuthToken()}
          className={cn(
            'flex items-center justify-center gap-2 w-full py-2.5 rounded-lg font-semibold text-sm transition-colors',
            plan.highlight
              ? 'bg-vit-600 text-white hover:bg-vit-500'
              : 'bg-white/8 text-white hover:bg-white/12',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          {pending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
          {!getAuthToken() ? 'Sign in to upgrade' : plan.price_usd === 0 ? 'Downgrade' : 'Upgrade'}
        </button>
      )}
    </motion.div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Subscription() {
  const { data: plans = DEFAULT_PLANS } = usePlans()
  const { data: sub } = useCurrentSub()
  const [pendingId, setPendingId] = useState<string | null>(null)

  const upgradeMutation = useMutation({
    mutationFn: async (planId: string) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/subscription/upgrade`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: planId }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Upgrade failed')
      return d
    },
    onSuccess: d => {
      setPendingId(null)
      if (d.payment_url) {
        toast.info('Redirecting to payment…')
        setTimeout(() => { window.location.href = d.payment_url }, 800)
      } else {
        toast.success('Plan upgraded successfully')
      }
    },
    onError: (e: Error) => { setPendingId(null); toast.error(e.message) },
  })

  function upgrade(planId: string) {
    if (!getAuthToken()) { toast.error('Please sign in to upgrade'); return }
    setPendingId(planId)
    upgradeMutation.mutate(planId)
  }

  return (
    <div className="pt-20 pb-20 min-h-screen relative">
      <div className="absolute inset-0 section-grid opacity-20 pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-vit-500/10 border border-vit-500/20 mb-4">
            <Star className="w-3.5 h-3.5 text-vit-400" />
            <span className="text-xs font-medium text-vit-400">Subscription Plans</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">Choose your plan</h1>
          <p className="text-white/45 text-sm max-w-md mx-auto">
            Start free and upgrade as you grow. All paid plans include a 7-day free trial.
          </p>
          {sub && (
            <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-white/60">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Current plan: <span className="text-white font-medium capitalize">{sub.tier ?? sub.plan_name ?? 'Free'}</span>
            </div>
          )}
        </motion.div>

        {/* Plan grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {plans.map(plan => (
            <PlanCard
              key={plan.id}
              plan={plan}
              current={sub?.tier ?? sub?.plan_id}
              onUpgrade={upgrade}
              pending={pendingId === plan.id && upgradeMutation.isPending}
            />
          ))}
        </div>

        {/* FAQs */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mt-16 bg-surface-800/40 border border-white/8 rounded-2xl p-8"
        >
          <h2 className="font-bold text-white mb-6">Frequently asked questions</h2>
          <div className="grid sm:grid-cols-2 gap-6">
            {[
              { q: 'Can I change plans anytime?', a: 'Yes. Upgrades take effect immediately; downgrades apply at the next billing cycle.' },
              { q: 'What payment methods are accepted?', a: 'We accept cards, bank transfers, and VITCoin payments via our payment partners.' },
              { q: 'Is there a free trial?', a: 'All paid plans include a 7-day free trial. No card required for the Free plan.' },
              { q: 'How do I cancel?', a: 'Cancel anytime from your account settings. You keep access until the end of your billing period.' },
            ].map(faq => (
              <div key={faq.q}>
                <h4 className="text-sm font-semibold text-white mb-1.5">{faq.q}</h4>
                <p className="text-xs text-white/45 leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
