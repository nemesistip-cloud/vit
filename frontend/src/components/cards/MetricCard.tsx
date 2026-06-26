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
  const pad = variant === 'hero' ? 'p-6' : variant === 'compact' ? 'p-3' : 'p-4';

  if (loading) {
    return (
      <div
        className={cn('bg-card border border-border rounded-xl flex gap-3', pad, className)}
        aria-hidden="true"
      >
        {icon && <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />}
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-2.5 w-1/3" />
          <Skeleton className={cn('w-2/3', variant === 'hero' ? 'h-8' : 'h-5')} />
          <Skeleton className="h-2.5 w-1/4" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-card border border-border rounded-xl flex gap-3 transition-colors hover:border-primary/20 group',
        pad,
        className
      )}
      role="region"
      aria-label={label}
    >
      {icon && (
        <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors group-hover:bg-primary/15">
          {icon}
        </div>
      )}

      <div className="flex flex-col gap-0.5 flex-1 min-w-0">
        <span className="text-[10px] text-muted-foreground uppercase tracking-[0.1em] font-semibold font-mono leading-none">
          {label}
        </span>

        <span
          className={cn(
            'font-mono font-bold text-foreground leading-tight tabular-nums',
            variant === 'hero' ? 'text-4xl' : 'text-lg'
          )}
        >
          {value ?? '—'}
        </span>

        {change !== undefined && (
          <span
            className={cn(
              'flex items-center gap-0.5 text-xs font-mono font-semibold',
              changePositive ? 'text-emerald-400' : 'text-rose-400'
            )}
            aria-label={`${changePositive ? 'Up' : 'Down'} ${change}`}
          >
            {changePositive
              ? <ArrowUpRight size={11} />
              : <ArrowDownRight size={11} />}
            {change}
          </span>
        )}

        {subtitle && (
          <span className="text-xs text-muted-foreground leading-none mt-0.5 truncate">
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
