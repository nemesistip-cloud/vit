import { useSyncExternalStore } from 'react'

export interface WorkspaceSidebarState {
  collapsed: boolean
  selectedPath: string
}

export interface WorkspaceDockState {
  favorites: string[]
  order: string[]
  pinned: string[]
}

export interface WorkspaceWidgetState {
  id: string
  visible: boolean
  collapsed: boolean
  position: number
  size: 'sm' | 'md' | 'lg' | 'full'
  zIndex: number
  lastActive: number
}

export interface WorkspacePanelState {
  open: string[]
  closed: string[]
  activeTab: string
}

export interface WorkspacePreferences {
  theme: 'dark' | 'light' | 'system'
  density: 'compact' | 'comfortable' | 'spacious'
  layoutMode: 'grid' | 'freeform' | 'split'
  language: string
}

export interface WorkspaceWindowState {
  id: string
  appKey: string
  title: string
  path: string
  x: number
  y: number
  width: number
  height: number
  minimized: boolean
  maximized: boolean
  visible: boolean
  zIndex: number
  lastState?: 'normal' | 'minimized' | 'maximized'
  restoreBounds?: { x: number; y: number; width: number; height: number }
}

export interface WorkspaceState {
  activeWorkspace: string
  lastOpenedModule: string
  currentRoute: string
  sidebar: WorkspaceSidebarState
  dock: WorkspaceDockState
  widgets: Record<string, WorkspaceWidgetState>
  panels: WorkspacePanelState
  preferences: WorkspacePreferences
  windows: Record<string, WorkspaceWindowState>
  windowOrder: string[]
  activeWindowId: string | null
  processes?: Record<string, any>
  activeProcessId?: string | null
}

const STORAGE_KEY = 'vit_workspace_state_v1'

const defaultWidgets = (): Record<string, WorkspaceWidgetState> => ({
  'quick-access': {
    id: 'quick-access',
    visible: true,
    collapsed: false,
    position: 0,
    size: 'md',
    zIndex: 1,
    lastActive: Date.now(),
  },
  'operational-focus': {
    id: 'operational-focus',
    visible: true,
    collapsed: false,
    position: 1,
    size: 'md',
    zIndex: 1,
    lastActive: Date.now(),
  },
})

const defaultState = (): WorkspaceState => ({
  activeWorkspace: 'workspace',
  lastOpenedModule: '/workspace',
  currentRoute: '/workspace',
  sidebar: {
    collapsed: false,
    selectedPath: '/dashboard',
  },
  dock: {
    favorites: ['workspace', 'assistant', 'wallet', 'predictions'],
    order: ['workspace', 'assistant', 'wallet', 'predictions', 'settings'],
    pinned: ['workspace', 'assistant', 'wallet', 'predictions', 'settings'],
  },
  widgets: defaultWidgets(),
  panels: {
    open: ['overview'],
    closed: [],
    activeTab: 'overview',
  },
  preferences: {
    theme: 'dark',
    density: 'comfortable',
    layoutMode: 'grid',
    language: 'en',
  },
  windows: {},
  windowOrder: [],
  activeWindowId: null,
})

function getNextWindowZIndex(windows: Record<string, WorkspaceWindowState>) {
  return Object.values(windows).reduce((max, window) => Math.max(max, window.zIndex), 10) + 1
}

class WorkspacePersistenceService {
  load(): WorkspaceState {
    if (typeof window === 'undefined') return defaultState()

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (!raw) return defaultState()

      const parsed = JSON.parse(raw) as Partial<WorkspaceState>
      return {
        ...defaultState(),
        ...parsed,
        sidebar: { ...defaultState().sidebar, ...parsed.sidebar },
        dock: { ...defaultState().dock, ...parsed.dock },
        widgets: { ...defaultWidgets(), ...parsed.widgets },
        panels: { ...defaultState().panels, ...parsed.panels },
        preferences: { ...defaultState().preferences, ...parsed.preferences },
        windows: parsed.windows ?? {},
        windowOrder: parsed.windowOrder ?? [],
        activeWindowId: parsed.activeWindowId ?? null,
      }
    } catch {
      return defaultState()
    }
  }

  save(state: WorkspaceState) {
    if (typeof window === 'undefined') return
    window.localStorage.getItem // no-op check
    try {
      // Clean sensitive application state prior to persistence
      const sanitized = {
        ...state,
        processes: undefined,
      }
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized))
    } catch {
      // Ignore quota errors
    }
  }
}

