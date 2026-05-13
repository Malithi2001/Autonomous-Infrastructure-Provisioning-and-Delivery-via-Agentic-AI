import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Clock, AlertTriangle, ShieldCheck } from 'lucide-react'
import { approvalService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'

interface Approval {
  id: string
  description?: string
  action?: string
  summary?: string
  status: string
  expires_at?: string
  created_at: string
}

function relativeTime(value?: string) {
  if (!value) return 'time unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'time unknown'
  return formatDistanceToNow(date, { addSuffix: true })
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [loading, setLoading] = useState(true)

  const fetchApprovals = async () => {
    try {
      const data = await approvalService.list()
      setApprovals(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchApprovals() }, [])

  const decide = async (id: string, approved: boolean) => {
    await approvalService.decide(id, approved)
    fetchApprovals()
  }

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-amber-500/30 bg-amber-500/10"><ShieldCheck size={19} className="text-amber-600 dark:text-amber-300" /></div>
          <div><h1 className="text-base font-semibold text-ink">HITL Approvals</h1><p className="text-xs text-ink-subtle">Human-in-the-loop approval gate for high-risk operations</p></div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? <div className="flex h-32 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" /></div>
          : approvals.length === 0 ? <div className="flex h-full flex-col items-center justify-center text-center"><div className="mb-4 rounded-3xl border border-primary-500/25 bg-primary-500/10 p-4"><CheckCircle size={40} className="text-primary-600 dark:text-primary-300" /></div><p className="font-medium text-ink">No pending approvals</p><p className="mt-1 text-sm text-ink-subtle">High-risk agent actions will appear here for your review.</p></div>
            : <div className="mx-auto max-w-3xl space-y-4">{approvals.map((a) => { const description = a.description || a.action || a.summary || 'Approval requested by the agent.'; return <div key={a.id} className="card p-5 transition hover:border-primary-500/30"><div className="mb-4 flex items-start gap-3"><AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-500" /><div className="flex-1"><p className="mb-1 text-sm font-medium text-ink">{description}</p><div className="flex flex-wrap items-center gap-3 text-xs text-ink-subtle"><span className="flex items-center gap-1"><Clock size={11} />{relativeTime(a.created_at)}</span>{a.expires_at && <span className="text-amber-700 dark:text-amber-300">Expires {relativeTime(a.expires_at)}</span>}</div></div></div>{a.status === 'pending' && <div className="flex flex-wrap gap-3"><button onClick={() => decide(a.id, true)} className="flex items-center gap-1.5 rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-500"><CheckCircle size={14} /> Approve</button><button onClick={() => decide(a.id, false)} className="flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-500/15 dark:text-red-300"><XCircle size={14} /> Reject</button></div>}</div>})}</div>}
      </div>
    </div>
  )
}
