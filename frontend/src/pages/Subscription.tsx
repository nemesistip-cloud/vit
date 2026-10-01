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
  display_name: string
  price_monthly: number
  price_yearly: number
  tier: string
  features: string[]
  description?: string
}

type BillingPeriod = 'monthly' | 'yearly'

const FEATURE_LABELS: Record<string, string> = {
  predictions: 'Predictions',
  basic_history: 'Prediction history',
  advanced_analytics: 'Advanced analytics',
  ai_insights: 'AI insights',
  accumulator_builder: 'Accumulator builder',
  model_breakdown: 'Model breakdown',
  telegram_alerts: 'Telegram alerts',
  bankroll_tools: 'Bankroll tools',
  csv_upload: 'CSV upload',
  priority_support: 'Priority support',
  submit_predictions: 'Submit predictions',
  validator_rewards: 'Validator rewards',
  governance_voting: 'Governance voting',
  over_under: 'Over/under market',
  btts: 'Both teams to score',
  asian_handicap: 'Asian handicap',
}

const TIER_ICON: Record<string, React.ElementType> = {
  free:    Shield,
  analyst: BarChart3,
  pro:     Zap,
  validator: Crown,
}

const TIER_COLOR: Record<string, string> = {
  free:    'text-white/50',
  analyst: 'text-blue-400',
  pro:     'text-vit-400',
  validator: 'text-amber-400',
}

