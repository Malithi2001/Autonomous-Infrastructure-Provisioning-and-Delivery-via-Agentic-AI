import { getDebugHint, getUserFriendlyError } from "@/lib/errorMessages";
import {
  cicdAssistantService,
  type DetectedStack,
  type FailurePrediction,
} from "@/services/api";
import { AlertCircle, FileCode2, Loader2, Sparkles, Wand2 } from "lucide-react";
import { useState } from "react";

const sampleLog = `npm ERR! Missing script: "test"
npm ERR!
npm ERR! To see a list of scripts, run:
npm ERR!   npm run`;

const sampleFiles = `package.json
package-lock.json
src/App.tsx
vite.config.ts
Dockerfile`;

const sampleLogs = [
  {
    label: "npm missing test script",
    value: `npm ERR! Missing script: "test"
npm ERR! To see a list of scripts, run:
npm ERR!   npm run`,
  },
  {
    label: "npm missing lockfile",
    value: "npm ERR! package-lock.json is required for reproducible installs when running npm ci.",
  },
  {
    label: "Python missing dependency",
    value: "ModuleNotFoundError: No module named 'pydantic_settings' while loading app.core.config",
  },
  {
    label: "pytest not found",
    value: "Run pytest -q failed: /usr/bin/bash: pytest: command not found",
  },
  {
    label: "Docker build failed",
    value: "Docker build failed: COPY requirements.txt /app/requirements.txt no such file or directory",
  },
];

function formatConfidence(value: number | null) {
  if (value === null || Number.isNaN(value)) return "Not available";
  return `${Math.round(value * 100)}%`;
}

function stackSummary(stack: DetectedStack) {
  return [
    stack.language,
    stack.framework,
    stack.package_manager,
    stack.has_docker ? "Docker" : null,
    stack.has_existing_workflows ? "existing workflow" : null,
  ]
    .filter(Boolean)
    .join(" / ");
}

