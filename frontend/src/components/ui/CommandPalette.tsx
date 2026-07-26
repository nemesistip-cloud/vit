import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  Brain,
  LayoutDashboard,
  Search,
  Settings,
  Shield,
  Sparkles,
  Store,
  Trophy,
  Wallet,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getAppRegistry } from '@/lib/appRegistry'
import { useWorkspaceStore, workspaceStoreInstance } from '@/lib/workspacePersistence'

type PaletteItemType = 'app' | 'navigation' | 'action'

interface PaletteItem {
  id: string
  type: PaletteItemType
  label: string
  sub: string
  path: string
  icon: React.ElementType
  appId?: string
  windowId?: string
}

interface Props {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: Props) {
  const [q, setQ] = useState('')
  const [cursor, setCursor] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const workspace = useWorkspaceStore()

  useEffect(() => {
    if (open) {
      setQ('')
      setCursor(0)
      window.setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  useEffect(() => {
    setCursor(0)
  }, [q])

  const results = useMemo(() => {
    const registryItems = getAppRegistry().map((app) => {
      const openWindow = Object.values(workspace.windows).find((window) => window.appKey === app.id && window.visible)
      return {
        id: `app-${app.id}`,
        type: 'app' as const,
        label: openWindow ? `${app.name} (open)` : app.name,
        sub: openWindow ? 'Focus the existing window' : app.description,
        path: app.route,
        icon: app.icon,
        appId: app.id,
        windowId: openWindow?.id,
      }
    })

    const navigationItems: PaletteItem[] = [
      { id: 'nav-workspace', type: 'navigation', label: 'Workspace', sub: 'Open the workspace overview', path: '/workspace', icon: LayoutDashboard },
      { id: 'nav-assistant', type: 'navigation', label: 'Assistant', sub: 'Open the AI assistant', path: '/assistant', icon: Brain },
      { id: 'nav-settings', type: 'navigation', label: 'Settings', sub: 'Open workspace settings', path: '/settings', icon: Settings },
    ]

    const actionItems: PaletteItem[] = []
    if (workspace.activeWindowId) {
      actionItems.push({
        id: 'action-focus',
        type: 'action',
        label: 'Focus active window',
        sub: 'Bring the current window to the front',
        path: '',
        icon: Sparkles,
      })
      actionItems.push({
        id: 'action-close',
        type: 'action',
        label: 'Close active window',
        sub: 'Close the currently active workspace window',
        path: '',
        icon: X,
      })
    }

    const allItems = [...registryItems, ...navigationItems, ...actionItems]

    if (!q.trim()) return allItems.slice(0, 8)

    const query = q.toLowerCase()
    return allItems
      .filter((item) =>
        item.label.toLowerCase().includes(query) ||
        item.sub.toLowerCase().includes(query) ||
        item.type.toLowerCase().includes(query),
      )
      .slice(0, 10)
  }, [q, workspace])

  function handleSelection(item: PaletteItem) {
    if (item.type === 'app') {
      if (item.windowId) {
        workspaceStoreInstance.focusWindow(item.windowId)
      } else {
        workspaceStoreInstance.openWindow(item.appId!, { title: item.label.replace(' (open)', ''), path: item.path })
      }
      onClose()
      return
    }

    if (item.type === 'navigation') {
      navigate(item.path)
      onClose()
      return
    }

    if (item.id === 'action-focus' && workspace.activeWindowId) {
      workspaceStoreInstance.focusWindow(workspace.activeWindowId)
    }

    if (item.id === 'action-close' && workspace.activeWindowId) {
      workspaceStoreInstance.closeWindow(workspace.activeWindowId)
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
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[15vh] pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -16 }}
              transition={{ duration: 0.15 }}
              className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/12 bg-surface-900/98 shadow-2xl pointer-events-auto"
            >
              <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3.5">
                <Search className="h-4 w-4 shrink-0 text-white/30" />
                <input
                  ref={inputRef}
                  value={q}
                  onChange={(event) => setQ(event.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Search apps, navigation, commands…"
                  className="flex-1 bg-transparent text-sm text-white outline-none placeholder-white/25"
                />
                {q && (
                  <button onClick={() => setQ('')} className="text-white/25 transition-colors hover:text-white/60">
                    <X className="h-4 w-4" />
                  </button>
                )}
                <kbd className="rounded bg-white/6 px-2 py-0.5 text-[10px] font-mono text-white/20">ESC</kbd>
              </div>

              <div className="max-h-80 overflow-y-auto py-2">
                {results.length === 0 && (
                  <div className="flex flex-col items-center justify-center gap-1.5 py-10">
                    <Search className="h-6 w-6 text-white/10" />
                    <p className="text-sm text-white/25">No results for "{q}"</p>
                  </div>
                )}

                {results.map((item, index) => {
                  const Icon = item.icon
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelection(item)}
                      className={cn(
                        'flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors',
                        index === cursor ? 'bg-white/8' : 'hover:bg-white/5',
                      )}
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/5">
                        <Icon className="h-3.5 w-3.5 text-white/40" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-white">{item.label}</p>
                        {item.sub && <p className="truncate text-xs text-white/35">{item.sub}</p>}
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 shrink-0 text-white/15" />
                    </button>
                  )
                })}
              </div>

              <div className="flex items-center gap-4 border-t border-white/6 px-4 py-2.5 text-[10px] text-white/20">
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
