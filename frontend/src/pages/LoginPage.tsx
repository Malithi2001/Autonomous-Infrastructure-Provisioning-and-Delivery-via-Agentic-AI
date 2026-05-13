import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Bot, Eye, EyeOff, KeyRound, LockKeyhole, Mail, ServerCog, ShieldCheck, Sparkles, UserRound, UsersRound } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuthStore } from '@/store/authStore'
import { DEMO_CREDENTIALS, ROLE_DEFINITIONS, ROLE_ORDER, defaultPathForRole } from '@/lib/rbac'
import type { UserRole } from '@/types'
import clsx from 'clsx'

const SIGNUP_ROLES: Extract<UserRole, 'developer' | 'viewer'>[] = ['developer', 'viewer']

function isValidEmail(value: string) {
  return /^\S+@\S+\.\S+$/.test(value)
}

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, signup, user, isAuthenticated, isLoading } = useAuthStore()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [selectedLoginRole, setSelectedLoginRole] = useState<UserRole>('admin')
  const [signupRole, setSignupRole] = useState<Extract<UserRole, 'developer' | 'viewer'>>('developer')
  const [email, setEmail] = useState(DEMO_CREDENTIALS.admin.email)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState(DEMO_CREDENTIALS.admin.password)
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const redirectTo = useMemo(() => {
    const state = location.state as { from?: { pathname?: string } } | null
    return state?.from?.pathname || defaultPathForRole(user?.role)
  }, [location.state, user?.role])

  useEffect(() => {
    if (isAuthenticated) navigate(defaultPathForRole(user?.role), { replace: true })
  }, [isAuthenticated, navigate, user?.role])

  useEffect(() => {
    setError('')
    setShowPassword(false)
    if (mode === 'login') {
      const demo = DEMO_CREDENTIALS[selectedLoginRole]
      setEmail(demo.email)
      setPassword(demo.password)
      setUsername('')
      setConfirmPassword('')
    } else {
      setEmail('')
      setPassword('')
      setUsername('')
      setConfirmPassword('')
    }
  }, [mode, selectedLoginRole])

  if (isAuthenticated) return <Navigate to={redirectTo} replace />

  const validate = () => {
    if (!email.trim()) return 'Email is required.'
    if (!isValidEmail(email.trim())) return 'Enter a valid email address.'
    if (mode === 'signup' && username.trim().length < 3) return 'Username must be at least 3 characters.'
    if (!password) return 'Password is required.'
    if (password.length < (mode === 'signup' ? 8 : 6)) return `Password must be at least ${mode === 'signup' ? 8 : 6} characters.`
    if (mode === 'signup' && password !== confirmPassword) return 'Passwords do not match.'
    return ''
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }
    setSubmitting(true)
    setError('')
    try {
      if (mode === 'signup') {
        await signup(email.trim(), username.trim(), password, signupRole)
      } else {
        await login(email.trim(), password)
      }
      const currentRole = useAuthStore.getState().user?.role
      navigate(defaultPathForRole(currentRole), { replace: true })
    } catch (err: any) {
      setError(err.response?.data?.detail || `${mode === 'signup' ? 'Sign up' : 'Login'} failed. Please try again.`)
    } finally {
      setSubmitting(false)
    }
  }

  const disabled = submitting || isLoading

  return (
    <div className="relative min-h-screen overflow-hidden app-bg">
      <div className="pointer-events-none absolute inset-0 app-gradient" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary-400/60 to-transparent" />
      <div className="absolute right-4 top-4 z-20 sm:right-6 sm:top-6"><ThemeToggle /></div>

      <main className="relative grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden flex-col justify-between border-r border-surface-600/70 p-10 lg:flex">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary-500/30 bg-primary-500/10 shadow-glow">
              <Bot size={23} className="text-primary-500 dark:text-primary-300" />
            </div>
            <div>
              <p className="font-semibold text-ink">Smart DevOps Assistant</p>
              <p className="text-xs text-ink-subtle">Role-governed infrastructure delivery</p>
            </div>
          </div>

          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary-500/25 bg-primary-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.26em] text-primary-700 dark:text-primary-300">
              <Sparkles size={13} /> RBAC Control Plane
            </div>
            <h1 className="text-4xl font-semibold leading-tight text-ink xl:text-5xl">
              One AI DevOps workspace, four safe access levels.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-ink-muted">
              Admins provision accounts, operators approve high-risk actions, developers build safely, and viewers get read-only operational insight.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm xl:grid-cols-4">
            {ROLE_ORDER.map((role) => {
              const definition = ROLE_DEFINITIONS[role]
              return (
                <div key={role} className="rounded-2xl border border-surface-600 bg-surface-800/70 p-4 shadow-panel">
                  <UsersRound size={18} className={`mb-3 ${definition.accentClass}`} />
                  <p className="font-semibold text-ink">{definition.label}</p>
                  <p className="mt-1 text-xs leading-5 text-ink-subtle">{definition.headline}</p>
                </div>
              )
            })}
          </div>
        </section>

        <section className="flex items-center justify-center px-4 py-16 sm:px-6 lg:px-10">
          <div className="w-full max-w-lg">
            <div className="mb-8 text-center lg:hidden">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-3xl border border-primary-500/30 bg-primary-500/10">
                <Bot size={28} className="text-primary-500 dark:text-primary-300" />
              </div>
              <h1 className="text-xl font-semibold text-ink">Smart DevOps Assistant</h1>
              <p className="mt-1 text-sm text-ink-subtle">Role-governed infrastructure control plane</p>
            </div>

            <div className="glass-panel p-6 sm:p-8">
              <div className="mb-7">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary-700 dark:text-primary-300">{mode === 'signup' ? 'Request safe access' : 'Welcome back'}</p>
                <h2 className="mt-3 text-2xl font-semibold text-ink">{mode === 'signup' ? 'Create a role-limited account' : 'Sign in to your role workspace'}</h2>
                <p className="mt-2 text-sm text-ink-subtle">
                  {mode === 'signup'
                    ? 'Public signup is limited to Developer and Viewer roles. Admins can provision Operator/Admin users later.'
                    : 'Choose a demo role to fill credentials, or enter your own email and password.'}
                </p>
              </div>

              <div className="mb-6 grid grid-cols-2 rounded-2xl border border-surface-600 bg-surface-900/70 p-1">
                <button type="button" onClick={() => setMode('login')} className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${mode === 'login' ? 'bg-surface-800 text-ink shadow-panel' : 'text-ink-muted hover:text-ink'}`}>
                  Sign in
                </button>
                <button type="button" onClick={() => setMode('signup')} className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${mode === 'signup' ? 'bg-surface-800 text-ink shadow-panel' : 'text-ink-muted hover:text-ink'}`}>
                  Sign up
                </button>
              </div>

              {mode === 'login' && (
                <div className="mb-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {ROLE_ORDER.map((role) => {
                    const definition = ROLE_DEFINITIONS[role]
                    const credentials = DEMO_CREDENTIALS[role]
                    const active = selectedLoginRole === role
                    return (
                      <button
                        key={role}
                        type="button"
                        onClick={() => setSelectedLoginRole(role)}
                        className={clsx(
                          'rounded-2xl border p-3 text-left transition hover:-translate-y-0.5 hover:shadow-panel',
                          active ? `${definition.badgeClass} shadow-panel` : 'border-surface-600 bg-surface-900/60 text-ink-muted hover:bg-surface-800',
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold">{definition.label}</span>
                          <KeyRound size={14} className={definition.accentClass} />
                        </div>
                        <p className="mt-1 text-xs leading-5 opacity-80">{credentials.note}</p>
                      </button>
                    )
                  })}
                </div>
              )}

              {mode === 'signup' && (
                <div className="mb-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {SIGNUP_ROLES.map((role) => {
                    const definition = ROLE_DEFINITIONS[role]
                    const active = signupRole === role
                    return (
                      <button
                        key={role}
                        type="button"
                        onClick={() => setSignupRole(role)}
                        className={clsx(
                          'rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-panel',
                          active ? `${definition.badgeClass} shadow-panel` : 'border-surface-600 bg-surface-900/60 text-ink-muted hover:bg-surface-800',
                        )}
                      >
                        <p className="text-sm font-semibold">{definition.label}</p>
                        <p className="mt-1 text-xs leading-5 opacity-80">{definition.description}</p>
                      </button>
                    )
                  })}
                </div>
              )}

              {error && <div className="mb-5 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200">{error}</div>}

              <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                {mode === 'signup' && (
                  <div>
                    <label htmlFor="username" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Username</label>
                    <div className="relative">
                      <UserRound size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle" />
                      <input id="username" type="text" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="devops.engineer" autoComplete="username" className="input-field py-3 pl-10 pr-4" />
                    </div>
                  </div>
                )}

                <div>
                  <label htmlFor="email" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Email address</label>
                  <div className="relative">
                    <Mail size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle" />
                    <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="admin@example.com" autoComplete="email" className="input-field py-3 pl-10 pr-4" />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Password</label>
                  <div className="relative">
                    <LockKeyhole size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle" />
                    <input id="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} className="input-field py-3 pl-10 pr-12" />
                    <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-ink-subtle transition hover:bg-surface-700 hover:text-ink" aria-label={showPassword ? 'Hide password' : 'Show password'}>
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                {mode === 'signup' && (
                  <div>
                    <label htmlFor="confirm-password" className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Confirm password</label>
                    <div className="relative">
                      <LockKeyhole size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle" />
                      <input id="confirm-password" type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="••••••••" autoComplete="new-password" className="input-field py-3 pl-10 pr-4" />
                    </div>
                  </div>
                )}

                <button type="submit" disabled={disabled} className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary-600 px-4 py-3 text-sm font-semibold text-white shadow-glow transition hover:bg-primary-500 disabled:cursor-not-allowed disabled:bg-surface-600 disabled:text-ink-faint disabled:shadow-none">
                  {submitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : mode === 'signup' ? <UserRound size={16} /> : <ShieldCheck size={16} />}
                  {submitting ? (mode === 'signup' ? 'Creating account…' : 'Signing in…') : (mode === 'signup' ? `Create ${ROLE_DEFINITIONS[signupRole].label} account` : `Sign in as ${ROLE_DEFINITIONS[selectedLoginRole].label}`)}
                </button>
              </form>

              <div className="mt-5 rounded-2xl border border-surface-600 bg-surface-900/50 px-4 py-3 text-xs leading-5 text-ink-subtle">
                <ServerCog size={14} className="mr-2 inline text-primary-600 dark:text-primary-300" />
                Admin and Operator signup is disabled for safety. Sign in with seeded accounts or create privileged users from the Admin workspace.
              </div>
            </div>

            <p className="mt-6 text-center text-xs text-ink-faint">Horizon Campus · Faculty of Information Technology</p>
          </div>
        </section>
      </main>
    </div>
  )
}
