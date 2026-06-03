import { getDebugHint, getUserFriendlyError } from "@/lib/errorMessages";
import { hasPermission } from "@/lib/rbac";
import {
  approvalService,
  executionService,
  healthService,
  workflowFailureService,
  type SystemStatus,
  type WorkflowFailure,
} from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { formatDistanceToNow } from "date-fns";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileCode2,
  GitPullRequest,
  History,
  Loader2,
  Network,
  RefreshCw,
  SearchCode,
  Server,
  Settings,
  ShieldCheck,
  Terminal,
  TriangleAlert,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { IS_MOBILE_MODE } from "@/config/runtime";

interface Approval {
  id: string;
  action?: string;
  summary?: string;
  risk_level?: string;
  requested_by?: string;
  created_at?: string;
  status: string;
}

interface Execution {
  id: string;
  requested_by?: string;
  tool_name?: string;
  status: string;
  source?: string;
  summary: string;
  started_at?: string;
}

interface DashboardData {
  status: SystemStatus | null;
  approvals: Approval[];
  failures: WorkflowFailure[];
  executions: Execution[];
}

type LoadState = "idle" | "loading" | "ready" | "error";

function relativeTime(value?: string | null) {
  if (!value) return "time unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "time unknown";
  return formatDistanceToNow(date, { addSuffix: true });
}

function metricTone(value: "good" | "warn" | "info") {
  const tones = {
    good: "border-primary-500/30 bg-primary-500/10 text-primary-700 dark:text-primary-200",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-200",
    info: "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-200",
  };
  return tones[value];
}

function statusBadge(status: string) {
  const normalized = status.toLowerCase();
  if (["ok", "ready", "completed", "diagnosed", "success"].includes(normalized)) {
    return <span className="badge-success">{status}</span>;
  }
  if (["failed", "error", "diagnosis_failed", "rejected"].includes(normalized)) {
    return <span className="badge-error">{status}</span>;
  }
  if (["pending", "approval_pending", "running"].includes(normalized)) {
    return <span className="badge-warning">{status}</span>;
  }
  return <span className="badge-info">{status}</span>;
}

function iconForExecution(status: string) {
  if (["completed", "success"].includes(status)) return CheckCircle2;
  if (status === "failed") return AlertCircle;
  if (status === "running") return Loader2;
  return Clock3;
}

function SectionHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex min-w-0 items-end justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {subtitle && (
          <p className="mt-1 text-xs leading-5 text-ink-subtle">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}

function KpiCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  tone: "good" | "warn" | "info";
}) {
  return (
    <div className="rounded-lg border border-surface-600 bg-surface-800 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-medium uppercase tracking-[0.12em] text-ink-subtle">
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold leading-none text-ink">
            {value}
          </p>
        </div>
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${metricTone(tone)}`}
        >
          <Icon size={17} />
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-ink-subtle">{detail}</p>
    </div>
  );
}

function ActionButton({
  label,
  icon: Icon,
  onClick,
}: {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-surface-600 bg-surface-800 px-3 text-sm font-semibold text-ink transition hover:border-primary-500/40 hover:bg-primary-500/10 hover:text-primary-700 dark:hover:text-primary-200"
    >
      <Icon size={15} />
      <span className="whitespace-nowrap">{label}</span>
    </button>
  );
}

function EmptyState({
  icon: Icon,
  title,
  detail,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
}) {
  return (
    <div className="flex min-h-36 flex-col items-center justify-center rounded-lg border border-dashed border-surface-600 bg-surface-900/50 px-4 py-6 text-center">
      <Icon size={24} className="text-ink-faint" />
      <p className="mt-3 text-sm font-semibold text-ink">{title}</p>
      <p className="mt-1 max-w-md text-xs leading-5 text-ink-subtle">{detail}</p>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState("");
  const [data, setData] = useState<DashboardData>({
    status: null,
    approvals: [],
    failures: [],
    executions: [],
  });

  const canReadApprovals = hasPermission(user?.role, "approvals:read");
  const canReadFailures = hasPermission(user?.role, "workflow_failures:read");
  const canReadExecutions =
    hasPermission(user?.role, "executions:read") ||
    hasPermission(user?.role, "audit:read");

  const loadDashboard = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      const [statusResult, approvalsResult, failuresResult, executionsResult] =
        await Promise.allSettled([
          healthService.status(),
          canReadApprovals ? approvalService.list() : Promise.resolve([]),
          canReadFailures ? workflowFailureService.list(5) : Promise.resolve([]),
          canReadExecutions
            ? executionService.list({ limit: 5, days: 7 })
            : Promise.resolve([]),
        ]);

      if (statusResult.status === "rejected") {
        throw statusResult.reason;
      }

      setData({
        status: statusResult.value,
        approvals:
          approvalsResult.status === "fulfilled" && Array.isArray(approvalsResult.value)
            ? approvalsResult.value
            : [],
        failures:
          failuresResult.status === "fulfilled" && Array.isArray(failuresResult.value)
            ? failuresResult.value
            : [],
        executions:
          executionsResult.status === "fulfilled" && Array.isArray(executionsResult.value)
            ? executionsResult.value
            : [],
      });
      setState("ready");
    } catch (err) {
      setError(getUserFriendlyError(err));
      setState("error");
    }
  }, [canReadApprovals, canReadExecutions, canReadFailures]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const serviceRows = useMemo(() => {
    if (!data.status) return [];
    return [
      {
        name: "Backend API",
        owner: "FastAPI",
        state: data.status.backend_api.status === "ok" ? "Ready" : "Issue",
        message: data.status.backend_api.message,
        ok: data.status.backend_api.status === "ok",
        icon: Server,
      },
      {
        name: IS_MOBILE_MODE ? "Docker Runtime" : "Docker",
        owner: IS_MOBILE_MODE ? "Backend host" : "Local host",
        state: data.status.docker.available ? "Ready" : "Limited",
        message: IS_MOBILE_MODE
          ? "Docker commands execute on the configured backend host."
          : data.status.docker.message,
        ok: data.status.docker.available,
        icon: Activity,
      },
      {
        name: "GitHub",
        owner: "Repository automation",
        state: data.status.github.configured ? "Configured" : "Missing",
        message: data.status.github.message,
        ok: data.status.github.configured,
        icon: GitPullRequest,
      },
      {
        name: "ML Model",
        owner: "Failure classifier",
        state: data.status.ml_model.available ? "Available" : "Missing",
        message: data.status.ml_model.message,
        ok: data.status.ml_model.available,
        icon: Workflow,
      },
    ];
  }, [data.status]);

  const readyCount = serviceRows.filter((row) => row.ok).length;
  const failedExecutions = data.executions.filter((item) => item.status === "failed").length;
  const modeLabel = IS_MOBILE_MODE
    ? "Mobile"
    : data.status?.desktop_mode.enabled
      ? "Desktop"
      : "Web";
  const automationFlow: Array<[string, LucideIcon]> = [
    ["User request", Bot],
    ["Orchestration agent", Network],
    ["Specialized agent", Workflow],
    ["Tool or service", Terminal],
    ["Structured response", ArrowRight],
  ];

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <header className="shrink-0 border-b border-surface-600 bg-surface-900/95 px-4 py-4 backdrop-blur md:px-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-700 dark:text-primary-200">
                <Bot size={19} />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold text-ink">
                  Operations Dashboard
                </h1>
                <p className="mt-1 text-xs leading-5 text-ink-subtle">
                  CI/CD automation health, approvals, failures, and audit
                  activity in one working view.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex min-h-9 items-center rounded-lg border border-surface-600 bg-surface-800 px-3 text-xs font-semibold text-ink">
              Mode: {modeLabel}
            </span>
            <span className="inline-flex min-h-9 items-center rounded-lg border border-surface-600 bg-surface-800 px-3 text-xs font-semibold text-ink">
              Access: {data.status?.desktop_mode.auth_disabled ? "Local bypass" : "RBAC"}
            </span>
            <button
              type="button"
              onClick={loadDashboard}
              disabled={state === "loading"}
              className="btn-secondary min-h-9 rounded-lg px-3 py-0"
            >
              <RefreshCw
                size={14}
                className={state === "loading" ? "animate-spin" : ""}
              />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5 md:px-6 md:py-6">
        <div className="mx-auto max-w-7xl space-y-6">
          {state === "error" && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-700 dark:text-red-200">
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
          )}

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Readiness"
              value={state === "loading" ? "..." : `${readyCount}/${serviceRows.length || 4}`}
              detail="Core services reporting healthy"
              icon={CheckCircle2}
              tone={readyCount >= 3 ? "good" : "warn"}
            />
            <KpiCard
              label="Approvals"
              value={canReadApprovals ? data.approvals.length : "-"}
              detail={canReadApprovals ? "Pending human decisions" : "Not visible for this role"}
              icon={ShieldCheck}
              tone={data.approvals.length ? "warn" : "good"}
            />
            <KpiCard
              label="Failures"
              value={canReadFailures ? data.failures.length : "-"}
              detail={canReadFailures ? "Recent diagnosed workflow runs" : "Not visible for this role"}
              icon={TriangleAlert}
              tone={data.failures.length ? "warn" : "good"}
            />
            <KpiCard
              label="Audit"
              value={canReadExecutions ? data.executions.length : "-"}
              detail={failedExecutions ? `${failedExecutions} failed recently` : "Recent execution activity"}
              icon={History}
              tone={failedExecutions ? "warn" : "info"}
            />
          </section>

          <section className="rounded-lg border border-surface-600 bg-surface-800 px-4 py-3">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-subtle">
                  Primary Workflows
                </p>
                <p className="mt-1 text-sm text-ink">
                  Start the common demo tasks directly from the dashboard.
                </p>
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1 xl:pb-0">
                {!IS_MOBILE_MODE && (
                  <ActionButton
                    label="Containers"
                    icon={Terminal}
                    onClick={() => navigate("/multi-agent")}
                  />
                )}
                <ActionButton
                  label="Diagnose Logs"
                  icon={SearchCode}
                  onClick={() => navigate("/diagnosis")}
                />
                <ActionButton
                  label="Generate Workflow"
                  icon={FileCode2}
                  onClick={() => navigate("/diagnosis")}
                />
                <ActionButton
                  label="Repository Setup"
                  icon={GitPullRequest}
                  onClick={() => navigate("/repository-setup")}
                />
                <ActionButton
                  label="Settings"
                  icon={Settings}
                  onClick={() => navigate("/settings")}
                />
              </div>
            </div>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <div>
              <SectionHeader
                title="Service Readiness"
                subtitle="Runtime dependencies for the autonomous CI/CD loop."
              />
              <div className="overflow-hidden rounded-lg border border-surface-600 bg-surface-800">
                {state === "loading" ? (
                  <div className="flex h-48 items-center justify-center">
                    <Loader2 size={22} className="animate-spin text-primary-500" />
                  </div>
                ) : (
                  <div className="divide-y divide-surface-600">
                    {serviceRows.map(({ name, owner, state: rowState, message, ok, icon: Icon }) => (
                      <div
                        key={name}
                        className="grid gap-3 px-4 py-4 md:grid-cols-[1fr_7rem_1.4fr]"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-surface-600 bg-surface-900 text-primary-600 dark:text-primary-300">
                            <Icon size={16} />
                          </div>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-ink">
                              {name}
                            </p>
                            <p className="mt-1 truncate text-xs text-ink-subtle">
                              {owner}
                            </p>
                          </div>
                        </div>
                        <div className="md:self-center">
                          {ok ? statusBadge("Ready") : statusBadge(rowState)}
                        </div>
                        <p className="min-w-0 text-sm leading-6 text-ink-subtle md:self-center">
                          {message}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <SectionHeader
                title="Governed Automation"
                subtitle="Supervisor-required runtime path."
              />
              <div className="rounded-lg border border-surface-600 bg-surface-800 p-4">
                <div className="space-y-3">
                  {automationFlow.map(([label, Icon], index) => (
                    <div
                      key={String(label)}
                      className="flex items-center gap-3 rounded-lg border border-surface-600 bg-surface-900 px-3 py-2"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary-500/10 text-xs font-semibold text-primary-700 dark:text-primary-200">
                        {index + 1}
                      </div>
                      <Icon size={15} className="text-ink-subtle" />
                      <p className="text-sm font-medium text-ink">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-6 xl:grid-cols-3">
            <div>
              <SectionHeader
                title="Approval Queue"
                subtitle="High-risk work waiting for review."
                action={
                  canReadApprovals ? (
                    <button
                      type="button"
                      onClick={() => navigate("/approvals")}
                      className="btn-ghost min-h-8 rounded-lg px-2"
                    >
                      Open <ChevronRight size={14} />
                    </button>
                  ) : null
                }
              />
              {!canReadApprovals ? (
                <EmptyState
                  icon={ShieldCheck}
                  title="Approval queue hidden"
                  detail="This role can use safe workflows but cannot view approval requests."
                />
              ) : data.approvals.length === 0 ? (
                <EmptyState
                  icon={CheckCircle2}
                  title="No pending approvals"
                  detail="High-risk GitHub and automation actions will appear here."
                />
              ) : (
                <div className="space-y-2">
                  {data.approvals.slice(0, 4).map((approval) => (
                    <button
                      key={approval.id}
                      type="button"
                      onClick={() => navigate("/approvals")}
                      className="w-full rounded-lg border border-surface-600 bg-surface-800 px-3 py-3 text-left transition hover:border-primary-500/40"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="min-w-0 text-sm font-semibold text-ink">
                          {approval.summary || approval.action || "Approval requested"}
                        </p>
                        {statusBadge(approval.risk_level || approval.status)}
                      </div>
                      <p className="mt-2 text-xs text-ink-subtle">
                        {relativeTime(approval.created_at)}
                        {approval.requested_by ? ` by ${approval.requested_by}` : ""}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <SectionHeader
                title="Workflow Failures"
                subtitle="Recent CI/CD diagnoses."
                action={
                  canReadFailures ? (
                    <button
                      type="button"
                      onClick={() => navigate("/workflow-failures")}
                      className="btn-ghost min-h-8 rounded-lg px-2"
                    >
                      Open <ChevronRight size={14} />
                    </button>
                  ) : null
                }
              />
              {!canReadFailures ? (
                <EmptyState
                  icon={TriangleAlert}
                  title="Failures hidden"
                  detail="Workflow failure records are not visible for this role."
                />
              ) : data.failures.length === 0 ? (
                <EmptyState
                  icon={CheckCircle2}
                  title="No workflow failures"
                  detail="Failed GitHub Actions runs will appear after webhook diagnosis."
                />
              ) : (
                <div className="space-y-2">
                  {data.failures.slice(0, 4).map((failure) => (
                    <button
                      key={failure.id}
                      type="button"
                      onClick={() => navigate("/workflow-failures")}
                      className="w-full rounded-lg border border-surface-600 bg-surface-800 px-3 py-3 text-left transition hover:border-primary-500/40"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="min-w-0 truncate text-sm font-semibold text-ink">
                          {failure.repo_full_name}
                        </p>
                        {statusBadge(failure.status)}
                      </div>
                      <p className="mt-2 truncate text-xs text-ink-subtle">
                        {failure.predicted_label || "unclassified"} ·{" "}
                        {relativeTime(failure.created_at)}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <SectionHeader
                title="Recent Executions"
                subtitle="Latest agent, model, GitHub, and approval actions."
                action={
                  canReadExecutions ? (
                    <button
                      type="button"
                      onClick={() => navigate("/executions")}
                      className="btn-ghost min-h-8 rounded-lg px-2"
                    >
                      Open <ChevronRight size={14} />
                    </button>
                  ) : null
                }
              />
              {!canReadExecutions ? (
                <EmptyState
                  icon={History}
                  title="Audit hidden"
                  detail="Execution history is not visible for this role."
                />
              ) : data.executions.length === 0 ? (
                <EmptyState
                  icon={History}
                  title="No recent executions"
                  detail="Agent and API actions will appear here after use."
                />
              ) : (
                <div className="space-y-2">
                  {data.executions.slice(0, 5).map((execution) => {
                    const Icon = iconForExecution(execution.status);
                    return (
                      <button
                        key={execution.id}
                        type="button"
                        onClick={() => navigate("/executions")}
                        className="w-full rounded-lg border border-surface-600 bg-surface-800 px-3 py-3 text-left transition hover:border-primary-500/40"
                      >
                        <div className="flex items-start gap-3">
                          <Icon
                            size={15}
                            className={
                              execution.status === "running"
                                ? "mt-0.5 shrink-0 animate-spin text-blue-500"
                                : "mt-0.5 shrink-0 text-primary-600 dark:text-primary-300"
                            }
                          />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-ink">
                              {execution.summary}
                            </p>
                            <p className="mt-1 truncate text-xs text-ink-subtle">
                              {execution.tool_name || execution.source || "agent"} ·{" "}
                              {relativeTime(execution.started_at)}
                            </p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
