import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import { Card } from './ui/Card'
import { StatusBadge } from './ui/StatusBadge'
import { Spinner } from './ui/Spinner'

interface Props {
  name: string
  description: string
  icon: LucideIcon
  status?: string
  version?: string
  latency?: number
  isLoading?: boolean
  href?: string
  index?: number
}

export function ServiceCard({ name, description, icon: Icon, status, version, latency, isLoading, href, index = 0 }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
    >
      <Card hover className="h-full p-5 flex flex-col gap-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-vit-500/10 border border-vit-500/20 flex items-center justify-center">
              <Icon className="w-5 h-5 text-vit-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white">{name}</h3>
              {version && <p className="text-xs text-white/40 font-mono">v{version}</p>}
            </div>
          </div>
          {isLoading ? (
            <Spinner className="w-4 h-4" />
          ) : (
            <StatusBadge status={status} pulse size="sm" />
          )}
        </div>

        <p className="text-sm text-white/60 leading-relaxed flex-1">{description}</p>

        {latency !== undefined && (
          <div className="flex items-center gap-2 pt-1 border-t border-white/5">
            <span className="text-xs text-white/40">Latency</span>
            <span className="text-xs font-mono text-vit-400">{latency}ms</span>
          </div>
        )}

        {href && (
          <a
            href={href}
            className="text-xs text-vit-400 hover:text-vit-300 transition-colors mt-auto"
          >
            View details →
          </a>
        )}
      </Card>
    </motion.div>
  )
}
