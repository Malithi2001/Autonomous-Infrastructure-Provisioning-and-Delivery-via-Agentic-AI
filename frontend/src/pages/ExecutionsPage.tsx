import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Clock, Loader } from 'lucide-react'
import { executionService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

interface Execution {
  id: string
  requested_by: string
  status: string
  summary: string
  details?: string | null
  started_at: string
  completed_at?: string | null
  source?: string | null
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'success': return <CheckCircle size={14} className="text-primary-400" />
    case 'failed':  return <XCircle size={14} className="text-red-400" />
    case 'running': return <Loader size={14} className="text-blue-400 animate-spin" />
    default:        return <Clock size={14} className="text-gray-500" />
  }
}

const sourceBadge = (source?: string | null) => {
  if (!source) return null
  return (
    <span className="bg-surface-700 text-primary-300 text-xs font-medium px-2 py-0.5 rounded-full">
      {source}
    </span>
  )
}

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    executionService.list().then(setExecutions).finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-surface-600 shrink-0">
        <h1 className="text-base font-semibold text-white">Execution History</h1>
        <p className="text-xs text-gray-500">Full audit trail of all agent actions</p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : executions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Clock size={40} className="text-gray-600 mb-3" />
            <p className="text-white font-medium">No executions yet</p>
            <p className="text-sm text-gray-500 mt-1">Agent actions will be logged here with full traceability.</p>
          </div>
        ) : (
          <div className="space-y-2 max-w-3xl">
            {executions.map((ex) => (
              <div key={ex.id} className="card px-4 py-3 flex items-center gap-4 hover:border-surface-500 transition-colors">
                <div className="shrink-0">{statusIcon(ex.status)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate">{ex.summary}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    <span className="mr-2">By {ex.requested_by}</span>
                    {formatDistanceToNow(new Date(ex.started_at), { addSuffix: true })}
                  </p>
                </div>
                <div className="shrink-0">{sourceBadge(ex.source)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