export default function DiagnosisPage() {
  const [logText, setLogText] = useState(sampleLog);
  const [prediction, setPrediction] = useState<FailurePrediction | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState("");

  const [fileList, setFileList] = useState(sampleFiles);
  const [stack, setStack] = useState<DetectedStack | null>(null);
  const [workflowYaml, setWorkflowYaml] = useState("");
  const [workflowPath, setWorkflowPath] = useState("");
  const [generating, setGenerating] = useState(false);
  const [workflowError, setWorkflowError] = useState("");

  const predictFailure = async () => {
    const trimmedLog = logText.trim();
    if (!trimmedLog || predicting) return;

    setPredicting(true);
    setPredictionError("");
    try {
      const result = await cicdAssistantService.predictFailure(trimmedLog);
      setPrediction(result);
    } catch (err: any) {
      setPrediction(null);
      setPredictionError(getUserFriendlyError(err));
    } finally {
      setPredicting(false);
    }
  };

  const generateWorkflow = async () => {
    const files = fileList
      .split(/\r?\n/)
      .map((file) => file.trim())
      .filter(Boolean);
    if (files.length === 0 || generating) return;

    setGenerating(true);
    setWorkflowError("");
    try {
      const result = await cicdAssistantService.generateWorkflow(files);
      setStack(result.stack);
      setWorkflowPath(result.path);
      setWorkflowYaml(result.workflow_yaml);
    } catch (err: any) {
      setStack(null);
      setWorkflowPath("");
      setWorkflowYaml("");
      setWorkflowError(getUserFriendlyError(err));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-4 py-4 backdrop-blur md:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary-500/30 bg-primary-500/10">
            <Sparkles
              size={19}
              className="text-primary-600 dark:text-primary-300"
            />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">
              CI/CD Assistant
            </h1>
            <p className="text-xs text-ink-subtle">
              MVP testing for failure diagnosis and workflow generation
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
        <div className="mx-auto grid max-w-6xl gap-5 xl:grid-cols-2">
          <section className="card overflow-hidden">
            <div className="border-b border-surface-600 px-5 py-4">
              <div className="flex items-center gap-2">
                <AlertCircle
                  size={18}
                  className="text-amber-600 dark:text-amber-300"
                />
                <h2 className="text-sm font-semibold text-ink">
                  Failure Log Classifier
                </h2>
              </div>
              <p className="mt-1 text-xs text-ink-subtle">
                Paste a CI/CD error log and predict the likely failure type.
              </p>
            </div>
            <div className="space-y-4 p-4 sm:p-5">
              <textarea
                value={logText}
                onChange={(event) => setLogText(event.target.value)}
                className="input-field min-h-48 resize-y p-3 font-mono text-xs leading-5"
                placeholder="Paste CI/CD log text here"
              />
              <div className="flex flex-wrap gap-2">
                {sampleLogs.map((sample) => (
                  <button
                    key={sample.label}
                    type="button"
                    onClick={() => {
                      setLogText(sample.value);
                      setPrediction(null);
                      setPredictionError("");
                    }}
                    className="btn-ghost border border-surface-600 bg-surface-900/70"
                  >
                    {sample.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                <button
                  onClick={predictFailure}
                  disabled={!logText.trim() || predicting}
                  className="btn-primary w-full sm:w-auto"
                >
                  {predicting ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <Sparkles size={15} />
                  )}
                  Predict Failure
                </button>
                {predictionError && (
                  <div className="w-full">
                    <div className="inline-flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-200">
                      <AlertCircle size={16} className="mt-0.5 shrink-0" />
                      <div>
                        <p className="font-semibold">{predictionError}</p>
                        {getDebugHint(predictionError) && (
                          <p className="mt-1 text-xs opacity-80">
                            Tip: {getDebugHint(predictionError)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {prediction && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
                      Label
                    </p>
                    <p className="mt-1 font-mono text-sm font-semibold text-ink">
                      {prediction.label}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
                      Confidence
                    </p>
                    <p className="mt-1 text-sm font-semibold text-ink">
                      {formatConfidence(prediction.confidence)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4 sm:col-span-2">
                    <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
                      Suggested Fix
                    </p>
                    <p className="mt-2 text-sm leading-6 text-ink">
                      {prediction.suggested_fix}
                    </p>
                  </div>
                  {prediction.recommendation &&
                    typeof prediction.recommendation.risk_level ===
                      "string" && (
                      <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4 sm:col-span-2">
                        <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
                          Risk Level
                        </p>
                        <p className="mt-1 text-sm font-semibold text-ink">
                          {prediction.recommendation.risk_level}
                        </p>
                      </div>
                    )}
                </div>
              )}
            </div>
          </section>

          <section className="card overflow-hidden">
            <div className="border-b border-surface-600 px-5 py-4">
              <div className="flex items-center gap-2">
                <FileCode2
                  size={18}
                  className="text-blue-600 dark:text-blue-300"
                />
                <h2 className="text-sm font-semibold text-ink">
                  Workflow Generator
                </h2>
              </div>
              <p className="mt-1 text-xs text-ink-subtle">
                List repository files, one per line, and generate GitHub Actions
                YAML.
              </p>
            </div>
            <div className="space-y-4 p-4 sm:p-5">
              <textarea
                value={fileList}
                onChange={(event) => setFileList(event.target.value)}
                className="input-field min-h-48 resize-y p-3 font-mono text-xs leading-5"
                placeholder={"package.json\nsrc/App.tsx\nDockerfile"}
              />
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                <button
                  onClick={generateWorkflow}
                  disabled={!fileList.trim() || generating}
                  className="btn-primary w-full sm:w-auto"
                >
                  {generating ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <Wand2 size={15} />
                  )}
                  Generate Workflow
                </button>
                {workflowError && (
                  <div className="w-full">
                    <div className="inline-flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-200">
                      <AlertCircle size={16} className="mt-0.5 shrink-0" />
                      <div>
                        <p className="font-semibold">{workflowError}</p>
                        {getDebugHint(workflowError) && (
                          <p className="mt-1 text-xs opacity-80">
                            Tip: {getDebugHint(workflowError)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {stack && (
                <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">
                    Detected Stack
                  </p>
                  <p className="mt-2 text-sm font-semibold text-ink">
                    {stackSummary(stack)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="badge-info">
                      {stack.recommended_workflow}
                    </span>
                    {workflowPath && (
                      <span className="badge-success">{workflowPath}</span>
                    )}
                  </div>
                </div>
              )}

              {workflowYaml && (
                <pre className="max-h-96 max-w-full overflow-auto rounded-2xl border border-surface-600 bg-surface-950 p-4 text-xs leading-5 text-ink">
                  <code>{workflowYaml}</code>
                </pre>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
