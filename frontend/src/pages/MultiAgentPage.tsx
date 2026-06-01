import { useMemo, useState } from "react";
import {
  Bot,
  Braces,
  CheckCircle2,
  Loader2,
  Network,
  Play,
  Route,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { agentService, type AgentOrchestrationResult } from "@/services/api";

const demoContexts = {
  containers: "{}",
  reactWorkflow: JSON.stringify(
    {
      files: [
        "package.json",
        "package-lock.json",
        "src/App.jsx",
        "vite.config.js",
      ],
    },
    null,
    2,
  ),
  npmLog: JSON.stringify(
    {
      log_text:
        'npm ERR! Missing script: "test"\nnpm ERR! To see a list of scripts, run:\nnpm ERR!   npm run',
    },
    null,
    2,
  ),
  repoScan: JSON.stringify(
    {
      repo_full_name: "owner/repo",
    },
    null,
    2,
  ),
};

const quickDemos = [
  {
    label: "Show running containers",
    message: "show running containers",
    context: demoContexts.containers,
  },
  {
    label: "Generate CI workflow for React project",
    message: "generate CI workflow",
    context: demoContexts.reactWorkflow,
  },
  {
    label: "Analyze npm missing test script log",
    message: "analyze this log",
    context: demoContexts.npmLog,
  },
  {
    label: "Scan GitHub repository",
    message: "scan repository",
    context: demoContexts.repoScan,
  },
];

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function errorMessage(err: unknown) {
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { data?: { detail?: string } } })
      .response;
    if (response?.data?.detail) return response.data.detail;
  }
  if (err instanceof Error) return err.message;
  return "Unable to run the agent request.";
}

function riskBadgeClass(risk: string) {
  if (risk === "high") return "badge-error";
  if (risk === "medium") return "badge-warning";
  return "badge-success";
}

function ResultPanel({ result }: { result: AgentOrchestrationResult }) {
  const toolCalled =
    typeof result.metadata.tool_called === "string"
      ? result.metadata.tool_called
      : typeof result.metadata.proposed_tool_call === "string"
        ? result.metadata.proposed_tool_call
        : "Not reported";

  return (
    <section className="card overflow-hidden">
      <div className="border-b border-surface-600 px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {result.success ? (
              <CheckCircle2
                size={18}
                className="text-primary-600 dark:text-primary-300"
              />
            ) : (
              <ShieldAlert
                size={18}
                className="text-amber-600 dark:text-amber-300"
              />
            )}
            <h2 className="text-sm font-semibold text-ink">Agent Result</h2>
          </div>
          <span className={riskBadgeClass(result.risk_level)}>
            {result.risk_level}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
              Selected Agent
            </p>
            <p className="mt-2 break-words font-mono text-sm font-semibold text-ink">
              {result.selected_agent}
            </p>
          </div>
          <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
              Intent
            </p>
            <p className="mt-2 break-words font-mono text-sm font-semibold text-ink">
              {result.intent}
            </p>
          </div>
          <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
              Success
            </p>
            <p className="mt-2 text-sm font-semibold text-ink">
              {result.success ? "true" : "false"}
            </p>
          </div>
          <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
              Tool Called
            </p>
            <p className="mt-2 break-words font-mono text-sm font-semibold text-ink">
              {toolCalled}
            </p>
          </div>
        </div>

        <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
            Result
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink">
            {result.result}
          </p>
        </div>

        <details className="rounded-2xl border border-surface-600 bg-surface-950">
          <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-ink">
            Metadata JSON
          </summary>
          <pre className="max-h-96 overflow-auto border-t border-surface-600 p-4 text-xs leading-5 text-ink">
            <code>{formatJson(result.metadata)}</code>
          </pre>
        </details>
      </div>
    </section>
  );
}

export default function MultiAgentPage() {
  const [message, setMessage] = useState("show running containers");
  const [contextText, setContextText] = useState(demoContexts.containers);
  const [result, setResult] = useState<AgentOrchestrationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const parsedContextPreview = useMemo(() => {
    try {
      return JSON.parse(contextText || "{}") as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [contextText]);

  const runAgent = async () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || loading) return;

    let context: Record<string, unknown>;
    try {
      context = JSON.parse(contextText || "{}") as Record<string, unknown>;
    } catch {
      setError("Context must be valid JSON.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await agentService.orchestrate(trimmedMessage, context);
      setResult(response);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const applyDemo = (demo: (typeof quickDemos)[number]) => {
    setMessage(demo.message);
    setContextText(demo.context);
    setError("");
  };

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary-500/30 bg-primary-500/10">
            <Network
              size={19}
              className="text-primary-600 dark:text-primary-300"
            />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">
              Multi-Agent Orchestration
            </h1>
            <p className="text-xs text-ink-subtle">
              Route one user request through the orchestration agent and
              specialized agents
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
        <div className="mx-auto max-w-6xl space-y-5">
          <section className="card overflow-hidden">
            <div className="border-b border-surface-600 px-5 py-4">
              <div className="flex items-center gap-2">
                <Route
                  size={18}
                  className="text-primary-600 dark:text-primary-300"
                />
                <h2 className="text-sm font-semibold text-ink">
                  Run Agent Flow
                </h2>
              </div>
            </div>

            <div className="space-y-5 p-5">
              <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                <div>
                  <label
                    htmlFor="agent-command"
                    className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-subtle"
                  >
                    User Command
                  </label>
                  <textarea
                    id="agent-command"
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    className="input-field mt-3 min-h-36 resize-y p-3 text-sm leading-6"
                    placeholder="show running containers"
                  />
                </div>

                <div>
                  <label
                    htmlFor="agent-context"
                    className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-subtle"
                  >
                    Optional JSON Context
                  </label>
                  <textarea
                    id="agent-context"
                    value={contextText}
                    onChange={(event) => setContextText(event.target.value)}
                    className="input-field mt-3 min-h-36 resize-y p-3 font-mono text-xs leading-5"
                    placeholder='{"repo_full_name":"owner/repo"}'
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={runAgent}
                  disabled={!message.trim() || loading}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {loading ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <Play size={15} />
                  )}
                  Run Agent
                </button>
                <span
                  className={
                    parsedContextPreview ? "badge-success" : "badge-error"
                  }
                >
                  <Braces size={12} className="mr-1 inline" />
                  {parsedContextPreview ? "Valid JSON" : "Invalid JSON"}
                </span>
                {error && (
                  <span className="text-sm text-red-600 dark:text-red-300">
                    {error}
                  </span>
                )}
              </div>
            </div>
          </section>

          <section className="card p-5">
            <div className="mb-4 flex items-center gap-2">
              <Sparkles
                size={18}
                className="text-blue-600 dark:text-blue-300"
              />
              <h2 className="text-sm font-semibold text-ink">
                Quick Demo Buttons
              </h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {quickDemos.map((demo) => (
                <button
                  key={demo.label}
                  type="button"
                  onClick={() => applyDemo(demo)}
                  className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4 text-left text-sm font-medium text-ink transition hover:border-primary-500/40 hover:bg-primary-500/10"
                >
                  <Bot
                    size={16}
                    className="mb-3 text-primary-600 dark:text-primary-300"
                  />
                  {demo.label}
                </button>
              ))}
            </div>
          </section>

          {result && <ResultPanel result={result} />}
        </div>
      </div>
    </div>
  );
}
