import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function formatUptime(seconds: number): string {
  const days  = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins  = Math.floor((seconds % 3600) / 60)
  if (days > 0)  return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

export function timeAgo(date: string | Date): string {
  const diff = Date.now() - new Date(date).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60)   return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export function statusColor(status: string | undefined): 'green' | 'yellow' | 'red' | 'gray' {
  if (!status) return 'gray'
  const s = status.toLowerCase()
  if (s === 'healthy' || s === 'ok' || s === 'operational' || s === 'online') return 'green'
  if (s === 'degraded' || s === 'warning' || s === 'partial') return 'yellow'
  if (s === 'unhealthy' || s === 'error' || s === 'offline' || s === 'down') return 'red'
  return 'gray'
}
