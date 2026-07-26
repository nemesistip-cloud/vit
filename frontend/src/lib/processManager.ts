import { getAppById } from '@/lib/appRegistry'
import { workspaceStoreInstance } from '@/lib/workspacePersistence'

export type ProcessStatus = 'starting' | 'running' | 'suspended' | 'minimized' | 'closed'

export interface WorkspaceProcess {
  processId: string
  appId: string
  windowId: string | null
  status: ProcessStatus
  createdAt: number
  lastFocused: number
  memoryState: Record<string, unknown>
  metadata: Record<string, unknown>
}

class WorkspaceProcessManager {
  launchProcess(appId: string, metadata: Record<string, unknown> = {}) {
    const app = getAppById(appId)
    if (!app) return null

    const existingWindow = Object.values(workspaceStoreInstance.getState().windows).find((window) => window.appKey === appId && window.visible)
    if (existingWindow) {
      workspaceStoreInstance.focusWindow(existingWindow.id)
      return existingWindow.id
    }

    const windowId = workspaceStoreInstance.openWindow(appId, {
      title: app.name,
      path: app.route,
      width: app.defaultWindowSize.width,
      height: app.defaultWindowSize.height,
    })

    const process: WorkspaceProcess = {
      processId: `${appId}-${windowId}`,
      appId,
      windowId,
      status: 'running',
      createdAt: Date.now(),
      lastFocused: Date.now(),
      memoryState: {},
      metadata,
    }

    const state = workspaceStoreInstance.getState()
    const processes = {
      ...(state as any).processes,
      [process.processId]: process,
    }

    workspaceStoreInstance.updateWindow(windowId, { title: app.name })
    workspaceStoreInstance.setPreferences({})
    const next = {
      ...state,
      processes,
      activeProcessId: process.processId,
    }

    ;(workspaceStoreInstance as any).commit(next)
    return windowId
  }

  focusProcess(processId: string) {
    const state = workspaceStoreInstance.getState() as any
    const process = state.processes?.[processId]
    if (!process?.windowId) return
    workspaceStoreInstance.focusWindow(process.windowId)
    const next = {
      ...state,
      processes: {
        ...state.processes,
        [processId]: {
          ...process,
          status: 'running',
          lastFocused: Date.now(),
        },
      },
      activeProcessId: processId,
    }
    ;(workspaceStoreInstance as any).commit(next)
  }

  suspendProcess(processId: string) {
    const state = workspaceStoreInstance.getState() as any
    const process = state.processes?.[processId]
    if (!process) return
    const next = {
      ...state,
      processes: {
        ...state.processes,
        [processId]: {
          ...process,
          status: 'suspended',
        },
      },
    }
    ;(workspaceStoreInstance as any).commit(next)
  }

  resumeProcess(processId: string) {
    const state = workspaceStoreInstance.getState() as any
    const process = state.processes?.[processId]
    if (!process) return
    const next = {
      ...state,
      processes: {
        ...state.processes,
        [processId]: {
          ...process,
          status: 'running',
        },
      },
    }
    ;(workspaceStoreInstance as any).commit(next)
  }

  minimizeProcess(processId: string) {
    const state = workspaceStoreInstance.getState() as any
    const process = state.processes?.[processId]
    if (!process?.windowId) return
    workspaceStoreInstance.minimizeWindow(process.windowId)
    const next = {
      ...state,
      processes: {
        ...state.processes,
        [processId]: {
          ...process,
          status: 'minimized',
        },
      },
    }
    ;(workspaceStoreInstance as any).commit(next)
  }

  closeProcess(processId: string) {
    const state = workspaceStoreInstance.getState() as any
    const process = state.processes?.[processId]
    if (!process?.windowId) return
    workspaceStoreInstance.closeWindow(process.windowId)
    const next = {
      ...state,
      processes: {
        ...state.processes,
        [processId]: {
          ...process,
          status: 'closed',
        },
      },
      activeProcessId: state.activeProcessId === processId ? null : state.activeProcessId,
    }
    ;(workspaceStoreInstance as any).commit(next)
  }

  restartProcess(processId: string) {
    const state = workspaceStoreInstance.getState() as any
    const process = state.processes?.[processId]
    if (!process) return
    this.closeProcess(processId)
    const app = getAppById(process.appId)
    if (!app) return
    this.launchProcess(process.appId, process.metadata)
  }
}

export const workspaceProcessManager = new WorkspaceProcessManager()
