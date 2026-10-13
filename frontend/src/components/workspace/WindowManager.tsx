import React, { useEffect, useMemo, useRef, useState, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Minus, Maximize2, Move, GripHorizontal, RotateCcw, LayoutGrid } from 'lucide-react'
import { workspaceStoreInstance, useWorkspaceStore, WorkspaceWindowState } from '@/lib/workspacePersistence'
import { cn } from '@/lib/utils'
import { getAppById } from '@/lib/appRegistry'
import { workspaceProcessManager } from '@/lib/processManager'
import { useViewport } from '@/hooks/useViewport'

interface WindowManagerProps {
  className?: string
}

export function WindowManager({ className }: WindowManagerProps) {
  const workspace = useWorkspaceStore()
  const { isMobile, isTablet } = useViewport()
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 })

  const windows = useMemo(
    () => Object.values(workspace.windows).filter((win) => win.visible),
    [workspace.windows]
  )

  useEffect(() => {
    if (!containerRef.current) return
    const updateSize = () => {
      if (containerRef.current) {
        setContainerSize({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    updateSize()
    const observer = new ResizeObserver(updateSize)
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  const activeMobileWindow = useMemo(() => {
    if (!windows.length) return null
    if (workspace.activeWindowId) {
      const active = windows.find((w) => w.id === workspace.activeWindowId)
      if (active) return active
    }
    return windows[windows.length - 1]
  }, [windows, workspace.activeWindowId])

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-surface-900/50 p-3 sm:p-4 transition-all duration-200',
        isMobile ? 'min-h-[500px]' : 'min-h-[580px]',
        className
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.08),_transparent_30%)]" />

      {/* Toolbar / Header bar */}
      <div className="relative z-10 mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-white/8 pb-3">
        <div className="flex items-center gap-2">
          <LayoutGrid className="h-4 w-4 text-vit-400" />
          <span className="text-sm font-semibold text-white">Active Windows</span>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">
            {windows.length} open
          </span>
        </div>

        <div className="flex items-center gap-2">
          {windows.length > 0 && (
            <button
              type="button"
              onClick={() => workspaceStoreInstance.resetLayout()}
              className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/60 transition-colors hover:bg-white/10 hover:text-white"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Layout
            </button>
          )}
        </div>
      </div>

      {/* Mobile Application Switcher & Stacked View */}
      {isMobile ? (
        <div className="relative z-10 flex flex-1 flex-col space-y-3">
          {windows.length > 1 && (
            <div className="flex flex-wrap items-center gap-1.5 border-b border-white/5 pb-2">
              {windows.map((win) => {
                const isActive = activeMobileWindow?.id === win.id
                return (
                  <button
                    key={win.id}
                    type="button"
                    onClick={() => workspaceStoreInstance.focusWindow(win.id)}
                    className={cn(
                      'flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-colors',
                      isActive
                        ? 'bg-vit-500/20 text-vit-300 border border-vit-500/30'
                        : 'bg-white/5 text-white/50 hover:bg-white/10 hover:text-white'
                    )}
                  >
                    <span>{win.title}</span>
                    <span
                      onClick={(e) => {
                        e.stopPropagation()
                        workspaceStoreInstance.closeWindow(win.id)
                      }}
                      className="ml-1 rounded p-0.5 hover:bg-white/20"
                    >
                      <X className="h-3 w-3" />
                    </span>
                  </button>
                )
              })}
            </div>
          )}

          {activeMobileWindow ? (
            <MobileWindowCard win={activeMobileWindow} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
              <p className="text-sm text-white/40">No applications open in workspace.</p>
              <p className="text-xs text-white/25 mt-1">Select an app above to launch it.</p>
            </div>
          )}
        </div>
      ) : (
        /* Tablet / Desktop Window Canvas */
        <div className="relative flex-1 min-h-[460px] w-full overflow-hidden">
          {windows.length === 0 ? (
            <div className="flex h-full min-h-[300px] flex-col items-center justify-center text-center">
              <p className="text-sm font-medium text-white/40">No active windows</p>
              <p className="text-xs text-white/25 mt-1">Launch an app to begin your workspace session.</p>
            </div>
          ) : (
            <AnimatePresence>
              {windows.map((win) => (
                <WindowFrame
                  key={win.id}
                  win={win}
                  containerWidth={containerSize.width}
                  containerHeight={containerSize.height}
                  isTablet={isTablet}
                />
              ))}
            </AnimatePresence>
          )}
        </div>
      )}
    </div>
  )
}

function MobileWindowCard({ win }: { win: WorkspaceWindowState }) {
  const app = getAppById(win.appKey)
  const Component = app?.component

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-1 flex-col rounded-2xl border border-white/10 bg-surface-900/95 shadow-xl overflow-hidden"
    >
      <div className="flex items-center justify-between border-b border-white/8 bg-surface-800/80 px-4 py-3">
        <span className="text-sm font-medium text-white">{win.title}</span>
        <button
          type="button"
          aria-label="Close app window"
          className="rounded-lg p-1 text-white/50 hover:bg-white/10 hover:text-white"
          onClick={() => workspaceStoreInstance.closeWindow(win.id)}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 max-h-[60vh]">
        <Suspense fallback={<div className="p-4 text-sm text-white/40">Loading application...</div>}>
          {Component ? <Component /> : <div className="text-sm text-white/40">Unsupported app</div>}
        </Suspense>
      </div>
    </motion.div>
  )
}

