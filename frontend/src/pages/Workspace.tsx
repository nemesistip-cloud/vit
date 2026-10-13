import { motion } from 'framer-motion'
import { Coins, Shield, RotateCcw } from 'lucide-react'
import { getStoredUser } from '@/hooks/useAuth'
import { WindowManager } from '@/components/workspace/WindowManager'
import { getAppRegistry } from '@/lib/appRegistry'
import { workspaceProcessManager } from '@/lib/processManager'
import { workspaceStoreInstance } from '@/lib/workspacePersistence'

export default function Workspace() {
  const user = getStoredUser()

  const shortcuts = getAppRegistry().filter((app) => ['dashboard', 'ai', 'wallet', 'predictions'].includes(app.id))

  return (
    <div className="space-y-6 max-w-full overflow-x-hidden">
      {/* Header Banner */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-white/10 bg-surface-900/70 p-5 sm:p-6 shadow-2xl shadow-black/20"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs sm:text-sm font-medium uppercase tracking-[0.24em] text-vit-400/80">Workspace OS</p>
            <h1 className="mt-1 sm:mt-2 text-xl sm:text-2xl font-semibold text-white">
              Welcome back, {user?.username || 'operator'}.
            </h1>
            <p className="mt-2 text-xs sm:text-sm max-w-2xl text-white/55">
              This workspace is your operational hub for predictions, analytics, wallet activity, and AI assistance.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-2 rounded-2xl border border-vit-500/20 bg-vit-500/10 px-3.5 py-2 text-xs sm:text-sm text-vit-300">
              <Shield className="h-4 w-4 shrink-0" />
              <span>Protected workspace</span>
            </div>
            <button
              type="button"
              onClick={() => workspaceStoreInstance.resetLayout()}
              className="inline-flex items-center gap-1.5 rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/60 hover:bg-white/10 hover:text-white transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Layout
            </button>
          </div>
        </div>
      </motion.div>

      {/* Grid of Shortcuts & Operational Focus */}
      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-4 sm:p-5">
          <div className="mb-3 sm:mb-4 flex items-center justify-between">
            <h2 className="text-base sm:text-lg font-semibold text-white">Workspace apps</h2>
            <span className="text-xs text-white/40">Launch in Window Manager</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {shortcuts.map((app) => {
              const Icon = app.icon
              return (
                <button
                  key={app.id}
                  type="button"
                  onClick={() => workspaceProcessManager.launchProcess(app.id)}
                  className="rounded-2xl border border-white/8 bg-surface-800/60 p-3.5 text-left transition-colors hover:border-vit-500/20 hover:bg-surface-800/80 cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-vit-500/10 text-vit-300">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-sm sm:text-base text-white truncate">{app.name}</p>
                      <p className="text-xs text-white/40 truncate">{app.description}</p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-4 sm:p-5">
          <div className="flex items-center gap-2 text-vit-300">
            <Coins className="h-4 w-4 shrink-0" />
            <h2 className="text-base sm:text-lg font-semibold text-white">Operational focus</h2>
          </div>
          <div className="mt-3 sm:mt-4 space-y-2.5 text-xs sm:text-sm text-white/55">
            <div className="rounded-2xl border border-white/8 bg-surface-800/60 p-3">
              Review system status and recent activity in one place.
            </div>
            <div className="rounded-2xl border border-white/8 bg-surface-800/60 p-3">
              Open the AI assistant for detailed guidance and next actions.
            </div>
            <div className="rounded-2xl border border-white/8 bg-surface-800/60 p-3">
              Keep wallet flow and prediction work aligned from a single shell.
            </div>
          </div>
        </div>
      </div>

      {/* Main Window Manager */}
      <WindowManager className="w-full" />
    </div>
  )
}
