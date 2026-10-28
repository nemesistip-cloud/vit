import { Link, NavLink, Outlet } from 'react-router-dom'
import { ArrowLeft, Brain } from 'lucide-react'
import { Toaster } from 'sonner'
import { cn } from '@/lib/utils'
import { ROUTES, VITPREDICT_NAVIGATION_ITEMS } from '@/lib/navigation'

export function VITPredictShell() {
  return (
    <div className="min-h-screen bg-[#0b1118] text-white">
      <header className="border-b border-white/10 bg-[#101922]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-4">
            <Link to={ROUTES.applications} className="inline-flex items-center gap-1.5 text-xs text-white/50 transition hover:text-white">
              <ArrowLeft className="h-3.5 w-3.5" /> VIT Network
            </Link>
            <span className="h-5 w-px bg-white/10" />
            <Link to={ROUTES.vitpredict} className="flex items-center gap-2 font-semibold tracking-normal">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/15 text-emerald-300">
                <Brain className="h-4 w-4" />
              </span>
              <span>VITPredict</span>
              <span className="rounded border border-emerald-400/25 px-1.5 py-0.5 text-[9px] font-medium uppercase text-emerald-300/80">App</span>
            </Link>
          </div>
          <nav aria-label="VITPredict navigation" className="flex max-w-full gap-1 overflow-x-auto">
            {VITPREDICT_NAVIGATION_ITEMS.map(({ id, path, label, icon: Icon, end }) => (
              <NavLink
                key={id}
                to={path}
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
        <Link to={ROUTES.applications} className="ml-2 text-emerald-300/80 hover:text-emerald-200">All applications</Link>
      </footer>
      <Toaster theme="dark" position="bottom-right" />
    </div>
  )
}