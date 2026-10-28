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
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'
import { cn } from '@/lib/utils'

function useNavigationShell() {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [navigationOpen, setNavigationOpen] = useState(false)
  const openPalette = useCallback(() => setPaletteOpen(true), [])
  const closeNavigation = useCallback(() => setNavigationOpen(false), [])
  const toggleNavigation = useCallback(() => setNavigationOpen((value) => !value), [])

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

  return {
    paletteOpen,
    setPaletteOpen,
    openPalette,
    navigationOpen,
    closeNavigation,
    toggleNavigation,
  }
}

export function AppShell() {
  const {
    paletteOpen,
    setPaletteOpen,
    openPalette,
    navigationOpen,
    closeNavigation,
    toggleNavigation,
  } = useNavigationShell()
  const location = useLocation()
  const workspace = useWorkspaceStore()
  const sidebarCollapsed = workspace.sidebar.collapsed

  useEffect(() => {
    workspaceStoreInstance.setCurrentRoute(location.pathname)
    closeNavigation()
  }, [location.pathname, closeNavigation])

  return (
    <ErrorBoundary>
      <div className="min-h-screen flex flex-col bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.08),_transparent_35%)]">
        <Navbar
          onOpenSearch={openPalette}
          navigationOpen={navigationOpen}
          onToggleNavigation={toggleNavigation}
        />
        <Sidebar open={navigationOpen} onClose={closeNavigation} isAuthenticated />
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />

        <main className={cn(
          'flex-1 pt-16 transition-[padding] duration-200',
          sidebarCollapsed ? 'lg:pl-[56px]' : 'lg:pl-[220px]',
        )}>
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <div className="panel panel-glow mb-6 flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <Breadcrumbs className="text-sm" />
              <Link
                to="/assistant"
                className="btn-vit inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium bg-vit-500/90 hover:bg-vit-400"
              >
                <Sparkles className="h-4 w-4" />
                Open Assistant
              </Link>
            </div>
            <Outlet />
          </div>
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
    </ErrorBoundary>
  )
}

export function PublicShell() {
  const {
    paletteOpen,
    setPaletteOpen,
    openPalette,
    navigationOpen,
    closeNavigation,
    toggleNavigation,
  } = useNavigationShell()

  return (
    <div className="min-h-screen flex flex-col bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.08),_transparent_35%)]">
      <Navbar
        onOpenSearch={openPalette}
        navigationOpen={navigationOpen}
        onToggleNavigation={toggleNavigation}
        showPublicNavigation
      />
      <Sidebar open={navigationOpen} onClose={closeNavigation} isAuthenticated={false} />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
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
