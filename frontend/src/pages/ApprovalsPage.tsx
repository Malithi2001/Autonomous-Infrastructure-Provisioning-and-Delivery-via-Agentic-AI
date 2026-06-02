import { getDebugHint, getUserFriendlyError } from "@/lib/errorMessages";
import { approvalService } from "@/services/api";
import { formatDistanceToNow } from "date-fns";
import {
    AlertCircle,
    AlertTriangle,
    CheckCircle,
    Clock,
    Loader2,
    ShieldCheck,
    XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

interface Approval {
  id: string;
  description?: string;
  action?: string;
  summary?: string;
  requested_by?: string;
  risk_level?: string;
  tool_name?: string;
  tool_input?: string;
  payload?: string;
  status: string;
  expires_at?: string;
  created_at: string;
}

interface ApprovalDetails {
  repository?: string;
  workflow_run_id?: number;
  predicted_failure?: string;
  suggested_fix?: string;
  proposed_file_changes?: string[];
  risk_level?: string;
  workflow_path?: string;
  workflow_url?: string;
}

function relativeTime(value?: string) {
  if (!value) return "time unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "time unknown";
  return formatDistanceToNow(date, { addSuffix: true });
}

function parseApprovalDetails(approval: Approval): ApprovalDetails | null {
  const raw = approval.tool_input || approval.payload;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed.approval_details || parsed;
  } catch {
    return null;
  }
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value?: string | number | null;
}) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-ink">{value}</dd>
    </div>
  );
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [decidingId, setDecidingId] = useState<string | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await approvalService.list();
      setApprovals(data);
    } catch (err: any) {
      setError(getUserFriendlyError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const decide = async (id: string, approved: boolean) => {
    if (decidingId) return;
    setDecidingId(id);
    setError("");
    try {
      await approvalService.decide(id, approved);
      await fetchApprovals();
    } catch (err: any) {
      setError(getUserFriendlyError(err));
    } finally {
      setDecidingId(null);
    }
  };

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-amber-500/30 bg-amber-500/10">
            <ShieldCheck
              size={19}
              className="text-amber-600 dark:text-amber-300"
            />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">HITL Approvals</h1>
            <p className="text-xs text-ink-subtle">
              Human-in-the-loop approval gate for high-risk operations
            </p>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          </div>
        ) : error ? (
          <div className="mx-auto max-w-3xl">
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-red-700 dark:text-red-200">
              <div className="flex items-start gap-3">
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">{error}</p>
                  {getDebugHint(error) && (
                    <p className="mt-2 text-xs opacity-80">
                      Tip: {getDebugHint(error)}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : approvals.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 rounded-3xl border border-primary-500/25 bg-primary-500/10 p-4">
              <CheckCircle
                size={40}
                className="text-primary-600 dark:text-primary-300"
              />
            </div>
            <p className="font-medium text-ink">No pending approvals</p>
            <p className="mt-1 text-sm text-ink-subtle">
              High-risk agent actions will appear here for your review.
            </p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {approvals.map((a) => {
              const description =
                a.description ||
                a.action ||
                a.summary ||
                "Approval requested by the agent.";
              const details = parseApprovalDetails(a);
              const risk = details?.risk_level || a.risk_level;
              return (
                <div
                  key={a.id}
                  className="card p-5 transition hover:border-primary-500/30"
                >
                  <div className="mb-4 flex items-start gap-3">
                    <AlertTriangle
                      size={18}
                      className="mt-0.5 shrink-0 text-amber-500"
                    />
                    <div className="flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-ink">
                          {description}
                        </p>
                        {risk && (
                          <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium uppercase text-amber-700 dark:text-amber-300">
                            {risk}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-ink-subtle">
                        <span className="flex items-center gap-1">
                          <Clock size={11} />
                          {relativeTime(a.created_at)}
                        </span>
                        {a.requested_by && (
                          <span>Requested by {a.requested_by}</span>
                        )}
                        {a.expires_at && (
                          <span className="text-amber-700 dark:text-amber-300">
                            Expires {relativeTime(a.expires_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {details && (
                    <div className="mb-4 rounded-lg border border-surface-600 bg-surface-800/60 p-4">
                      <dl className="grid gap-4 sm:grid-cols-2">
                        <DetailRow
                          label="Repository"
                          value={details.repository}
                        />
                        <DetailRow
                          label="Workflow run"
                          value={details.workflow_run_id}
                        />
                        <DetailRow
                          label="Predicted failure"
                          value={details.predicted_failure}
                        />
                        <DetailRow
                          label="Workflow file"
                          value={details.workflow_path}
                        />
                        <DetailRow
                          label="Suggested fix"
                          value={details.suggested_fix}
                        />
                        <DetailRow
                          label="Workflow URL"
                          value={details.workflow_url}
                        />
                      </dl>
                      {details.proposed_file_changes &&
                        details.proposed_file_changes.length > 0 && (
                          <div className="mt-4">
                            <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
                              Proposed file changes
                            </p>
                            <ul className="mt-2 space-y-1 text-sm text-ink-subtle">
                              {details.proposed_file_changes.map(
                                (change, index) => (
                                  <li key={`${a.id}-${index}`}>{change}</li>
                                ),
                              )}
                            </ul>
                          </div>
                        )}
                    </div>
                  )}

                  {a.status === "pending" && (
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() => decide(a.id, true)}
                        disabled={decidingId === a.id}
                        className="flex items-center gap-1.5 rounded-xl bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-500 disabled:cursor-not-allowed disabled:bg-surface-600 disabled:text-ink-faint"
                      >
                        {decidingId === a.id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <CheckCircle size={14} />
                        )}
                        Approve
                      </button>
                      <button
                        onClick={() => decide(a.id, false)}
                        disabled={decidingId === a.id}
                        className="flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60 dark:text-red-300"
                      >
                        {decidingId === a.id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <XCircle size={14} />
                        )}
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
