import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { approvalService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import { canDecideApprovals } from '@/lib/rbac'

interface Approval {
  id: string
  requested_by: string
  action: string
  risk_level: string
  summary: string
  status: string
  created_at: string
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [loading, setLoading] = useState(true)
  const userRole = useAuthStore((s) => s.user?.role)
  const allowDecision = canDecideApprovals(userRole)

  const fetchApprovals = async () => {
    try {
      const data = await approvalService.list()
      setApprovals(data)
    } catch {
      // Handle error
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
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-surface-600 shrink-0">
        <h1 className="text-base font-semibold text-white">HITL Approvals</h1>
        <p className="text-xs text-gray-500">Human-in-the-Loop approval gate for high-risk operations</p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : approvals.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <CheckCircle size={40} className="text-primary-400 mb-3" />
            <p className="text-white font-medium">No pending approvals</p>
            <p className="text-sm text-gray-500 mt-1">High-risk agent actions will appear here for your review.</p>
          </div>
        ) : (
          <div className="space-y-4 max-w-2xl">
            {approvals.map((a) => (
              <div key={a.id} className="card p-5">
                <div className="flex items-start gap-3 mb-4">
                  <AlertTriangle size={18} className="text-yellow-400 mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm text-white font-medium mb-1">{a.summary}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock size={11} />
                        {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                      </span>
                      <span>{a.action}</span>
                      <span className="uppercase">{a.risk_level}</span>
                      <span>By {a.requested_by}</span>
                    </div>
                  </div>
                </div>
                {a.status === 'pending' && allowDecision && (
                  <div className="flex gap-3">
                    <button
                      onClick={() => decide(a.id, true)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-sm rounded-lg transition-colors"
                    >
                      <CheckCircle size={14} /> Approve
                    </button>
                    <button
                      onClick={() => decide(a.id, false)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-600/30 text-sm rounded-lg transition-colors"
                    >
                      <XCircle size={14} /> Reject
                    </button>
                  </div>
                )}
                {a.status === 'pending' && !allowDecision && (
                  <p className="text-xs text-gray-500">Read-only access for your role.</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
