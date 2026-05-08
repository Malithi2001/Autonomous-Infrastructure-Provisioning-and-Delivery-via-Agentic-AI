import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '@/store/themeStore'

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { resolvedTheme, toggleTheme } = useThemeStore()
  const isDark = resolvedTheme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex items-center gap-2 rounded-xl border border-surface-600 bg-surface-800 px-3 py-2 text-sm font-medium text-ink-muted shadow-sm transition hover:border-primary-500/50 hover:bg-surface-700 hover:text-ink"
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {isDark ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} className="text-blue-600" />}
      {!compact && <span>{isDark ? 'Light' : 'Dark'}</span>}
    </button>
  )
}
