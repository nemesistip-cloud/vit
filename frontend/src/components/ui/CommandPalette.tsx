import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  Search,
  Sparkles,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getAuthToken, getStoredUser } from '@/hooks/useAuth'
import { getAppRegistry } from '@/lib/appRegistry'
import { getNavigationGroups } from '@/lib/navigation'
import { useWorkspaceStore } from '@/lib/workspacePersistence'
import { workspaceProcessManager } from '@/lib/processManager'

type PaletteItemType = 'navigation' | 'action'

interface PaletteItem {
  id: string
  type: PaletteItemType
  label: string
  sub: string
  path?: string
  icon: React.ElementType
}

interface Props {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const workspace = useWorkspaceStore()
  const isAuthenticated = Boolean(getAuthToken())
  const user = getStoredUser()
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  useEffect(() => {
    if (!open) return
    setQuery('')
    setCursor(0)
    window.setTimeout(() => inputRef.current?.focus(), 50)
  }, [open])

  useEffect(() => {
    setCursor(0)
  }, [query])

  const results = useMemo(() => {
    const navigationItems: PaletteItem[] = getNavigationGroups(isAuthenticated, isAdmin)
      .flatMap((group) => group.items)
      .map((item) => ({
        id: item.id,
        type: 'navigation',
        label: item.label,
        sub: item.path,
        path: item.path,
        icon: item.icon,
      }))

    const navigationPaths = new Set(navigationItems.map((item) => item.path))
    for (const app of getAppRegistry().filter((item) => item.category === 'Applications')) {
      if (navigationPaths.has(app.route)) continue
      navigationItems.push({
        id: `app-${app.id}`,
        type: 'navigation',
        label: app.name,
        sub: app.description,
        path: app.route,
        icon: app.icon,
      })
    }

    const actionItems: PaletteItem[] = []
    if (workspace.activeWindowId) {
      actionItems.push({
        id: 'action-focus',
        type: 'action',
        label: 'Focus active window',
        sub: 'Bring the current workspace window to the front',
        icon: Sparkles,
      })
      actionItems.push({
        id: 'action-close',
        type: 'action',
        label: 'Close active window',
        sub: 'Close the current workspace window',
        icon: X,
      })
    }

    const uniqueItems = [...navigationItems, ...actionItems]
      .filter((item, index, all) =>
        item.type === 'action' || all.findIndex((other) => other.type !== 'action' && other.path === item.path) === index,
      )

    if (!query.trim()) return uniqueItems.slice(0, 8)

    const normalizedQuery = query.trim().toLowerCase()
    return uniqueItems
      .filter((item) =>
        item.label.toLowerCase().includes(normalizedQuery) ||
        item.sub.toLowerCase().includes(normalizedQuery) ||
        item.type.toLowerCase().includes(normalizedQuery),
      )
      .slice(0, 10)
  }, [isAdmin, isAuthenticated, query, workspace])

  function handleSelection(item: PaletteItem) {
    if (item.type === 'navigation' && item.path) {
      navigate(item.path)
      onClose()
      return
    }

    if (item.id === 'action-focus' && workspace.activeWindowId) {
      const processId = Object.keys(workspace.processes ?? {}).find((candidate) =>
        workspace.processes?.[candidate]?.windowId === workspace.activeWindowId,
      )
      if (processId) workspaceProcessManager.focusProcess(processId)
    }

    if (item.id === 'action-close' && workspace.activeWindowId) {
      const processId = Object.keys(workspace.processes ?? {}).find((candidate) =>
        workspace.processes?.[candidate]?.windowId === workspace.activeWindowId,
      )
      if (processId) workspaceProcessManager.closeProcess(processId)
    }

    onClose()
  }

  function handleKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setCursor((current) => Math.min(current + 1, results.length - 1))
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setCursor((current) => Math.max(current - 1, 0))
    }
    if (event.key === 'Enter' && results[cursor]) {
      event.preventDefault()
      handleSelection(results[cursor])
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      onClose()
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="Close search"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          <div className="pointer-events-none fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto px-4 pt-[12vh]">
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Search navigation"
              initial={{ opacity: 0, scale: 0.98, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: -8 }}
              transition={{ duration: 0.15 }}
              className="pointer-events-auto w-full max-w-xl overflow-hidden rounded-2xl border border-white/12 bg-surface-900 shadow-2xl shadow-black/50"
            >
              <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3.5">
                <Search aria-hidden="true" className="h-4 w-4 shrink-0 text-white/35" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Search pages and applications"
                  aria-label="Search pages and applications"
                  className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder-white/30"
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => setQuery('')}
                    aria-label="Clear search"
                    className="rounded p-1 text-white/35 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
                  >
                    <X aria-hidden="true" className="h-4 w-4" />
                  </button>
                )}
                <kbd className="rounded bg-white/6 px-2 py-0.5 font-mono text-[10px] text-white/35">ESC</kbd>
              </div>

              <div className="max-h-[min(60vh,24rem)] overflow-y-auto py-2">
                {results.length === 0 && (
                  <div className="flex flex-col items-center justify-center gap-2 py-10">
                    <Activity aria-hidden="true" className="h-6 w-6 text-white/15" />
                    <p className="text-sm text-white/40">No results for “{query}”</p>
                  </div>
                )}

                {results.map((item, index) => {
                  const Icon = item.icon
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleSelection(item)}
                      aria-current={index === cursor ? 'true' : undefined}
                      className={cn(
                        'flex min-h-12 w-full items-center gap-3 px-4 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-vit-400',
                        index === cursor ? 'bg-white/8' : 'hover:bg-white/5',
                      )}
                    >
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5">
                        <Icon aria-hidden="true" className="h-4 w-4 text-white/50" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-white">{item.label}</span>
                        {item.sub && <span className="block truncate text-xs text-white/40">{item.sub}</span>}
                      </span>
                      <ArrowRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-white/25" />
                    </button>
                  )
                })}
              </div>

              <div className="flex items-center gap-4 border-t border-white/6 px-4 py-2.5 text-[10px] text-white/35">
                <span><kbd className="font-mono">↑↓</kbd> navigate</span>
                <span><kbd className="font-mono">↵</kbd> open</span>
                <span><kbd className="font-mono">esc</kbd> close</span>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
