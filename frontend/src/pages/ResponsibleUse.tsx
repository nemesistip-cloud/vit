import { Link } from 'react-router-dom'
import { AlertTriangle, ShieldCheck, FileText, Gauge } from 'lucide-react'

const principles = [
  {
    icon: FileText,
    title: 'Record-first',
    body: 'Treat predictions as a public signal, not guaranteed profit. The platform is designed to make its record inspectable before and after a fixture.',
  },
  {
    icon: Gauge,
    title: 'Evidence over hype',
    body: 'Confidence scores, model context, and operational status should be read as context, not certainty. Live service health matters as much as any single pick.',
  },
  {
    icon: ShieldCheck,
    title: 'Responsible use',
    body: 'This tooling is for research, monitoring, and informed decision-making. It does not replace personal judgment, risk controls, or local compliance requirements.',
  },
]

export default function ResponsibleUse() {
  return (
    <div className="pt-16 min-h-screen">
      <section className="relative border-b border-white/8">
        <div className="absolute inset-0 section-grid opacity-20" />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 py-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/25 bg-amber-500/8 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.2em] text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5" />
            Responsible use
          </div>
          <h1 className="mt-6 text-4xl sm:text-5xl font-medium tracking-[-0.06em] text-white">Use the signal with context.</h1>
          <p className="mt-4 max-w-2xl text-base sm:text-lg text-white/65 leading-relaxed">
            VIT is a transparency and intelligence layer for public market signals. It is not a guarantee of profit, certainty, or regulatory approval.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid md:grid-cols-3 gap-5">
          {principles.map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-2xl border border-white/8 bg-surface-800/60 p-6">
              <div className="w-11 h-11 rounded-xl bg-vit-500/10 border border-vit-500/20 flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-vit-300" />
              </div>
              <h2 className="text-xl font-medium text-white mb-2">{title}</h2>
              <p className="text-sm leading-relaxed text-white/60">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-20">
        <div className="rounded-3xl border border-white/8 bg-surface-800/50 p-8">
          <h2 className="text-2xl font-medium tracking-[-0.04em] text-white mb-4">Important limits</h2>
          <ul className="space-y-3 text-sm text-white/65 leading-relaxed list-disc pl-5">
            <li>Signals and predictions are informational and should be reviewed alongside your own judgment and risk controls.</li>
            <li>Results can be affected by data quality, model limitations, schedule changes, and live operational constraints.</li>
            <li>Nothing in this platform should be interpreted as financial, legal, tax, or betting advice.</li>
            <li>Users remain responsible for understanding local laws, platform terms, and any compliance obligations relevant to their use.</li>
          </ul>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/status-page" className="inline-flex items-center gap-2 rounded-xl bg-vit-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-vit-400 transition-colors">
              Live status
            </Link>
            <Link to="/platform" className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white/70 hover:text-white transition-colors">
              Learn the platform
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
