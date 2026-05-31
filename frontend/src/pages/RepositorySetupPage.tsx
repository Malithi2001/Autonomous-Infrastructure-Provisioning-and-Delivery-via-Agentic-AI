import { useState } from 'react'
import { ExternalLink, GitPullRequest, GitBranch, Loader2, Radar } from 'lucide-react'
import { repositoryService, type RepositoryScanResult, type WorkflowPRResult } from '@/services/api'

function stackSummary(stack: RepositoryScanResult['stack']) {
  return [
    stack.language,
    stack.framework,
    stack.package_manager,
    stack.has_docker ? 'Docker' : null,
    stack.has_existing_workflows ? 'existing workflow' : null,
  ].filter(Boolean).join(' / ')
}

function StackPanel({ result }: { result: RepositoryScanResult }) {
  return (
    <div className="rounded-2xl border border-surface-600 bg-surface-900/70 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">Detected Stack</p>
          <p className="mt-2 text-sm font-semibold text-ink">{stackSummary(result.stack)}</p>
        </div>
        <span className="badge-info">{result.stack.recommended_workflow}</span>
      </div>
      <div className="mt-4 grid gap-3 text-sm text-ink-subtle sm:grid-cols-2 lg:grid-cols-4">
        <span>Language: <span className="text-ink">{result.stack.language}</span></span>
        <span>Framework: <span className="text-ink">{result.stack.framework}</span></span>
        <span>Package: <span className="text-ink">{result.stack.package_manager}</span></span>
        <span>Files: <span className="text-ink">{result.files.length}</span></span>
      </div>
    </div>
  )
}

export default function RepositorySetupPage() {
  const [repoFullName, setRepoFullName] = useState('')
  const [scanResult, setScanResult] = useState<RepositoryScanResult | null>(null)
  const [prResult, setPrResult] = useState<WorkflowPRResult | null>(null)
  const [scanning, setScanning] = useState(false)
  const [creatingPr, setCreatingPr] = useState(false)
  const [error, setError] = useState('')

  const normalizedRepo = repoFullName.trim()

  const scanRepository = async () => {
    if (!normalizedRepo || scanning) return
    setScanning(true)
    setError('')
    setPrResult(null)
    try {
      const result = await repositoryService.scan(normalizedRepo)
      setScanResult(result)
    } catch (err: any) {
      setScanResult(null)
      setError(err.response?.data?.detail || err.message || 'Unable to scan this repository.')
    } finally {
      setScanning(false)
    }
  }

  const createWorkflowPr = async () => {
    if (!normalizedRepo || creatingPr) return
    setCreatingPr(true)
    setError('')
    try {
      const result = await repositoryService.createWorkflowPr(normalizedRepo)
      setPrResult(result)
      setScanResult((current) => current || { repo_full_name: result.repo_full_name, files: [], stack: result.detected_stack })
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Unable to create a workflow pull request.')
    } finally {
      setCreatingPr(false)
    }
  }

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary-500/30 bg-primary-500/10">
            <GitPullRequest size={19} className="text-primary-600 dark:text-primary-300" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">Repository CI/CD Setup</h1>
            <p className="text-xs text-ink-subtle">Scan a GitHub repository and open a workflow setup pull request</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
        <div className="mx-auto max-w-5xl space-y-5">
          <section className="card p-5">
            <label htmlFor="repo-full-name" className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-subtle">
              Repository
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                id="repo-full-name"
                value={repoFullName}
                onChange={(event) => setRepoFullName(event.target.value)}
                className="input-field flex-1"
                placeholder="owner/repo"
              />
              <button
                type="button"
                onClick={scanRepository}
                disabled={!normalizedRepo || scanning}
                className="btn-primary inline-flex items-center justify-center gap-2"
              >
                {scanning ? <Loader2 size={15} className="animate-spin" /> : <Radar size={15} />}
                Scan Repository
              </button>
            </div>
            {error && (
              <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200">
                {error}
              </div>
            )}
          </section>

          {scanResult && (
            <section className="card p-5">
              <StackPanel result={scanResult} />
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={createWorkflowPr}
                  disabled={!normalizedRepo || creatingPr}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  {creatingPr ? <Loader2 size={15} className="animate-spin" /> : <GitPullRequest size={15} />}
                  Create Workflow PR
                </button>
                <span className="text-xs text-ink-subtle">Creates a branch and opens a pull request. It does not push to main.</span>
              </div>
            </section>
          )}

          {prResult && (
            <section className="card p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-ink-subtle">Pull Request Created</p>
                  <h2 className="mt-2 text-base font-semibold text-ink">{prResult.repo_full_name}</h2>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="badge-success">{prResult.workflow_path}</span>
                    <span className="badge-info inline-flex items-center gap-1">
                      <GitBranch size={12} /> {prResult.branch}
                    </span>
                  </div>
                </div>
                <a
                  href={prResult.pull_request_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary inline-flex items-center gap-2"
                >
                  Open PR <ExternalLink size={15} />
                </a>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
