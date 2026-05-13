import { Bot, Container, GitBranch, HeartPulse, ServerCog, TerminalSquare } from 'lucide-react'

const icons = [Container, HeartPulse, GitBranch, ServerCog, TerminalSquare]

interface ChatEmptyStateProps {
  suggestions: string[]
  onSuggestion: (value: string) => void
  disabled?: boolean
}

export function ChatEmptyState({ suggestions, onSuggestion, disabled }: ChatEmptyStateProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4 py-10 text-center">
      <div className="relative mb-7">
        <div className="absolute inset-0 rounded-3xl bg-primary-500/20 blur-2xl" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-3xl border border-primary-500/30 bg-primary-500/10 shadow-glow">
          <Bot size={32} className="text-primary-500 dark:text-primary-300" />
        </div>
      </div>
      <div className="max-w-xl">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-primary-700 dark:text-primary-300">Agentic DevOps Console</p>
        <h2 className="text-2xl font-semibold text-ink">What infrastructure task should we tackle?</h2>
        <p className="mt-3 text-sm leading-6 text-ink-muted">Ask the assistant to inspect services, summarize CI/CD status, run safe operational checks, or prepare controlled infrastructure actions with approval gates.</p>
      </div>
      <div className="mt-8 grid w-full max-w-3xl grid-cols-1 gap-3 md:grid-cols-2">
        {suggestions.map((suggestion, index) => {
          const Icon = icons[index % icons.length]
          return (
            <button key={suggestion} onClick={() => onSuggestion(suggestion)} disabled={disabled} className="group rounded-2xl border border-surface-600 bg-surface-800/75 p-4 text-left shadow-panel transition-all hover:-translate-y-0.5 hover:border-primary-500/50 hover:bg-surface-700/80 disabled:cursor-not-allowed disabled:opacity-60">
              <div className="flex items-start gap-3">
                <div className="rounded-xl border border-surface-600 bg-surface-900 p-2 text-primary-600 transition-colors group-hover:border-primary-500/50 dark:text-primary-300"><Icon size={17} /></div>
                <span className="text-sm font-medium leading-6 text-ink">{suggestion}</span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
