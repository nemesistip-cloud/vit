import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowRight, Brain, CircleAlert, LineChart, ShieldCheck, Layers, ExternalLink, Lock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ENDPOINTS } from '@/lib/api'
import { vitpredictApiPath } from '@/lib/vitpredictApi'

interface AppHealth {
  app_id: string
  status: string
  checks: Record<string, string>
}

interface AccumulatorLeg {
  match_id: number
  home_team: string
  away_team: string
  selection: string
  model_prob: number
  market_odds: number
}

interface AccumulatorData {
  legs?: AccumulatorLeg[]
  total_odds?: number
  expected_value?: number
  combined_probability?: number
  recommended_stake_pct?: number
  error?: string
}

export default function VITPredictApp() {
  const health = useQuery<AppHealth>({
    queryKey: ['vitpredict-health'],
    queryFn: async ({ signal }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/apps/vitpredict/health`, { signal })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail?.status ?? `Health check unavailable (${response.status})`)
      return data
    },
    retry: false,
    refetchInterval: 60_000,
  })

  const accumulator = useQuery<AccumulatorData>({
    queryKey: ['vitpredict-daily-accumulator'],
    queryFn: async ({ signal }) => {
      const response = await fetch(`${ENDPOINTS.gateway}${vitpredictApiPath('/api/predict/accumulator?limit=3')}`, { signal })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail ?? `Forecast shortlist unavailable (${response.status})`)
      return data
    },
    retry: false,
  })

  const features = [
    { icon: Activity, title: 'Fixtures and match history', description: 'Explore upcoming football fixtures, results, and historical context.', to: '/apps/vitpredict/matches' },
    { icon: Brain, title: 'Prediction intelligence', description: 'Review forecast probabilities, provenance, and data-quality warnings.', to: '/apps/vitpredict/predictions' },
    { icon: LineChart, title: 'Data and evaluation', description: 'Inspect odds provenance and measure model performance.', to: '/apps/vitpredict/odds' },
  ]

  return (
    <div className="space-y-10">
      <section className="grid gap-8 border-b border-white/10 pb-10 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
        <div>
          <p className="mb-3 text-xs font-semibold uppercase text-emerald-300/75">VIT Network application</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight sm:text-5xl">VITPredict</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-white/60">Football prediction intelligence for fixtures, market context, forecast probabilities, and verified model evaluation.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/apps/vitpredict/matches" className="inline-flex items-center gap-2 rounded-md bg-emerald-300 px-4 py-2.5 text-sm font-semibold text-[#092018] hover:bg-emerald-200">Explore fixtures <ArrowRight className="h-4 w-4" /></Link>
            <Link to="/applications" className="inline-flex items-center gap-2 rounded-md border border-white/15 px-4 py-2.5 text-sm text-white/70 hover:bg-white/5">VIT Network applications</Link>
          </div>
        </div>
        <aside aria-live="polite" className="border-l-2 border-emerald-300/50 bg-white/[0.025] px-4 py-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-white/45"><ShieldCheck className="h-4 w-4" /> Application health</div>
          {health.isPending ? <p className="mt-3 text-sm text-white/45">Checking shared services…</p> : health.isError ? (
            <div role="status" className="mt-3 flex items-center gap-2 text-sm text-amber-200"><CircleAlert className="h-4 w-4" /> Status unavailable</div>
          ) : (
            <div className="mt-3 space-y-2">
              <p className="text-sm font-medium text-emerald-200">{health.data.status}</p>
              {Object.entries(health.data.checks).map(([name, status]) => <p key={name} className="flex justify-between gap-4 text-xs text-white/50"><span className="capitalize">{name}</span><span>{status}</span></p>)}
            </div>
          )}
        </aside>
      </section>

      {/* Daily forecast shortlist */}
      <section className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-6 backdrop-blur-sm">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/15 text-emerald-300">
              <Layers className="h-4 w-4" />
            </span>
            <div>
              <h3 className="font-semibold text-white">Daily Forecast Shortlist</h3>
              <p className="text-xs text-white/50">Stored model probabilities and available market prices; not an LLM-generated forecast</p>
            </div>
          </div>
          {accumulator.data?.total_odds && (
            <div className="text-right">
              <span className="text-xs text-white/40 block">Indicative combined odds</span>
              <span className="text-lg font-bold text-emerald-300">{accumulator.data.total_odds.toFixed(2)}x</span>
            </div>
          )}
        </div>

        {accumulator.isPending ? (
          <p className="text-xs text-white/40 py-2">Loading stored forecasts and market data...</p>
        ) : accumulator.isError ? (
          <p role="status" className="text-xs text-amber-200 py-2">
            Forecast shortlist is unavailable. {accumulator.error instanceof Error ? accumulator.error.message : 'Try again later.'}
          </p>
        ) : accumulator.data?.error ? (
          <p role="status" className="text-xs text-amber-200 py-2">{accumulator.data.error}</p>
        ) : accumulator.data?.legs && accumulator.data.legs.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-3 mt-4">
            {accumulator.data.legs.map((leg, i) => (
              <div key={i} className="rounded-lg border border-white/10 bg-white/5 p-3.5 text-xs">
                <div className="flex justify-between font-medium text-white/90 mb-1">
                  <span>{leg.home_team} vs {leg.away_team}</span>
                  <span className="text-emerald-300 font-semibold">{(leg.market_odds || 1.0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-white/50">
                  <span>Selection: <strong className="text-white/80 capitalize">{leg.selection}</strong></span>
                  <span>Model: {((leg.model_prob || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-white/40 py-2">No qualifying forecast combinations are available for today.</p>
        )}
      </section>

      <section aria-labelledby="vitpredict-capabilities">
        <div className="mb-4 flex items-end justify-between gap-4"><div><p className="text-xs uppercase text-white/35">Workspace</p><h2 id="vitpredict-capabilities" className="mt-1 text-xl font-semibold">Prediction intelligence</h2></div><span className="text-xs text-white/35">App ID: app:vitpredict</span></div>
        <div className="divide-y divide-white/10 border-y border-white/10">
          {features.map(({ icon: Icon, title, description, to }) => (
            <Link key={title} to={to} className="group flex items-center gap-4 py-5 transition hover:bg-white/[0.025]">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-emerald-300/15 text-emerald-200"><Icon className="h-5 w-5" /></span>
              <span className="min-w-0 flex-1"><span className="block font-medium">{title}</span><span className="mt-1 block text-sm text-white/50">{description}</span></span>
              <ArrowRight className="h-4 w-4 shrink-0 text-white/30 transition group-hover:translate-x-1 group-hover:text-emerald-200" />
            </Link>
          ))}
        </div>

        {/* Wallet Segregation & Regulatory Disclaimer */}
        <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.02] p-4 text-xs text-white/50 flex gap-3 items-start">
          <Lock className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
          <div>
            <span className="font-medium text-white/80 block mb-0.5">Sports Market Wallet Protection</span>
            VITPredict provides AI analysis and model forecasts only. In strict accordance with VIT platform policy, sports markets do not process deposits, withdrawals, or direct wallet wagers. External execution is handled via licensed affiliate partner links.
          </div>
        </div>
      </section>
    </div>
  )
}
