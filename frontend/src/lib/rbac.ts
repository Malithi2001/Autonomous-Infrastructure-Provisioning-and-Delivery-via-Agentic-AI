import type { UserRole } from "@/types";

export interface RoleDefinition {
  role: UserRole;
  label: string;
  description: string;
  headline: string;
  permissions: readonly string[];
  badgeClass: string;
  accentClass: string;
}

export const ROLE_ORDER: UserRole[] = [
  "admin",
  "operator",
  "developer",
  "viewer",
];

export const ROLE_DEFINITIONS: Record<UserRole, RoleDefinition> = {
  admin: {
    role: "admin",
    label: "Admin",
    description:
      "Full platform owner with user management, audit, approval, and infrastructure permissions.",
    headline: "Full control plane access",
    permissions: ["*"],
    badgeClass:
      "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-200",
    accentClass: "text-rose-600 dark:text-rose-300",
  },
  operator: {
    role: "operator",
    label: "Operator",
    description:
      "Operations controller for production-safe tools, approval gates, logs, metrics, and executions.",
    headline: "Production operations and approvals",
    permissions: [
      "agent:chat",
      "agents:orchestrate",
      "cicd:read",
      "cicd:generate",
      "failures:predict",
      "repositories:read",
      "repositories:write",
      "workflow_failures:read",
      "workflow_failures:write",
      "audit:read",
      "logs:read",
      "logs:write",
      "metrics:read",
      "executions:read",
      "executions:write",
      "approvals:read",
      "approvals:decide",
      "deployments:staging",
      "deployments:production",
      "infrastructure:read",
      "infrastructure:write",
    ],
    badgeClass:
      "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-200",
    accentClass: "text-amber-600 dark:text-amber-300",
  },
  developer: {
    role: "developer",
    label: "Developer",
    description:
      "Build CI/CD workflows, propose workflow pull requests, review your own approvals, and use development/staging tools.",
    headline: "CI/CD and personal approvals",
    permissions: [
      "agent:chat",
      "approvals:read",
      "approvals:decide:own",
      "agents:orchestrate",
      "cicd:read",
      "cicd:generate",
      "failures:predict",
      "repositories:read",
      "repositories:write",
      "workflow_failures:read",
      "executions:read",
      "logs:read",
      "deployments:staging",
    ],
    badgeClass:
      "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-200",
    accentClass: "text-sky-600 dark:text-sky-300",
  },
  viewer: {
    role: "viewer",
    label: "Viewer",
    description:
      "Read-only observer for safe AI chat, personal activity, and the status of their own approval requests.",
    headline: "Read-only operational insight",
    permissions: ["agent:chat", "approvals:read", "executions:read"],
    badgeClass:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200",
    accentClass: "text-emerald-600 dark:text-emerald-300",
  },
};

export const DEMO_CREDENTIALS: Record<
  UserRole,
  { email: string; password: string; note: string }
> = {
  admin: {
    email: "admin@example.com",
    password: "admin123",
    note: "Manage users, roles, and all agent workflows.",
  },
  operator: {
    email: "operator@devops.example.com",
    password: "operator123",
    note: "Approve high-risk actions and operate production workflows.",
  },
  developer: {
    email: "devops.engineer@example.com",
    password: "developer123",
    note: "Build CI/CD workflows and review your own approval requests.",
  },
  viewer: {
    email: "viewer@company.example.com",
    password: "viewer123",
    note: "Use safe AI chat without operational control-plane access.",
  },
};

export const CHAT_SUGGESTIONS: Record<UserRole, string[]> = {
  admin: [
    "Show pending approvals and recent failed executions.",
    "Summarize infrastructure risks from the latest activity.",
    "Create an operator checklist for today.",
  ],
  operator: [
    "Show production deployment risks before approval.",
    "Summarize failed executions from the last day.",
    "Check service health and suggest next actions.",
  ],
  developer: [
    "Diagnose the latest CI failure logs.",
    "Suggest a staging deployment plan.",
    "Explain recent execution failures.",
  ],
  viewer: [
    "Explain what this DevOps assistant can help with.",
    "Describe CI/CD failure diagnosis in plain language.",
    "Summarize safe DevOps best practices.",
  ],
};

export function normalizeRole(role?: string | null): UserRole {
  const value = String(role || "").toLowerCase();
  return ROLE_ORDER.includes(value as UserRole)
    ? (value as UserRole)
    : "viewer";
}

export function getRoleDefinition(role?: string | null): RoleDefinition {
  return ROLE_DEFINITIONS[normalizeRole(role)];
}

export function hasPermission(
  role: string | null | undefined,
  permission: string,
): boolean {
  const permissions = getRoleDefinition(role).permissions;
  return permissions.includes("*") || permissions.includes(permission);
}

export function defaultPathForRole(role?: string | null): string {
  return role ? "/dashboard" : "/chat";
}

export function canAccessPath(
  role: string | null | undefined,
  path: string,
): boolean {
  if (path.startsWith("/dashboard") || path.startsWith("/settings")) {
    return Boolean(role);
  }
  if (path.startsWith("/users")) return hasPermission(role, "users:manage");
  if (path.startsWith("/diagnosis"))
    return (
      hasPermission(role, "failures:predict") ||
      hasPermission(role, "cicd:generate")
    );
  if (path.startsWith("/repository-setup"))
    return hasPermission(role, "repositories:write");
  if (path.startsWith("/workflow-failures"))
    return hasPermission(role, "workflow_failures:read");
  if (path.startsWith("/approvals"))
    return hasPermission(role, "approvals:read");
  if (path.startsWith("/executions"))
    return hasPermission(role, "executions:read");
  if (path.startsWith("/evaluation"))
    return hasPermission(role, "metrics:read");
  if (path.startsWith("/multi-agent"))
    return hasPermission(role, "agents:orchestrate");
  if (path.startsWith("/chat") || path === "/")
    return hasPermission(role, "agent:chat");
  return false;
}
