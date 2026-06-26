import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';

/** One row: avatar circle + two text lines + trailing badge */
export function RowSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3" aria-hidden="true">
      <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3 w-3/5" />
        <Skeleton className="h-2.5 w-2/5" />
      </div>
      <Skeleton className="h-5 w-14 rounded-md" />
    </div>
  );
}

/** Stacked card: label line + big value + small sub-label */
export function CardSkeleton() {
  return (
    <div className="p-4 space-y-2 bg-card border border-border rounded-xl" aria-hidden="true">
      <Skeleton className="h-2.5 w-2/5" />
      <Skeleton className="h-6 w-3/5" />
      <Skeleton className="h-2.5 w-1/4" />
    </div>
  );
}

/** Metric card skeleton matching MetricCard layout */
export function MetricSkeleton() {
  return (
    <div className="flex gap-3 p-4 bg-card border border-border rounded-xl" aria-hidden="true">
      <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-2.5 w-1/3" />
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-2.5 w-1/4" />
      </div>
    </div>
  );
}

/** Table row skeleton */
export function TableRowSkeleton({ cols = 4 }: { cols?: number }) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3 border-b border-border"
      aria-hidden="true"
    >
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-3 rounded ${i === 0 ? 'w-1/3' : i === cols - 1 ? 'w-16' : 'flex-1'}`}
        />
      ))}
    </div>
  );
}

/** Full-section skeleton: N rows */
export function ListSkeleton({ rows = 4, variant = 'row' }: { rows?: number; variant?: 'row' | 'card' | 'metric' }) {
  const El = variant === 'card' ? CardSkeleton : variant === 'metric' ? MetricSkeleton : RowSkeleton;
  return (
    <div className={variant === 'card' || variant === 'metric' ? 'grid grid-cols-2 gap-3' : 'space-y-0 divide-y divide-border bg-card border border-border rounded-xl overflow-hidden'}>
      {Array.from({ length: rows }).map((_, i) => <El key={i} />)}
    </div>
  );
}
