import { motion } from 'framer-motion'
import { Coins, Shield } from 'lucide-react'
import { getStoredUser } from '@/hooks/useAuth'
import { workspaceStoreInstance } from '@/lib/workspacePersistence'
import { WindowManager } from '@/components/workspace/WindowManager'
import { getAppRegistry } from '@/lib/appRegistry'

export default function Workspace() {
  const user = getStoredUser()

  const shortcuts = getAppRegistry().filter((app) => ['dashboard', 'ai', 'wallet', 'predictions'].includes(app.id))

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-white/10 bg-surface-900/70 p-6 shadow-2xl shadow-black/20"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-vit-400/80">Workspace OS</p>
            <h1 className="mt-2 text-2xl font-semibold text-white">Welcome back, {user?.username || 'operator'}.</h1>
            <p className="mt-3 max-w-2xl text-sm text-white/55">
              This workspace is your operational hub for predictions, analytics, wallet activity, and AI assistance.
            </p>
          </div>
          <div className="rounded-2xl border border-vit-500/20 bg-vit-500/10 px-4 py-3 text-sm text-vit-300">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Protected workspace • secure session
            </div>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Workspace apps</h2>
            <span className="text-sm text-white/40">Multiple windows • persistent</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {shortcuts.map((app) => {
              const Icon = app.icon
              return (
                <button
                  key={app.id}
                  onClick={() => workspaceStoreInstance.openWindow(app.id, { title: app.name, path: app.route })}
                  className="rounded-2xl border border-white/8 bg-surface-800/60 p-4 text-left transition-colors hover:border-vit-500/20 hover:bg-surface-800/80"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-vit-500/10 text-vit-300">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-medium text-white">{app.name}</p>
                      <p className="text-sm text-white/40">{app.description}</p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-surface-900/70 p-5">
          <div className="flex items-center gap-2 text-vit-300">
            <Coins className="h-4 w-4" />
            <h2 className="text-lg font-semibold text-white">Operational focus</h2>
          </div>
          <div className="mt-4 space-y-3 text-sm text-white/55">
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

      <WindowManager className="min-h-[520px]" />
    </div>
  )
}
