import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string | number;
  changePositive?: boolean;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'hero' | 'compact';
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
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-xl flex gap-3 transition-colors hover:border-primary/20 group',
        variant === 'hero'    ? 'p-6' :
        variant === 'compact' ? 'p-3' : 'p-4',
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
            'font-mono font-bold text-foreground leading-tight',
            variant === 'hero' ? 'text-4xl' : 'text-lg'
          )}
        >
          {value}
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
          <span className="text-xs text-muted-foreground leading-none mt-0.5">
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
