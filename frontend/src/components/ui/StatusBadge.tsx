import { cn, statusColor } from '@/lib/utils'

interface Props {
  status?: string
  pulse?: boolean
  size?: 'sm' | 'md'
}

const colorMap = {
  green: 'bg-emerald-400/15 text-emerald-400 border-emerald-400/30',
  yellow: 'bg-yellow-400/15 text-yellow-400 border-yellow-400/30',
  red: 'bg-red-400/15 text-red-400 border-red-400/30',
  gray: 'bg-white/10 text-white/50 border-white/10',
}

const dotMap = {
  green: 'bg-emerald-400 shadow-[0_0_6px_theme(colors.emerald.400)]',
  yellow: 'bg-yellow-400 shadow-[0_0_6px_theme(colors.yellow.400)]',
  red: 'bg-red-400 shadow-[0_0_6px_theme(colors.red.400)]',
  gray: 'bg-white/30',
}

export function StatusBadge({ status, pulse = false, size = 'md' }: Props) {
  const color = statusColor(status)
  const label = status ?? 'unknown'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium uppercase tracking-wide',
        colorMap[color],
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs',
      )}
    >
      <span className={cn('rounded-full', size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2', dotMap[color], pulse && color === 'green' && 'animate-pulse')} />
      {label}
    </span>
  )
}
