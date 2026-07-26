import { useEffect, useMemo, useState } from 'react'
import { lazy, Suspense } from 'react'
import { motion } from 'framer-motion'
import { X, Minus, Maximize2, Move, GripHorizontal } from 'lucide-react'
import { workspaceStoreInstance, useWorkspaceStore } from '@/lib/workspacePersistence'
import { cn } from '@/lib/utils'
import { getAppById } from '@/lib/appRegistry'
import { workspaceProcessManager } from '@/lib/processManager'

interface WindowManagerProps {
  className?: string
}

export function WindowManager({ className }: WindowManagerProps) {
  const workspace = useWorkspaceStore()
  const windows = useMemo(() => Object.values(workspace.windows).filter((window) => window.visible), [workspace.windows])

  return (
    <div className={cn('relative min-h-[420px] overflow-hidden rounded-3xl border border-white/10 bg-surface-900/50', className)}>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.08),_transparent_30%)]" />
      {windows.map((window) => (
        <WindowFrame key={window.id} window={window} />
      ))}
    </div>
  )
}

function WindowFrame({ window }: { window: any }) {
  const [dragging, setDragging] = useState(false)
  const [resizing, setResizing] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const app = getAppById(window.appKey)
  const Component = app?.component

  const isActive = workspaceStoreInstance.getState().activeWindowId === window.id
  const style = {
    left: window.x,
    top: window.y,
    width: window.width,
    height: window.height,
    zIndex: window.zIndex,
  }

  useEffect(() => {
    if (!window.visible) return
    const onMove = (event: MouseEvent) => {
      if (!dragging) return
      const nextX = event.clientX - dragOffset.x
      const nextY = event.clientY - dragOffset.y
      workspaceStoreInstance.updateWindow(window.id, { x: nextX, y: nextY })
    }
    const onUp = () => setDragging(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [dragging, dragOffset, window.id])

  useEffect(() => {
    if (!window.visible || !resizing) return
    const onMove = (event: MouseEvent) => {
      workspaceStoreInstance.updateWindow(window.id, {
        width: Math.max(320, event.clientX - window.x),
        height: Math.max(260, event.clientY - window.y),
      })
    }
    const onUp = () => setResizing(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [resizing, window.id, window.x, window.y])

  if (!window.visible) return null
  if (window.minimized) return null

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'absolute flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-surface-900/95 shadow-2xl shadow-black/30 backdrop-blur-xl',
        isActive ? 'ring-1 ring-vit-500/40' : 'ring-0',
      )}
      style={style}
      onMouseDown={() => workspaceStoreInstance.focusWindow(window.id)}
    >
      <div className="flex items-center justify-between border-b border-white/8 bg-surface-800/70 px-3 py-2">
        <div className="flex items-center gap-2">
          <Move className="h-3.5 w-3.5 text-white/40" />
          <span className="text-sm font-medium text-white">{window.title}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/5 hover:text-white"
            onClick={() => {
              const processId = Object.keys(workspaceStoreInstance.getState().processes ?? {}).find((candidate) => {
                const process = (workspaceStoreInstance.getState().processes ?? {})[candidate]
                return process.windowId === window.id
              })
              if (processId) {
                workspaceProcessManager.minimizeProcess(processId)
              }
            }}
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <button
            className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/5 hover:text-white"
            onClick={() => workspaceStoreInstance.maximizeWindow(window.id)}
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button
            className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/5 hover:text-white"
            onClick={() => {
              const processId = Object.keys(workspaceStoreInstance.getState().processes ?? {}).find((candidate) => {
                const process = (workspaceStoreInstance.getState().processes ?? {})[candidate]
                return process.windowId === window.id
              })
              if (processId) {
                workspaceProcessManager.closeProcess(processId)
              }
            }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      <div
        className="flex-1 overflow-auto p-3"
        onMouseDown={() => workspaceStoreInstance.focusWindow(window.id)}
      >
        <Suspense fallback={<div className="text-sm text-white/40">Loading application…</div>}>
          {Component ? <Component /> : <div className="text-sm text-white/40">Unsupported app</div>}
        </Suspense>
      </div>
      <button
        className="absolute bottom-0 right-0 flex h-5 w-5 items-center justify-center rounded-tl-md bg-white/5 text-white/40"
        onMouseDown={() => setResizing(true)}
      >
        <GripHorizontal className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  )
}
