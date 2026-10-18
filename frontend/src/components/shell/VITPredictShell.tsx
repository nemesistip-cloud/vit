import { Link, NavLink, Outlet } from 'react-router-dom'
import { Activity, ArrowLeft, Brain, ChartNoAxesCombined, Compass, LineChart, ShieldCheck } from 'lucide-react'
import { Toaster } from 'sonner'
import { cn } from '@/lib/utils'

const APP_LINKS = [
  { to: '/apps/vitpredict', label: 'Overview', icon: Compass, end: true },
  { to: '/apps/vitpredict/home', label: 'Insights', icon: Brain },
  { to: '/apps/vitpredict/matches', label: 'Fixtures', icon: Activity },
  { to: '/apps/vitpredict/predictions', label: 'Predictions', icon: Brain },
  { to: '/apps/vitpredict/odds', label: 'Odds data', icon: LineChart },
  { to: '/apps/vitpredict/analytics', label: 'Evaluation', icon: ChartNoAxesCombined },
  { to: '/apps/vitpredict/verification', label: 'Verification', icon: ShieldCheck },
]

export function VITPredictShell() {
  return (
    <div className="min-h-screen bg-[#0b1118] text-white">
      <header className="border-b border-white/10 bg-[#101922]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-4">
            <Link to="/applications" className="inline-flex items-center gap-1.5 text-xs text-white/50 transition hover:text-white">
              <ArrowLeft className="h-3.5 w-3.5" /> VIT Network
            </Link>
            <span className="h-5 w-px bg-white/10" />
            <Link to="/apps/vitpredict" className="flex items-center gap-2 font-semibold tracking-normal">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/15 text-emerald-300">
                <Brain className="h-4 w-4" />
              </span>
              <span>VITPredict</span>
              <span className="rounded border border-emerald-400/25 px-1.5 py-0.5 text-[9px] font-medium uppercase text-emerald-300/80">App</span>
            </Link>
          </div>
          <nav aria-label="VITPredict" className="flex max-w-full gap-1 overflow-x-auto">
            {APP_LINKS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) => cn(
                  'inline-flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors',
                  isActive ? 'bg-emerald-400/12 text-emerald-200' : 'text-white/55 hover:bg-white/5 hover:text-white',
                )}
              >
                <Icon className="h-3.5 w-3.5" /> {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto min-h-[70vh] max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
        <Outlet />
      </main>
      <footer className="border-t border-white/8 px-4 py-5 text-center text-xs text-white/35">
        VITPredict is an application in the VIT Network ecosystem.
        <Link to="/applications" className="ml-2 text-emerald-300/80 hover:text-emerald-200">All applications</Link>
      </footer>
      <Toaster theme="dark" position="bottom-right" />
    </div>
  )
}