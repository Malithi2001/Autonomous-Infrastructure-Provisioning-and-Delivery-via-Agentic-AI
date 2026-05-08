import { Radio, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import type { ConnectionStatus } from '@/types'

interface ConnectionStatusPillProps {
  status: ConnectionStatus
  lastError?: string | null
  onReconnect: () => void
}

const labels: Record<ConnectionStatus, string> = {
  connecting: 'Connecting',
  connected: 'Streaming ready',
  disconnected: 'HTTP fallback',
  error: 'HTTP fallback',
}

export function ConnectionStatusPill({ status, lastError, onReconnect }: ConnectionStatusPillProps) {
  const isConnected = status === 'connected'
  return (
    <div className={clsx('flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium', isConnected ? 'border-primary-500/30 bg-primary-500/10 text-primary-700 dark:text-primary-200' : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-200')} title={lastError || undefined}>
      <Radio size={13} className={clsx(isConnected && 'animate-pulse')} />
      <span>{labels[status]}</span>
      {!isConnected && <button onClick={onReconnect} className="ml-1 rounded-full p-0.5 transition hover:bg-black/5 dark:hover:bg-white/10" aria-label="Reconnect WebSocket"><RefreshCw size={12} /></button>}
    </div>
  )
}
