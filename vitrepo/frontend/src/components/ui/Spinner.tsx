import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'w-5 h-5 rounded-full border-2 border-white/20 border-t-vit-400 animate-spin',
        className,
      )}
    />
  )
}
