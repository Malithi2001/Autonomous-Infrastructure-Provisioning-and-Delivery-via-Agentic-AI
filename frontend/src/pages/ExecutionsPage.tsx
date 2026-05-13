import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Clock, Loader, Activity } from 'lucide-react'
import { executionService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

interface Execution {
  id: string
  requested_by: string
  status: string
  summary: string
  details?: string
  source?: string
  started_at?: string
  completed_at?: string
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'success':
    case 'completed': return <CheckCircle size={14} className="text-primary-600 dark:text-primary-300" />
    case 'failed': return <XCircle size={14} className="text-red-500 dark:text-red-300" />
    case 'running': return <Loader size={14} className="animate-spin text-blue-500 dark:text-blue-300" />
    default: return <Clock size={14} className="text-ink-subtle" />
  }
}

const statusBadge = (status: string) => {
  const classes: Record<string, string> = { completed: 'badge-success', success: 'badge-success', running: 'badge-info', failed: 'badge-error', cancelled: 'badge-warning' }
  const cls = classes[status] || 'badge-info'
  return <span className={cls}>{status}</span>
}

const relativeTime = (value?: string) => {
  if (!value) return 'time unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'time unknown'
  return formatDistanceToNow(date, { addSuffix: true })
}

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { executionService.list().then(setExecutions).finally(() => setLoading(false)) }, [])

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-blue-500/30 bg-blue-500/10"><Activity size={19} className="text-blue-600 dark:text-blue-300" /></div><div><h1 className="text-base font-semibold text-ink">Execution History</h1><p className="text-xs text-ink-subtle">Full audit trail of all agent actions</p></div></div>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? <div className="flex h-32 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" /></div>
          : executions.length === 0 ? <div className="flex h-full flex-col items-center justify-center text-center"><div className="mb-4 rounded-3xl border border-surface-600 bg-surface-800 p-4"><Clock size={40} className="text-ink-subtle" /></div><p className="font-medium text-ink">No executions yet</p><p className="mt-1 text-sm text-ink-subtle">Agent actions will be logged here with full traceability.</p></div>
            : <div className="mx-auto max-w-4xl space-y-2">{executions.map((ex) => <div key={ex.id} className="card flex items-center gap-4 px-4 py-3 transition-colors hover:border-primary-500/30"><div className="shrink-0">{statusIcon(ex.status)}</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-ink">{ex.summary}</p><p className="mt-0.5 text-xs text-ink-subtle">{ex.source && <span className="mr-2 font-mono text-primary-700 dark:text-primary-300">{ex.source}</span>}{relativeTime(ex.started_at)}</p></div><div className="shrink-0">{statusBadge(ex.status)}</div></div>)}</div>}
      </div>
    </div>
  )
}
