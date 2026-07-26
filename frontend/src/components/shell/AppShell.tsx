import { useCallback, useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { Toaster } from 'sonner'
import { Navbar } from '@/components/layout/Navbar'
import { Sidebar } from '@/components/shell/Sidebar'
import { Footer } from '@/components/layout/Footer'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { CommandPalette } from '@/components/ui/CommandPalette'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { WorkspaceDock } from '@/components/shell/WorkspaceDock'
import { workspaceStoreInstance } from '@/lib/workspacePersistence'

export function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const openPalette = useCallback(() => setPaletteOpen(true), [])
  const location = useLocation()

  useEffect(() => {
    workspaceStoreInstance.setCurrentRoute(location.pathname)
  }, [location.pathname])

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen(v => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <ErrorBoundary>
      <div className="min-h-screen flex flex-col bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.08),_transparent_35%)]">
        <Navbar onOpenSearch={openPalette} />
        <Sidebar />
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />

        <main className="flex-1 pt-16 pb-24 lg:pl-[220px] transition-[padding] duration-200">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/8 bg-surface-900/70 px-4 py-3 backdrop-blur-xl">
              <Breadcrumbs className="text-sm" />
              <Link
                to="/assistant"
                className="inline-flex items-center gap-2 rounded-full border border-vit-500/20 bg-vit-500/10 px-3 py-1.5 text-sm font-medium text-vit-300 transition-colors hover:bg-vit-500/20"
              >
                <Sparkles className="h-4 w-4" />
                Open Assistant
              </Link>
            </div>
            <Outlet />
          </div>
        </main>

        <Footer />
        <WorkspaceDock />
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'hsl(var(--surface-800, 220 20% 14%))',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#fff',
            },
          }}
        />
      </div>
    </ErrorBoundary>
  )
}

export function PublicShell() {
  return (
    <div className="min-h-screen flex flex-col bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.08),_transparent_35%)]">
      <Navbar />
      <main className="flex-1 pt-16">
        <Outlet />
      </main>
      <Footer />
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'hsl(var(--surface-800, 220 20% 14%))',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#fff',
          },
        }}
      />
    </div>
  )
}
