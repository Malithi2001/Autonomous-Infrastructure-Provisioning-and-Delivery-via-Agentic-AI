import type { UserRole } from '@/types'

export interface RoleDefinition {
  role: UserRole
  label: string
  description: string
  headline: string
  permissions: readonly string[]
  badgeClass: string
  accentClass: string
}

export const ROLE_ORDER: UserRole[] = ['admin', 'operator', 'developer', 'viewer']

export const ROLE_DEFINITIONS: Record<UserRole, RoleDefinition> = {
  admin: {
    role: 'admin',
    label: 'Admin',
    description: 'Full platform owner with user management, audit, approval, and infrastructure permissions.',
    headline: 'Full control plane access',
    permissions: ['*'],
    badgeClass: 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-200',
    accentClass: 'text-rose-600 dark:text-rose-300',
  },
  operator: {
    role: 'operator',
    label: 'Operator',
    description: 'Operations controller for production-safe tools, approval gates, logs, metrics, and executions.',
    headline: 'Production operations and approvals',
    permissions: [
      'agent:chat',
      'logs:read',
      'logs:write',
      'metrics:read',
      'executions:read',
      'executions:write',
      'approvals:read',
      'approvals:decide',
      'deployments:staging',
      'deployments:production',
      'infrastructure:read',
      'infrastructure:write',
    ],
    badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-200',
    accentClass: 'text-amber-600 dark:text-amber-300',
  },
  developer: {
    role: 'developer',
    label: 'Developer',
    description: 'Builder workflow for agent chat, diagnostics, metrics, logs, executions, and staging deployment tasks.',
    headline: 'Diagnostics and staging workflow',
    permissions: ['agent:chat', 'logs:read', 'metrics:read', 'executions:read', 'deployments:staging'],
    badgeClass: 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-200',
    accentClass: 'text-sky-600 dark:text-sky-300',
  },
  viewer: {
    role: 'viewer',
    label: 'Viewer',
    description: 'Read-only observer for operational insight, logs, metrics, approvals, and execution history.',
    headline: 'Read-only operational insight',
    permissions: ['agent:chat', 'approvals:read', 'logs:read', 'metrics:read', 'executions:read'],
    badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200',
    accentClass: 'text-emerald-600 dark:text-emerald-300',
  },
}

export const DEMO_CREDENTIALS: Record<UserRole, { email: string; password: string; note: string }> = {
  admin: {
    email: 'admin@example.com',
    password: 'admin123',
    note: 'Manage users, roles, and all agent workflows.',
  },
  operator: {
    email: 'operator@devops.example.com',
    password: 'operator123',
    note: 'Approve high-risk actions and operate production workflows.',
  },
  developer: {
    email: 'devops.engineer@example.com',
    password: 'developer123',
    note: 'Inspect systems and run safe development workflows.',
  },
  viewer: {
    email: 'viewer@company.example.com',
    password: 'viewer123',
    note: 'View read-only operational insight and history.',
  },
}

export const CHAT_SUGGESTIONS: Record<UserRole, string[]> = {
  admin: [
    'Show pending approvals and recent failed executions.',
    'Summarize infrastructure risks from the latest activity.',
    'Create an operator checklist for today.',
  ],
  operator: [
    'Show production deployment risks before approval.',
    'Summarize failed executions from the last day.',
    'Check service health and suggest next actions.',
  ],
  developer: [
    'Diagnose the latest CI failure logs.',
    'Suggest a staging deployment plan.',
    'Explain recent execution failures.',
  ],
  viewer: [
    'Summarize current system health.',
    'Show recent execution history.',
    'Explain the latest CI failure in plain language.',
  ],
}

export function normalizeRole(role?: string | null): UserRole {
  const value = String(role || '').toLowerCase()
  return ROLE_ORDER.includes(value as UserRole) ? (value as UserRole) : 'viewer'
}

export function getRoleDefinition(role?: string | null): RoleDefinition {
  return ROLE_DEFINITIONS[normalizeRole(role)]
}

export function hasPermission(role: string | null | undefined, permission: string): boolean {
  const permissions = getRoleDefinition(role).permissions
  return permissions.includes('*') || permissions.includes(permission)
}

export function defaultPathForRole(role?: string | null): string {
  return normalizeRole(role) === 'admin' ? '/users' : '/chat'
}

export function canAccessPath(role: string | null | undefined, path: string): boolean {
  if (path.startsWith('/users')) return hasPermission(role, 'users:manage')
  if (path.startsWith('/diagnosis')) return hasPermission(role, 'logs:read')
  if (path.startsWith('/repository-setup')) return hasPermission(role, 'executions:write')
  if (path.startsWith('/workflow-failures')) return hasPermission(role, 'executions:read')
  if (path.startsWith('/approvals')) return hasPermission(role, 'approvals:read')
  if (path.startsWith('/executions')) return hasPermission(role, 'executions:read')
  if (path.startsWith('/chat') || path === '/') return hasPermission(role, 'agent:chat')
  return false
}
