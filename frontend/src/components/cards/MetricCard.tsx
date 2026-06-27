import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value?: string | number;
  change?: string | number;
  changePositive?: boolean;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'hero' | 'compact';
  loading?: boolean;
  className?: string;
}

export default function MetricCard({
  label,
  value,
  change,
  changePositive,
  subtitle,
  icon,
  variant = 'default',
  loading = false,
  className,
}: MetricCardProps) {
  const pad = variant === 'hero' ? 'p-8' : variant === 'compact' ? 'p-4' : 'p-6';

  if (loading) {
    return (
      <div
        className={cn('bg-white/[0.01] border border-white/5 rounded flex gap-4', pad, className)}
        aria-hidden="true"
      >
        <div className="flex-1 space-y-3">
          <Skeleton className="h-2 w-1/3 bg-white/5" />
          <Skeleton className={cn('w-2/3 bg-white/5', variant === 'hero' ? 'h-10' : 'h-6')} />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-white/[0.01] border border-white/5 rounded-sm flex flex-col gap-3 transition-all hover:bg-white/[0.02] hover:border-white/10 group shadow-sm',
        pad,
        className
      )}
      role="region"
      aria-label={label}
    >
      <div className="flex items-center justify-between">
        <span className="text-[9px] text-muted-foreground uppercase tracking-[0.2em] font-bold font-mono leading-none">
          {label}
        </span>
        {icon && (
          <div className="text-muted-foreground group-hover:text-primary transition-colors opacity-50 group-hover:opacity-100">
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2 mt-auto">
        <span
          className={cn(
            'font-display font-bold text-foreground leading-none tracking-tight tabular-nums',
            variant === 'hero' ? 'text-4xl' : 'text-2xl'
          )}
        >
          {value ?? '—'}
        </span>

        {change !== undefined && (
          <span
            className={cn(
              'flex items-center gap-0.5 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full',
              changePositive ? 'text-emerald-400 bg-emerald-400/10' : 'text-amber-500 bg-amber-500/10'
            )}
            aria-label={`${changePositive ? 'Up' : 'Down'} ${change}`}
          >
            {changePositive
              ? <ArrowUpRight size={10} strokeWidth={3} />
              : <ArrowDownRight size={10} strokeWidth={3} />}
            {change}
          </span>
        )}
      </div>

      {subtitle && (
        <span className="text-[10px] font-mono text-muted-foreground/50 uppercase tracking-widest leading-none mt-1 truncate">
          {subtitle}
        </span>
      )}
    </div>
  );
}
