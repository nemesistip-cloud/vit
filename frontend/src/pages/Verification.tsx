import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowRight, CheckCircle2, Clock3, ShieldCheck, Sparkles } from 'lucide-react'
import { ENDPOINTS } from '@/lib/api'
import { presentStoredPick } from '@/lib/pickPresentation'
import { Spinner } from '@/components/ui/Spinner'

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function useVerificationRecords() {
  return useQuery({
    queryKey: ['verification-records'],
    queryFn: async () => {
      const [upcomingRes, recentRes] = await Promise.all([
        fetch(`${ENDPOINTS.gateway}/api/matches/upcoming?limit=4`),
        fetch(`${ENDPOINTS.gateway}/api/matches/recent?limit=4`),
      ])

      const upcoming = upcomingRes.ok ? await upcomingRes.json() : []
      const recent = recentRes.ok ? await recentRes.json() : []
      const collection = [...Array.isArray(upcoming) ? upcoming : [], ...Array.isArray(recent) ? recent : []]

      return collection.slice(0, 6).map((match: any) => {
        const prediction = presentStoredPick(match)
        const homeScore = match?.home_score ?? match?.home_goals
        const awayScore = match?.away_score ?? match?.away_goals
        const hasScore = homeScore != null && awayScore != null
        const status = hasScore
          ? 'Verified'
          : match?.status === 'live' || match?.status === 'in_play'
            ? 'Live'
            : prediction.stateLabel

        return {
          id: match?.id ?? match?.match_id,
          match: `${match?.home_team ?? 'Home'} vs ${match?.away_team ?? 'Away'}`,
          kickoff: formatDate(match?.kickoff_time),
          pick: prediction.pickLabel,
          prob: prediction.probabilityLabel,
          predictionMessage: prediction.message,
          status,
          result: hasScore ? `Final score: ${homeScore}-${awayScore}` : 'Awaiting result',
        }
      })
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export default function Verification() {
  const { data: records = [], isLoading } = useVerificationRecords()

  return (
    <div className="pt-16 min-h-screen">
      <section className="border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-18" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-vit-500/25 bg-vit-500/10 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.2em] text-vit-300">
            <ShieldCheck className="w-3.5 h-3.5" />
            Public record
          </div>
          <h1 className="mt-6 text-4xl sm:text-5xl font-medium tracking-[-0.06em] text-white">See the seal. Check the record. Verify the outcome.</h1>
          <p className="mt-4 max-w-2xl text-base sm:text-lg text-white/65 leading-relaxed">
            Every pick is timestamped before kickoff and retained as a public record so it can be reviewed against the final result without ambiguity.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/matches" className="inline-flex items-center gap-2 rounded-xl bg-vit-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-vit-400 transition-colors">
              Explore live picks <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/status-page" className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white/75 hover:text-white transition-colors">
              Platform status
            </Link>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-16">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><Spinner className="h-8 w-8 text-vit-400" /></div>
        ) : records.length === 0 ? (
          <div className="rounded-2xl border border-white/8 bg-surface-800/60 p-6 text-center text-sm text-white/60">
            No public record entries are available yet.
          </div>
        ) : (
          <div className="grid lg:grid-cols-3 gap-5">
            {records.map((entry: any) => (
              <div key={entry.id ?? entry.match} className="rounded-2xl border border-white/8 bg-surface-800/60 p-6">
                <div className="flex items-center justify-between gap-3 mb-5">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-white/40">Match</p>
                    <h2 className="mt-2 text-xl font-medium text-white">{entry.match}</h2>
                  </div>
                  <span className={
                    entry.status === 'Verified'
                      ? 'rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-300'
                      : entry.status === 'Live'
                        ? 'rounded-full border border-amber-500/25 bg-amber-500/10 px-2 py-1 text-[10px] font-medium text-amber-300'
                        : entry.status === 'Unavailable'
                          ? 'rounded-full border border-rose-500/25 bg-rose-500/10 px-2 py-1 text-[10px] font-medium text-rose-300'
                          : 'rounded-full border border-vit-500/25 bg-vit-500/10 px-2 py-1 text-[10px] font-medium text-vit-300'
                  }>
                    {entry.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-5">
                  <div className="rounded-xl border border-white/8 bg-black/15 p-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-white/35">Pick</p>
                    <p className="mt-2 text-sm font-medium text-white">{entry.pick}</p>
                  </div>
                  <div className="rounded-xl border border-white/8 bg-black/15 p-3">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-white/35">Prob.</p>
                    <p className="mt-2 text-sm font-medium text-vit-300">{entry.prob}</p>
                  </div>
                </div>
                {entry.predictionMessage && (
                  <p className="mb-4 text-xs leading-relaxed text-white/55">{entry.predictionMessage}</p>
                )}

                <div className="space-y-2 text-sm text-white/60">
                  <div className="flex items-center justify-between gap-3">
                    <span>Match ID</span>
                    <span className="font-mono text-white/75">#{entry.id ?? '—'}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2"><Clock3 className="w-3.5 h-3.5 text-white/35" /> Kickoff</span>
                    <span className="text-white/75">{entry.kickoff}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Outcome</span>
                    <span className="text-white/75">{entry.result}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-20">
        <div className="rounded-3xl border border-white/8 bg-surface-800/50 p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-vit-300" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-white/35">How it works</p>
              <h2 className="text-2xl font-medium tracking-[-0.04em] text-white">Verification at a glance</h2>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            {[
              { title: '1. Seal the pick', text: 'The recommendation is timestamped and logged before kickoff, creating a public reference point.' },
              { title: '2. Publish the record', text: 'The pick, confidence, and seal id remain visible so anyone can inspect the claim later.' },
              { title: '3. Compare outcome', text: 'After the fixture closes, the final result is compared against the recorded prediction and rationale.' },
            ].map((step) => (
              <div key={step.title} className="rounded-2xl border border-white/8 bg-black/10 p-5">
                <div className="mb-3 text-xs uppercase tracking-[0.2em] text-vit-300">{step.title}</div>
                <p className="text-sm text-white/65 leading-relaxed">{step.text}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 text-sm text-emerald-300">
              <Activity className="w-4 h-4" />
              Live platform status is visible from the public status page.
            </div>
            <Link to="/status-page" className="text-sm text-white/80 hover:text-white transition-colors">Open status →</Link>
          </div>
        </div>
      </section>
    </div>
  )
}
