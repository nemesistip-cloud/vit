import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowRight, Brain, CircleAlert, LineChart, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ENDPOINTS } from '@/lib/api'

interface AppHealth {
  app_id: string
  status: string
  checks: Record<string, string>
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

  const features = [
    { icon: Activity, title: 'Fixtures and match history', description: 'Explore upcoming football fixtures, results, and historical context.', to: '/apps/vitpredict/matches' },
    { icon: Brain, title: 'Prediction intelligence', description: 'Review calibrated outcome probabilities and model explanations.', to: '/apps/vitpredict/predictions' },
    { icon: LineChart, title: 'Data and evaluation', description: 'Inspect odds provenance and measure model performance.', to: '/apps/vitpredict/odds' },
  ]

  return (
    <div className="space-y-10">
      <section className="grid gap-8 border-b border-white/10 pb-10 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
        <div>
          <p className="mb-3 text-xs font-semibold uppercase text-emerald-300/75">VIT Network application</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight sm:text-5xl">VITPredict</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-white/60">Football prediction intelligence for fixtures, market context, calibrated probabilities, and model evaluation.</p>
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
        <p className="mt-5 max-w-3xl text-xs leading-5 text-white/35">VITPredict provides analysis and forecasts, not wagers or bet placement. Identity is shared with VIT Network; application permissions and data ownership remain scoped to VITPredict.</p>
      </section>
    </div>
  )
}