function WindowFrame({
  win,
  containerWidth,
  containerHeight,
  isTablet,
}: {
  win: WorkspaceWindowState
  containerWidth: number
  containerHeight: number
  isTablet: boolean
}) {
  const [dragging, setDragging] = useState(false)
  const [resizing, setResizing] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const app = getAppById(win.appKey)
  const Component = app?.component

  const isActive = workspaceStoreInstance.getState().activeWindowId === win.id

  // Bounded width/height calculations
  const minW = app?.minimumWindowSize.width ?? 320
  const minH = app?.minimumWindowSize.height ?? 260
  const boundedWidth = Math.min(Math.max(minW, win.width), Math.max(minW, containerWidth || 800))
  const boundedHeight = Math.min(Math.max(minH, win.height), Math.max(minH, containerHeight || 600))

  // Bounded positions
  const maxX = Math.max(0, (containerWidth || 800) - boundedWidth)
  const maxY = Math.max(0, (containerHeight || 600) - boundedHeight)
  const clampedX = Math.min(Math.max(0, win.x), maxX)
  const clampedY = Math.min(Math.max(0, win.y), maxY)

  const style = win.maximized
    ? { left: 0, top: 0, width: '100%', height: '100%', zIndex: win.zIndex }
    : {
        left: clampedX,
        top: clampedY,
        width: boundedWidth,
        height: boundedHeight,
        zIndex: win.zIndex,
      }

  const handleHeaderMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    // Ignore clicks on buttons or form controls
    const target = e.target as HTMLElement
    if (target.closest('button') || target.closest('input') || target.closest('select')) return

    workspaceStoreInstance.focusWindow(win.id)
    if (win.maximized) return // Disable dragging while maximized

    setDragging(true)
    setDragOffset({
      x: e.clientX - clampedX,
      y: e.clientY - clampedY,
    })
  }

  useEffect(() => {
    if (!win.visible || !dragging) return
    const onMove = (event: MouseEvent) => {
      const nextX = event.clientX - dragOffset.x
      const nextY = event.clientY - dragOffset.y

      const safeMaxX = Math.max(0, containerWidth - boundedWidth)
      const safeMaxY = Math.max(0, containerHeight - boundedHeight)

      workspaceStoreInstance.updateWindow(win.id, {
        x: Math.min(Math.max(0, nextX), safeMaxX),
        y: Math.min(Math.max(0, nextY), safeMaxY),
      })
    }
    const onUp = () => setDragging(false)

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [dragging, dragOffset, win.id, win.visible, containerWidth, containerHeight, boundedWidth, boundedHeight])

  useEffect(() => {
    if (!win.visible || !resizing) return
    const onMove = (event: MouseEvent) => {
      const newWidth = Math.min(
        Math.max(minW, event.clientX - win.x),
        Math.max(minW, containerWidth - win.x)
      )
      const newHeight = Math.min(
        Math.max(minH, event.clientY - win.y),
        Math.max(minH, containerHeight - win.y)
      )

      workspaceStoreInstance.updateWindow(win.id, {
        width: newWidth,
        height: newHeight,
      })
    }
    const onUp = () => setResizing(false)

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [resizing, win.id, win.x, win.y, win.visible, containerWidth, containerHeight, minW, minH])

  if (!win.visible || win.minimized) return null

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn(
        'absolute flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-surface-900/95 shadow-2xl shadow-black/30 backdrop-blur-xl transition-shadow duration-150',
        isActive ? 'ring-1 ring-vit-500/50 shadow-vit-500/10' : 'ring-0'
      )}
      style={style}
      onMouseDown={() => workspaceStoreInstance.focusWindow(win.id)}
    >
      {/* Header Bar */}
      <div
        className="flex cursor-grab items-center justify-between border-b border-white/8 bg-surface-800/80 px-3 py-2 active:cursor-grabbing select-none"
        onMouseDown={handleHeaderMouseDown}
      >
        <div className="flex items-center gap-2">
          <Move className="h-3.5 w-3.5 text-white/40" />
          <span className="text-sm font-medium text-white">{win.title}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Minimize window"
            className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            onClick={(e) => {
              e.stopPropagation()
              const processId = Object.keys(
                workspaceStoreInstance.getState().processes ?? {}
              ).find((candidate) => {
                const process = (workspaceStoreInstance.getState().processes ?? {})[candidate]
                return process.windowId === win.id
              })
              if (processId) {
                workspaceProcessManager.minimizeProcess(processId)
              } else {
                workspaceStoreInstance.minimizeWindow(win.id)
              }
            }}
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            aria-label="Maximize or restore window"
            className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            onClick={(e) => {
              e.stopPropagation()
              workspaceStoreInstance.maximizeWindow(win.id, containerWidth, containerHeight)
            }}
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            aria-label="Close window"
            className="rounded-md p-1 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            onClick={(e) => {
              e.stopPropagation()
              const processId = Object.keys(
                workspaceStoreInstance.getState().processes ?? {}
              ).find((candidate) => {
                const process = (workspaceStoreInstance.getState().processes ?? {})[candidate]
                return process.windowId === win.id
              })
              if (processId) {
                workspaceProcessManager.closeProcess(processId)
              } else {
                workspaceStoreInstance.closeWindow(win.id)
              }
            }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div
        className="flex-1 overflow-auto p-3 sm:p-4"
        onMouseDown={() => workspaceStoreInstance.focusWindow(win.id)}
      >
        <Suspense fallback={<div className="p-4 text-sm text-white/40">Loading application...</div>}>
          {Component ? <Component /> : <div className="text-sm text-white/40">Unsupported app</div>}
        </Suspense>
      </div>

      {/* Resize Handle (hidden if maximized or on tablet) */}
      {!win.maximized && !isTablet && (
        <button
          type="button"
          aria-label="Resize window"
          className="absolute bottom-0 right-0 flex h-5 w-5 items-center justify-center rounded-tl-md bg-white/5 text-white/40 cursor-se-resize hover:bg-white/10 hover:text-white"
          onMouseDown={(e) => {
            e.stopPropagation()
            workspaceStoreInstance.focusWindow(win.id)
            setResizing(true)
          }}
        >
          <GripHorizontal className="h-3.5 w-3.5" />
        </button>
      )}
    </motion.div>
  )
}
