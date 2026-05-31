import { FormEvent, useEffect, useMemo, useState } from 'react'
import { CheckCircle, Eye, EyeOff, Plus, ShieldCheck, UserCog, UsersRound } from 'lucide-react'
import { authService } from '@/services/api'
import type { User, UserRole } from '@/types'
import { ROLE_DEFINITIONS, ROLE_ORDER } from '@/lib/rbac'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

interface FormState {
  email: string
  username: string
  password: string
  role: UserRole
}

const initialForm: FormState = {
  email: '',
  username: '',
  password: '',
  role: 'developer',
}

function relativeTime(value?: string) {
  if (!value) return 'time unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'time unknown'
  return formatDistanceToNow(date, { addSuffix: true })
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [form, setForm] = useState<FormState>(initialForm)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const usersByRole = useMemo(() => {
    return ROLE_ORDER.reduce<Record<UserRole, number>>((acc, role) => {
      acc[role] = users.filter((user) => user.role === role).length
      return acc
    }, { admin: 0, operator: 0, developer: 0, viewer: 0 })
  }, [users])

  const fetchUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await authService.listUsers()
      setUsers(data)
    } catch (err: any) {
      setUsers([])
      const status = err.response?.status
      if (status === 401) {
        setError('Please sign in again before managing users.')
      } else if (status === 403) {
        setError('Admin access is required to manage users.')
      } else {
        setError(err.response?.data?.detail || 'Could not load users. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  const updateForm = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const validate = () => {
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) return 'Enter a valid email address.'
    if (form.username.trim().length < 3) return 'Username must be at least 3 characters.'
    if (form.password.length < 8) return 'Password must be at least 8 characters.'
    return ''
  }

  const handleCreateUser = async (event: FormEvent) => {
    event.preventDefault()
    const validation = validate()
    if (validation) {
      setError(validation)
      setSuccess('')
      return
    }

    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      const created = await authService.createUser({
        email: form.email.trim(),
        username: form.username.trim(),
        password: form.password,
        role: form.role,
      })
      setUsers((current) => [created, ...current])
      setSuccess(`${ROLE_DEFINITIONS[form.role].label} user ${created.username} was created.`)
      setForm(initialForm)
      setShowPassword(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not create user. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex h-full flex-col bg-surface-900">
      <div className="shrink-0 border-b border-surface-600 bg-surface-900/90 px-6 py-4 backdrop-blur">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/10">
              <UsersRound size={19} className="text-violet-600 dark:text-violet-300" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-ink">Users & Role Access</h1>
              <p className="text-xs text-ink-subtle">Admin-only provisioning for safe role-based AI DevOps access</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {ROLE_ORDER.map((role) => (
              <div key={role} className={clsx('rounded-2xl border px-3 py-2 text-xs', ROLE_DEFINITIONS[role].badgeClass)}>
                <p className="font-semibold">{ROLE_DEFINITIONS[role].label}</p>
                <p className="mt-0.5 opacity-80">{usersByRole[role]} account{usersByRole[role] === 1 ? '' : 's'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 overflow-y-auto px-6 py-6 xl:grid-cols-[420px_1fr]">
        <form onSubmit={handleCreateUser} className="card h-fit p-5" noValidate>
          <div className="mb-5 flex items-start gap-3">
            <div className="rounded-2xl border border-primary-500/30 bg-primary-500/10 p-2 text-primary-600 dark:text-primary-300">
              <UserCog size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-ink">Provision a user</h2>
              <p className="mt-1 text-xs leading-5 text-ink-subtle">Use this for Admin and Operator accounts. Public signup remains limited to Developer and Viewer.</p>
            </div>
          </div>

          {error && <div className="mb-4 rounded-2xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200">{error}</div>}
          {success && <div className="mb-4 flex items-center gap-2 rounded-2xl border border-primary-500/30 bg-primary-500/10 px-4 py-3 text-sm text-primary-700 dark:text-primary-200"><CheckCircle size={16} />{success}</div>}

          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Role</label>
              <div className="grid grid-cols-2 gap-2">
                {ROLE_ORDER.map((role) => {
                  const active = form.role === role
                  return (
                    <button
                      key={role}
                      type="button"
                      onClick={() => updateForm('role', role)}
                      className={clsx(
                        'rounded-2xl border p-3 text-left text-xs transition hover:-translate-y-0.5 hover:shadow-panel',
                        active ? ROLE_DEFINITIONS[role].badgeClass : 'border-surface-600 bg-surface-900/60 text-ink-muted hover:bg-surface-800',
                      )}
                    >
                      <p className="font-semibold">{ROLE_DEFINITIONS[role].label}</p>
                      <p className="mt-1 leading-4 opacity-80">{ROLE_DEFINITIONS[role].headline}</p>
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Email</label>
              <input value={form.email} onChange={(event) => updateForm('email', event.target.value)} type="email" placeholder="operator@devops.example.com" className="input-field px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Username</label>
              <input value={form.username} onChange={(event) => updateForm('username', event.target.value)} type="text" placeholder="operator" className="input-field px-4 py-3" />
            </div>
            <div>
              <label className="mb-2 block text-xs font-medium uppercase tracking-[0.16em] text-ink-subtle">Temporary password</label>
              <div className="relative">
                <input value={form.password} onChange={(event) => updateForm('password', event.target.value)} type={showPassword ? 'text' : 'password'} placeholder="minimum 8 characters" className="input-field px-4 py-3 pr-12" />
                <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-ink-subtle transition hover:bg-surface-700 hover:text-ink">
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>
          </div>

          <button type="submit" disabled={submitting} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary-600 px-4 py-3 text-sm font-semibold text-white shadow-glow transition hover:bg-primary-500 disabled:cursor-not-allowed disabled:bg-surface-600 disabled:text-ink-faint disabled:shadow-none">
            {submitting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : <Plus size={16} />}
            {submitting ? 'Creating user…' : 'Create user'}
          </button>
        </form>

        <div className="min-w-0">
          {loading ? (
            <div className="flex h-32 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" /></div>
          ) : users.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-4 rounded-3xl border border-surface-600 bg-surface-800 p-4"><UsersRound size={40} className="text-ink-subtle" /></div>
              <p className="font-medium text-ink">No users found</p>
              <p className="mt-1 text-sm text-ink-subtle">Create your first RBAC user from the form.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {users.map((user) => {
                const role = ROLE_DEFINITIONS[user.role]
                return (
                  <div key={user.id} className="card flex flex-col gap-4 px-4 py-4 transition-colors hover:border-primary-500/30 sm:flex-row sm:items-center">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-surface-600 bg-surface-800 text-ink-muted">
                      <ShieldCheck size={18} className={role.accentClass} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-ink">{user.username}</p>
                      <p className="truncate text-xs text-ink-subtle">{user.email}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                      <span className={clsx('rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]', role.badgeClass)}>{role.label}</span>
                      <span className="rounded-full border border-surface-600 px-2.5 py-1 text-[11px] text-ink-subtle">created {relativeTime(user.created_at)}</span>
                      {!user.is_active && <span className="badge-error">inactive</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
