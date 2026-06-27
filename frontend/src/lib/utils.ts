import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { format, isValid, parseISO, formatDistanceToNow } from "date-fns"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function safeFormat(date: any, formatStr: string, fallback = "--"): string {
  if (!date) return fallback;
  try {
    const d = typeof date === 'string' ? parseISO(date) : new Date(date);
    if (!isValid(d)) return fallback;
    return format(d, formatStr);
  } catch (e) {
    return fallback;
  }
}

export function formatTime(date: any, fallback = "--"): string {
  return safeFormat(date, "HH:mm", fallback);
}

export function safeFormatDistanceToNow(date: any, options?: any, fallback = "some time ago"): string {
  if (!date) return fallback;
  try {
    const d = typeof date === 'string' ? parseISO(date) : new Date(date);
    if (!isValid(d)) return fallback;
    return formatDistanceToNow(d, options);
  } catch (e) {
    return fallback;
  }
}
