import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  label: string
  value: string | number
  sub?: string
  icon?: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
  index?: number
  className?: string
}

export function StatCard({ label, value, sub, icon: Icon, index = 0, className }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.06, duration: 0.35 }}
      className={cn(
        'rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5',
        className,
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-sm text-white/50">{label}</p>
        {Icon && (
          <div className="w-8 h-8 rounded-lg bg-vit-500/10 flex items-center justify-center">
            <Icon className="w-4 h-4 text-vit-400" />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-white/40 mt-1">{sub}</p>}
    </motion.div>
  )
}
