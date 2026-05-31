import { useState } from 'react'
import { AlertCircle, FileCode2, Loader2, Sparkles, Wand2 } from 'lucide-react'
import { cicdAssistantService, type DetectedStack, type FailurePrediction } from '@/services/api'

const sampleLog = `npm ERR! Missing script: "test"
npm ERR!
npm ERR! To see a list of scripts, run:
npm ERR!   npm run`

const sampleFiles = `package.json
package-lock.json
src/App.tsx
vite.config.ts
Dockerfile`

function formatConfidence(value: number | null) {
  if (value === null || Number.isNaN(value)) return 'Not available'
  return `${Math.round(value * 100)}%`
}

function stackSummary(stack: DetectedStack) {
  return [
    stack.language,
    stack.framework,
    stack.package_manager,
    stack.has_docker ? 'Docker' : null,
    stack.has_existing_workflows ? 'existing workflow' : null,
  ].filter(Boolean).join(' / ')
}

export default function DiagnosisPage() {
  const [logText, setLogText] = useState(sampleLog)
  const [prediction, setPrediction] = useState<FailurePrediction | null>(null)
  const [predicting, setPredicting] = useState(false)
  const [predictionError, setPredictionError] = useState('')

  const [fileList, setFileList] = useState(sampleFiles)
  const [stack, setStack] = useState<DetectedStack | null>(null)
  const [workflowYaml, setWorkflowYaml] = useState('')
  const [workflowPath, setWorkflowPath] = useState('')
  const [generating, setGenerating] = useState(false)
  const [workflowError, setWorkflowError] = useState('')

  const predictFailure = async () => {
    const trimmedLog = logText.trim()
    if (!trimmedLog || predicting) return

    setPredicting(true)
    setPredictionError('')
    try {
      const result = await cicdAssistantService.predictFailure(trimmedLog)
      setPrediction(result)
    } catch (err: any) {
      setPrediction(null)
      setPredictionError(err.response?.data?.detail || err.message || 'Unable to predict this failure.')
    } finally {
      setPredicting(false)
    }
  }

  const generateWorkflow = async () => {
    const files = fileList.split(/\r?\n/).map((file) => file.trim()).filter(Boolean)
    if (files.length === 0 || generating) return

    setGenerating(true)
    setWorkflowError('')
    try {
      const result = await cicdAssistantService.generateWorkflow(files)
      setStack(result.stack)
      setWorkflowPath(result.path)
      setWorkflowYaml(result.workflow_yaml)
    } catch (err: any) {
      setStack(null)
      setWorkflowPath('')
      setWorkflowYaml('')
      setWorkflowError(err.response?.data?.detail || err.message || 'Unable to generate a workflow.')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary-500/30 bg-primary-500/10">
            <Sparkles size={19} className="text-primary-600 dark:text-primary-300" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">CI/CD Assistant</h1>
            <p className="text-xs text-ink-subtle">MVP testing for failure diagnosis and workflow generation</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
        <div className="mx-auto grid max-w-6xl gap-5 xl:grid-cols-2">
          <section className="card overflow-hidden">
            <div className="border-b border-surface-600 px-5 py-4">
              <div className="flex items-center gap-2">
                <AlertCircle size={18} className="text-amber-600 dark:text-amber-300" />
                <h2 className="text-sm font-semibold text-ink">Failure Log Classifier</h2>
              </div>
              <p className="mt-1 text-xs text-ink-subtle">Paste a CI/CD error log and predict the likely failure type.</p>
            </div>
            <div className="space-y-4 p-5">
              <textarea
                value={logText}
                onChange={(event) => setLogText(event.target.value)}
                className="input-field min-h-48 resize-y p-3 font-mono text-xs leading-5"
                placeholder="Paste CI/CD log text here"
              />
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={predictFailure}
                  disabled={!logText.trim() || predicting}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {predicting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                  Predict Failure
                </button>
                {predictionError && <span className="text-sm text-red-600 dark:text-red-300">{predictionError}</span>}
              </div>

              {prediction && (
                <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">Label</p>
                      <p className="mt-1 font-mono text-sm font-semibold text-ink">{prediction.label}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">Confidence</p>
                      <p className="mt-1 text-sm font-semibold text-ink">{formatConfidence(prediction.confidence)}</p>
                    </div>
                  </div>
                  <div className="mt-4 border-t border-surface-600 pt-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">Suggested Fix</p>
                    <p className="mt-2 text-sm leading-6 text-ink">{prediction.suggested_fix}</p>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="card overflow-hidden">
            <div className="border-b border-surface-600 px-5 py-4">
              <div className="flex items-center gap-2">
                <FileCode2 size={18} className="text-blue-600 dark:text-blue-300" />
                <h2 className="text-sm font-semibold text-ink">Workflow Generator</h2>
              </div>
              <p className="mt-1 text-xs text-ink-subtle">List repository files, one per line, and generate GitHub Actions YAML.</p>
            </div>
            <div className="space-y-4 p-5">
              <textarea
                value={fileList}
                onChange={(event) => setFileList(event.target.value)}
                className="input-field min-h-48 resize-y p-3 font-mono text-xs leading-5"
                placeholder={'package.json\nsrc/App.tsx\nDockerfile'}
              />
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={generateWorkflow}
                  disabled={!fileList.trim() || generating}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {generating ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />}
                  Generate Workflow
                </button>
                {workflowError && <span className="text-sm text-red-600 dark:text-red-300">{workflowError}</span>}
              </div>

              {stack && (
                <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">Detected Stack</p>
                  <p className="mt-2 text-sm font-semibold text-ink">{stackSummary(stack)}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="badge-info">{stack.recommended_workflow}</span>
                    {workflowPath && <span className="badge-success">{workflowPath}</span>}
                  </div>
                </div>
              )}

              {workflowYaml && (
                <pre className="max-h-96 overflow-auto rounded-2xl border border-surface-600 bg-surface-950 p-4 text-xs leading-5 text-ink">
                  <code>{workflowYaml}</code>
                </pre>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
