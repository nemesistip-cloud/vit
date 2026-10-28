import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, PanelsTopLeft } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { getAppRegistry } from '@/lib/appRegistry'
import { cn } from '@/lib/utils'

export function ApplicationSwitcher() {
  const [open, setOpen] = useState(false)
  const switcherRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const applications = getAppRegistry().filter((app) => app.category === 'Applications')

  useEffect(() => {
    if (!open) return

    function handlePointerDown(event: PointerEvent) {
      if (!switcherRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  if (applications.length === 0) return null

  return (
    <div ref={switcherRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? 'Close application switcher' : 'Open application switcher'}
        aria-expanded={open}
        aria-controls="application-switcher-menu"
        className={cn(
          'inline-flex min-h-10 items-center gap-2 rounded-xl border px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400',
          open
            ? 'border-white/20 bg-white/10 text-white'
            : 'border-white/8 bg-white/5 text-white/70 hover:bg-white/10 hover:text-white',
        )}
      >
        <PanelsTopLeft aria-hidden="true" className="h-4 w-4 text-vit-300" />
        <span>Applications</span>
        <ChevronDown aria-hidden="true" className={cn('h-3.5 w-3.5 text-white/40 transition-transform', open && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            id="application-switcher-menu"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute left-0 top-full z-50 mt-2 w-72 rounded-xl border border-white/10 bg-surface-800 p-2 shadow-2xl shadow-black/40"
          >
            <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-white/35">
              VIT applications
            </p>
            <div className="space-y-1">
              {applications.map((application) => {
                const Icon = application.icon
                return (
                  <Link
                    key={application.id}
                    to={application.route}
                    onClick={() => setOpen(false)}
                    className="flex min-h-12 items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-white/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vit-400"
                  >
                    <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-vit-300" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-white">{application.name}</span>
                      <span className="block truncate text-xs text-white/40">{application.description}</span>
                    </span>
                  </Link>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
