import { Link } from 'react-router-dom'
import { Activity, ArrowRight, CheckCircle2, Clock3, ShieldCheck, Sparkles } from 'lucide-react'

const records = [
  {
    match: 'Arsenal vs Chelsea',
    sealed: '18:30 UK',
    pick: 'Home win',
    prob: '58%',
    status: 'Sealed',
    result: 'Final score: 2-1',
  },
  {
    match: 'Bayern vs Dortmund',
    sealed: '19:00 CET',
    pick: 'Draw',
    prob: '41%',
    status: 'Verified',
    result: 'Final score: 1-1',
  },
  {
    match: 'Inter vs Milan',
    sealed: '20:45 CET',
    pick: 'Away win',
    prob: '46%',
    status: 'Live',
    result: 'Awaiting result',
  },
]

export default function Verification() {
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
        <div className="grid lg:grid-cols-3 gap-5">
          {records.map((entry) => (
            <div key={entry.match} className="rounded-2xl border border-white/8 bg-surface-800/60 p-6">
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

              <div className="space-y-2 text-sm text-white/60">
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2"><Clock3 className="w-3.5 h-3.5 text-white/35" /> Sealed</span>
                  <span className="text-white/75">{entry.sealed}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Outcome</span>
                  <span className="text-white/75">{entry.result}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
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
