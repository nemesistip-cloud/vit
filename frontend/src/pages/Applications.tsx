import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Boxes, CircleAlert, ExternalLink, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ENDPOINTS } from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'

interface ApplicationSummary {
  id: string
  slug: string
  name: string
  description: string
  category: string
  availability: 'available' | 'preview' | 'unavailable'
  integration_status: string
  version: string
  launch_path: string
  launch_url?: string | null
}

export default function Applications() {
  const apps = useQuery<ApplicationSummary[]>({
    queryKey: ['ecosystem-applications'],
    queryFn: async ({ signal }) => {
      const response = await fetch(`${ENDPOINTS.gateway}/api/apps`, { signal })
      if (!response.ok) throw new Error(`Application catalog unavailable (${response.status})`)
      const payload = await response.json()
      if (!Array.isArray(payload)) throw new Error('Application catalog returned an invalid response')
      return payload
    },
    retry: 1,
    staleTime: 60_000,
  })

  return (
    <div className="space-y-8">
      <header className="border-b border-white/10 pb-7">
        <p className="mb-2 text-xs font-semibold uppercase text-emerald-300/75">VIT Network</p>
        <h1 className="text-3xl font-semibold">Applications</h1>
        <p className="mt-2 max-w-2xl text-sm text-white/55">Independent products built on shared VIT identity and network services.</p>
      </header>

      {apps.isPending ? (
        <div className="flex min-h-40 items-center justify-center"><Spinner className="h-6 w-6 text-emerald-300" /></div>
      ) : apps.isError ? (
        <div role="alert" className="flex items-start justify-between gap-4 border-l-2 border-amber-400 bg-amber-400/5 px-4 py-4">
          <div className="flex gap-3"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" /><div><p className="text-sm font-medium">Applications could not be loaded</p><p className="mt-1 text-xs text-white/50">{apps.error.message}</p></div></div>
          <button type="button" onClick={() => void apps.refetch()} aria-label="Retry application catalog" className="rounded p-2 text-white/60 hover:bg-white/10 hover:text-white"><RefreshCw className="h-4 w-4" /></button>
        </div>
      ) : apps.data?.length ? (
        <ul className="divide-y divide-white/10 border-y border-white/10">
          {apps.data.map(app => (
            <li key={app.id} className="grid gap-4 py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <div className="flex gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-emerald-300/20 bg-emerald-300/8 text-emerald-200"><Boxes className="h-5 w-5" /></span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold">{app.name}</h2><span className="rounded border border-white/10 px-1.5 py-0.5 text-[10px] text-white/45">v{app.version}</span><span className="text-[10px] uppercase text-emerald-300/75">{app.integration_status}</span></div>
                  <p className="mt-1 max-w-2xl text-sm text-white/55">{app.description}</p>
                  <p className="mt-2 text-[11px] text-white/35">{app.category.replace(/-/g, ' ')} · {app.availability}</p>
                </div>
              </div>
              {app.launch_url ? (
                <a href={app.launch_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-md border border-white/15 px-3 py-2 text-sm font-medium text-white/75 transition hover:bg-white/5">
                  Launch <ExternalLink className="h-4 w-4" />
                </a>
              ) : (
                <Link to={app.launch_path} className="inline-flex items-center justify-center gap-2 rounded-md border border-emerald-300/25 px-3 py-2 text-sm font-medium text-emerald-200 transition hover:bg-emerald-300/10">
                  Launch <ArrowRight className="h-4 w-4" /><ExternalLink className="h-3 w-3 opacity-50" />
                </Link>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="border-y border-white/10 py-8 text-sm text-white/50">No applications are currently available.</p>
      )}
    </div>
  )
}