const TIER_BORDER: Record<string, string> = {
  free:    'border-white/8',
  analyst: 'border-blue-500/25',
  pro:     'border-vit-500/40',
  validator: 'border-amber-500/30',
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

function usePlans() {
  return useQuery<Plan[]>({
    queryKey: ['subscription-plans'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/subscription/plans`, { signal })
      if (!r.ok) throw new Error(`Subscription plans could not be loaded (${r.status})`)
      const d = await r.json()
      const rawPlans = Array.isArray(d) ? d : d.plans
      if (!Array.isArray(rawPlans)) throw new Error('Subscription catalog returned an invalid response')
      return rawPlans.map((plan: any) => {
        if (typeof plan.name !== 'string' || typeof plan.display_name !== 'string') {
          throw new Error('Subscription catalog returned an invalid plan')
        }
        const enabledFeatures = Object.entries(plan.features ?? {})
          .filter(([, enabled]) => enabled === true)
          .map(([key]) => FEATURE_LABELS[key] ?? key.replace(/_/g, ' '))
        return {
          id: plan.name,
          name: plan.name,
          display_name: plan.display_name,
          price_monthly: Number(plan.price_monthly),
          price_yearly: Number(plan.price_yearly),
          tier: plan.name,
          features: enabledFeatures,
          description: typeof plan.description === 'string' ? plan.description : undefined,
        }
      })
    },
    staleTime: 300_000,
  })
}

function useCurrentSub() {
  return useQuery({
    queryKey: ['my-subscription'],
    queryFn: async ({ signal }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/subscription/my-plan`, { signal, headers: authHeaders() })
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
  billing,
  onUpgrade,
  pending,
}: {
  plan: Plan
  current?: string
  billing: BillingPeriod
  onUpgrade: (id: string, billing: BillingPeriod) => void
  pending: boolean
}) {
  const Icon     = TIER_ICON[plan.tier] ?? Star
  const isCurrent = current === plan.id
  const price = billing === 'yearly' ? plan.price_yearly : plan.price_monthly

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'relative flex flex-col rounded-2xl border p-6 transition-all',
        TIER_BORDER[plan.tier],
        'bg-surface-800/50',
      )}
    >
      <div className="flex items-center gap-2.5 mb-3">
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center bg-white/5', TIER_COLOR[plan.tier])}>
          <Icon className="w-4 h-4" />
        </div>
        <h3 className="font-bold text-white">{plan.display_name}</h3>
      </div>

      <div className="mb-2">
        <span className={cn('text-3xl font-bold', TIER_COLOR[plan.tier])}>
          {price === 0 ? 'Free' : `$${price}`}
        </span>
        {price > 0 && <span className="text-white/35 text-sm ml-1">/{billing === 'yearly' ? 'year' : 'month'}</span>}
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
      ) : price === 0 ? (
        <button type="button" disabled className="w-full py-2.5 rounded-lg bg-white/5 text-white/40 text-sm font-medium">
          Free plan
        </button>
      ) : (
        <button
          onClick={() => onUpgrade(plan.id, billing)}
          disabled={pending}
          className={cn(
            'flex items-center justify-center gap-2 w-full py-2.5 rounded-lg font-semibold text-sm transition-colors',
            'bg-vit-600 text-white hover:bg-vit-500',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          {pending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
          Continue to checkout
        </button>
      )}
    </motion.div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Subscription() {
  const { data: plans, isLoading: plansLoading, error: plansError, refetch } = usePlans()
  const { data: sub } = useCurrentSub()
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [billing, setBilling] = useState<BillingPeriod>('monthly')

  const upgradeMutation = useMutation({
    mutationFn: async ({ plan, billing }: { plan: string; billing: BillingPeriod }) => {
      const r = await fetch(`${ENDPOINTS.gateway}/api/subscription/create-checkout`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan, billing }),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.detail ?? d.message ?? 'Upgrade failed')
      if (typeof d.checkout_url !== 'string') {
        throw new Error('Checkout did not return a secure payment URL')
      }
      const checkoutUrl = new URL(d.checkout_url)
      if (checkoutUrl.protocol !== 'https:' || !/(^|\.)paystack\.com$/i.test(checkoutUrl.hostname)) {
        throw new Error('Checkout returned an untrusted payment URL')
      }
      return { ...d, checkout_url: checkoutUrl.toString() }
    },
    onSuccess: d => {
      setPendingId(null)
      toast.info('Redirecting to Paystack checkout…')
      setTimeout(() => { window.location.assign(d.checkout_url) }, 800)
    },
    onError: (e: Error) => { setPendingId(null); toast.error(e.message) },
  })

  function upgrade(planId: string, selectedBilling: BillingPeriod) {
    setPendingId(planId)
    upgradeMutation.mutate({ plan: planId, billing: selectedBilling })
  }

  const currentPlan = sub?.plan?.name ?? sub?.plan_name

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
            Compare the current VIT Network plans and pricing.
          </p>
          {sub && (
            <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-white/60">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Current plan: <span className="text-white font-medium">{sub.plan?.display_name ?? sub.plan?.name ?? sub.plan_name ?? 'Free'}</span>
            </div>
          )}
        </motion.div>

        <div className="mb-6 flex justify-center">
          <div role="group" aria-label="Billing period" className="inline-flex rounded-lg border border-white/10 bg-white/5 p-1">
            {(['monthly', 'yearly'] as const).map(period => (
              <button
                key={period}
                type="button"
                aria-pressed={billing === period}
                onClick={() => setBilling(period)}
                className={cn('rounded-md px-4 py-2 text-sm capitalize transition-colors', billing === period ? 'bg-vit-500 text-white' : 'text-white/55 hover:text-white')}
              >
                {period}
              </button>
            ))}
          </div>
        </div>

        {/* Plan grid */}
        {plansLoading ? (
          <div role="status" className="py-12 text-center text-sm text-white/50">Loading current plans…</div>
        ) : plansError ? (
          <div role="alert" className="mx-auto max-w-lg rounded-xl border border-amber-500/25 bg-amber-500/10 p-5 text-center">
            <AlertCircle className="mx-auto mb-2 h-5 w-5 text-amber-300" />
            <p className="text-sm text-amber-100">Current plan pricing is unavailable. No fallback prices are shown.</p>
            <button type="button" onClick={() => void refetch()} className="mt-3 rounded-lg border border-amber-500/30 px-3 py-2 text-sm text-amber-100">Retry</button>
          </div>
        ) : !plans?.length ? (
          <p role="status" className="py-12 text-center text-sm text-white/50">No subscription plans are currently available.</p>
        ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {plans.map(plan => (
            <PlanCard
              key={plan.id}
              plan={plan}
              current={currentPlan}
              billing={billing}
              onUpgrade={upgrade}
              pending={pendingId === plan.id && upgradeMutation.isPending}
            />
          ))}
        </div>
        )}

        {/* FAQs */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mt-16 bg-surface-800/40 border border-white/8 rounded-2xl p-8"
        >
          <h2 className="font-bold text-white mb-6">Billing</h2>
          <div className="grid sm:grid-cols-2 gap-6">
            {[
              { q: 'How are paid plans billed?', a: 'Paid plans are billed in USD through Paystack. Choose monthly or yearly pricing above.' },
              { q: 'When does my plan change?', a: 'Your account updates after the payment provider confirms checkout.' },
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