class WorkspaceStore {
  private service: WorkspacePersistenceService
  private state: WorkspaceState
  private listeners = new Set<() => void>()
  private initialized = false

  constructor(service: WorkspacePersistenceService) {
    this.service = service
    this.state = defaultState()
  }

  initialize() {
    if (this.initialized) return this
    this.state = this.service.load()
    this.initialized = true
    this.emit()
    return this
  }

  getState() {
    if (!this.initialized) this.initialize()
    return this.state
  }

  subscribe(listener: () => void) {
    this.initialize()
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private emit() {
    for (const listener of this.listeners) listener()
  }

  private commit(next: WorkspaceState) {
    this.state = next
    this.service.save(this.state)
    this.emit()
  }

  resetLayout() {
    const next = defaultState()
    this.commit(next)
  }

  setCurrentRoute(route: string) {
    const state = this.getState()
    const next: WorkspaceState = {
      ...state,
      currentRoute: route,
      activeWorkspace: route.startsWith('/workspace') ? 'workspace' : state.activeWorkspace,
      lastOpenedModule: route,
    }
    this.commit(next)
  }

  setSidebarState(patch: Partial<WorkspaceSidebarState>) {
    const state = this.getState()
    this.commit({
      ...state,
      sidebar: {
        ...state.sidebar,
        ...patch,
      },
    })
  }

  setDockState(patch: Partial<WorkspaceDockState>) {
    const state = this.getState()
    this.commit({
      ...state,
      dock: {
        ...state.dock,
        ...patch,
      },
    })
  }

  setWidgetState(id: string, patch: Partial<WorkspaceWidgetState>) {
    const state = this.getState()
    this.commit({
      ...state,
      widgets: {
        ...state.widgets,
        [id]: {
          ...(state.widgets[id] ?? defaultWidgets()[id]),
          ...patch,
          id,
        },
      },
    })
  }

  setPanelState(patch: Partial<WorkspacePanelState>) {
    const state = this.getState()
    this.commit({
      ...state,
      panels: {
        ...state.panels,
        ...patch,
      },
    })
  }

  setPreferences(patch: Partial<WorkspacePreferences>) {
    const state = this.getState()
    this.commit({
      ...state,
      preferences: {
        ...state.preferences,
        ...patch,
      },
    })
  }

  openWindow(appKey: string, patch: Partial<WorkspaceWindowState> & { allowMultiInstance?: boolean } = {}) {
    const state = this.getState()
    const existing = Object.values(state.windows).find((window) => window.appKey === appKey && window.visible)
    if (existing && !patch.allowMultiInstance) {
      this.focusWindow(existing.id)
      return existing.id
    }

    const id = patch.id ?? `${appKey}-${Date.now()}`
    const windowState: WorkspaceWindowState = {
      id,
      appKey,
      title: patch.title ?? appKey,
      path: patch.path ?? `/${appKey}`,
      x: patch.x ?? 20 + (state.windowOrder.length % 4) * 24,
      y: patch.y ?? 20 + (state.windowOrder.length % 4) * 24,
      width: patch.width ?? 480,
      height: patch.height ?? 380,
      minimized: false,
      maximized: false,
      visible: true,
      zIndex: getNextWindowZIndex(state.windows),
      lastState: 'normal',
      restoreBounds: undefined,
      ...patch,
    }

    const windows = {
      ...state.windows,
      [id]: windowState,
    }

    const next: WorkspaceState = {
      ...state,
      windows,
      windowOrder: [...state.windowOrder, id],
      activeWindowId: id,
    }

    this.commit(next)
    return id
  }

  closeWindow(id: string) {
    const state = this.getState()
    const window = state.windows[id]
    if (!window) return

    const windows: Record<string, WorkspaceWindowState> = {
      ...state.windows,
      [id]: {
        ...window,
        visible: false,
        minimized: false,
        maximized: false,
        lastState: 'normal',
      },
    }

    const windowOrder = state.windowOrder.filter((windowId) => windowId !== id)
    const activeWindowId = state.activeWindowId === id
      ? windowOrder[windowOrder.length - 1] ?? null
      : state.activeWindowId

    this.commit({
      ...state,
      windows,
      windowOrder,
      activeWindowId,
    })
  }

  minimizeWindow(id: string) {
    const state = this.getState()
    const window = state.windows[id]
    if (!window) return

    const windows: Record<string, WorkspaceWindowState> = {
      ...state.windows,
      [id]: {
        ...window,
        minimized: true,
        maximized: false,
        lastState: 'minimized',
      },
    }

    this.commit({
      ...state,
      windows,
    })
  }

  restoreWindow(id: string) {
    const state = this.getState()
    const window = state.windows[id]
    if (!window) return

    const nextWindow: WorkspaceWindowState = {
      ...window,
      minimized: false,
      maximized: false,
      lastState: 'normal',
      x: window.restoreBounds?.x ?? window.x,
      y: window.restoreBounds?.y ?? window.y,
      width: window.restoreBounds?.width ?? window.width,
      height: window.restoreBounds?.height ?? window.height,
      restoreBounds: undefined,
    }

    const windows: Record<string, WorkspaceWindowState> = {
      ...state.windows,
      [id]: nextWindow,
    }

    this.commit({
      ...state,
      windows,
      activeWindowId: id,
    })
  }

  maximizeWindow(id: string, containerWidth = 1000, containerHeight = 650) {
    const state = this.getState()
    const window = state.windows[id]
    if (!window) return

    if (window.maximized) {
      // Toggle back to restored
      this.restoreWindow(id)
      return
    }

    const nextWindow: WorkspaceWindowState = {
      ...window,
      minimized: false,
      maximized: true,
      lastState: 'maximized',
      restoreBounds: { x: window.x, y: window.y, width: window.width, height: window.height },
      x: 0,
      y: 0,
      width: containerWidth,
      height: containerHeight,
    }

    const windows: Record<string, WorkspaceWindowState> = {
      ...state.windows,
      [id]: nextWindow,
    }

    this.commit({
      ...state,
      windows,
      activeWindowId: id,
    })
  }

  focusWindow(id: string) {
    const state = this.getState()
    const window = state.windows[id]
    if (!window || !window.visible) return

    const windows: Record<string, WorkspaceWindowState> = {
      ...state.windows,
      [id]: {
        ...window,
        zIndex: getNextWindowZIndex(state.windows),
      },
    }

    this.commit({
      ...state,
      windows,
      activeWindowId: id,
    })
  }

  updateWindow(id: string, patch: Partial<WorkspaceWindowState>) {
    const state = this.getState()
    const window = state.windows[id]
    if (!window) return

    const windows: Record<string, WorkspaceWindowState> = {
      ...state.windows,
      [id]: {
        ...window,
        ...patch,
      },
    }

    this.commit({
      ...state,
      windows,
    })
  }
}

const workspaceStore = new WorkspaceStore(new WorkspacePersistenceService())
workspaceStore.initialize()

export function useWorkspaceStore() {
  return useSyncExternalStore(
    workspaceStore.subscribe.bind(workspaceStore),
    workspaceStore.getState.bind(workspaceStore),
    workspaceStore.getState.bind(workspaceStore),
  )
}

export const workspaceStoreInstance = workspaceStore
