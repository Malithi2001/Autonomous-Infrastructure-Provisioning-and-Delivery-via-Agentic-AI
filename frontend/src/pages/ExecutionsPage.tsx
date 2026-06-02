import { getDebugHint, getUserFriendlyError } from "@/lib/errorMessages";
import { executionService } from "@/services/api";
import { formatDistanceToNow } from "date-fns";
import { Activity, AlertCircle, CheckCircle, Clock, Loader, X, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

interface Execution {
  id: string;
  requested_by: string;
  tool_name: string;
  status: string;
  source: string;
  summary: string;
  details?: string;
  started_at?: string;
  completed_at?: string;
}

interface Filters {
  tool: string | null;
  status: string | null;
  actor: string | null;
  days: number;
}

const TOOL_OPTIONS = [
  "failure_prediction_model",
  "github_create_workflow_pr",
  "github_create_fix_pr",
  "github_workflow_pr",
  "github_fix_pr",
  "repository_analyzer",
  "workflow_generator",
  "fix_recommendation",
  "approval_decision",
  "github_log_downloader",
];

const STATUS_OPTIONS = ["completed", "failed", "pending", "cancelled"];

const statusIcon = (status: string) => {
  switch (status) {
    case "success":
    case "completed":
      return (
        <CheckCircle
          size={14}
          className="text-primary-600 dark:text-primary-300"
        />
      );
    case "failed":
      return <XCircle size={14} className="text-red-500 dark:text-red-300" />;
    case "running":
      return (
        <Loader
          size={14}
          className="animate-spin text-blue-500 dark:text-blue-300"
        />
      );
    default:
      return <Clock size={14} className="text-ink-subtle" />;
  }
};

const statusBadge = (status: string) => {
  const classes: Record<string, string> = {
    completed: "badge-success",
    success: "badge-success",
    running: "badge-info",
    failed: "badge-error",
    cancelled: "badge-warning",
  };
  const cls = classes[status] || "badge-info";
  return <span className={cls}>{status}</span>;
};

const relativeTime = (value?: string) => {
  if (!value) return "time unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "time unknown";
  return formatDistanceToNow(date, { addSuffix: true });
};

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<Filters>({
    tool: null,
    status: null,
    actor: null,
    days: 7,
  });

  const fetchExecutions = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await executionService.list({
        tool: filters.tool,
        status: filters.status,
        actor: filters.actor,
        days: filters.days,
      });
      setExecutions(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setExecutions([]);
      setError(getUserFriendlyError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExecutions();
  }, [filters]);

  const handleClearFilters = () => {
    setFilters({ tool: null, status: null, actor: null, days: 7 });
  };

  const hasActiveFilters = filters.tool || filters.status || filters.actor;

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-blue-500/30 bg-blue-500/10">
            <Activity size={19} className="text-blue-600 dark:text-blue-300" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">Audit Log</h1>
            <p className="text-xs text-ink-subtle">
              Recent model, GitHub, approval, and agent actions
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 items-center">
          <select
            value={filters.tool || ""}
            onChange={(e) =>
              setFilters({ ...filters, tool: e.target.value || null })
            }
            className="text-sm px-2 py-1 rounded border border-surface-600 bg-surface-800 text-ink"
          >
            <option value="">All Tools</option>
            {TOOL_OPTIONS.map((tool) => (
              <option key={tool} value={tool}>
                {tool}
              </option>
            ))}
          </select>

          <select
            value={filters.status || ""}
            onChange={(e) =>
              setFilters({ ...filters, status: e.target.value || null })
            }
            className="text-sm px-2 py-1 rounded border border-surface-600 bg-surface-800 text-ink"
          >
            <option value="">All Status</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>

          <select
            value={filters.days.toString()}
            onChange={(e) =>
              setFilters({ ...filters, days: parseInt(e.target.value) })
            }
            className="text-sm px-2 py-1 rounded border border-surface-600 bg-surface-800 text-ink"
          >
            <option value="1">Last 24 hours</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
          </select>

          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="text-sm px-2 py-1 rounded border border-surface-600 bg-surface-800 text-ink-subtle hover:text-ink flex items-center gap-1"
            >
              <X size={14} />
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          </div>
        ) : error ? (
          <div className="mx-auto max-w-3xl rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-red-700 dark:text-red-200">
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
        ) : executions.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 rounded-3xl border border-surface-600 bg-surface-800 p-4">
              <Clock size={40} className="text-ink-subtle" />
            </div>
            <p className="font-medium text-ink">No executions found</p>
            <p className="mt-1 text-sm text-ink-subtle">
              Try adjusting your filters or check back later.
            </p>
          </div>
        ) : (
          <div className="mx-auto max-w-4xl space-y-2">
            {executions.map((ex) => (
              <div
                key={ex.id}
                className="card flex flex-col gap-2 px-4 py-3 transition-colors hover:border-primary-500/30"
              >
                <div className="flex items-center gap-4">
                  <div className="shrink-0">{statusIcon(ex.status)}</div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">
                      {ex.summary}
                    </p>
                    <p className="mt-0.5 text-xs text-ink-subtle">
                      {ex.source && (
                        <span className="mr-2 font-mono text-primary-700 dark:text-primary-300">
                          {ex.source}
                        </span>
                      )}
                      {ex.tool_name && (
                        <span className="mr-2 font-mono text-ink-subtle">
                          {ex.tool_name}
                        </span>
                      )}
                      {relativeTime(ex.started_at)}
                    </p>
                  </div>
                  <div className="shrink-0">{statusBadge(ex.status)}</div>
                </div>
                {ex.requested_by && (
                  <p className="text-xs text-ink-subtle ml-8">
                    By: {ex.requested_by}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
