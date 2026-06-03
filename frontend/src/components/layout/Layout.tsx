import { Outlet, NavLink, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Bot,
  CheckSquare,
  Clock,
  Gauge,
  GitPullRequest,
  LogOut,
  Network,
  SearchCode,
  Settings,
  Shield,
  Terminal,
  TriangleAlert,
  UsersRound,
  WifiOff,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { IS_AUTH_DISABLED, IS_MOBILE_MODE } from "@/config/runtime";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { getRoleDefinition, hasPermission } from "@/lib/rbac";
import clsx from "clsx";
import { useEffect, useState } from "react";

type NavItem = {
  to: string;
  icon: typeof Bot;
  label: string;
  permission: string;
  webOnly?: boolean;
};

const navItems: NavItem[] = [
  {
    to: "/dashboard",
    icon: Gauge,
    label: "Dashboard",
    permission: "agent:chat" as const,
  },
  {
    to: "/chat",
    icon: Terminal,
    label: "Agent Chat",
    permission: "agent:chat" as const,
  },
  {
    to: "/multi-agent",
    icon: Network,
    label: "Multi-Agent",
    permission: "agents:orchestrate" as const,
  },
  {
    to: "/diagnosis",
    icon: SearchCode,
    label: "CI/CD Assistant",
    permission: "cicd:generate" as const,
  },
  {
    to: "/repository-setup",
    icon: GitPullRequest,
    label: "Repository Setup",
    permission: "repositories:write" as const,
  },
  {
    to: "/workflow-failures",
    icon: TriangleAlert,
    label: "Workflow Failures",
    permission: "workflow_failures:read" as const,
  },
  {
    to: "/approvals",
    icon: CheckSquare,
    label: "Approvals",
    permission: "approvals:read" as const,
  },
  {
    to: "/executions",
    icon: Clock,
    label: "Audit",
    permission: "executions:read" as const,
  },
  {
    to: "/evaluation",
    icon: BarChart3,
    label: "Evaluation",
    permission: "metrics:read" as const,
  },
  {
    to: "/users",
    icon: UsersRound,
    label: "Users & Roles",
    permission: "users:manage" as const,
    webOnly: true,
  },
  {
    to: "/settings",
    icon: Settings,
    label: "Settings",
    permission: "agent:chat" as const,
  },
];

function RoleBadge({ role }: { role?: string }) {
  const definition = getRoleDefinition(role);
  return (
    <span
      className={clsx(
        "rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]",
        definition.badgeClass,
      )}
    >
      {definition.label}
    </span>
  );
}

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const role = getRoleDefinition(user?.role);
  const [isOnline, setIsOnline] = useState(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  const visibleNavItems = navItems.filter(
    (item) =>
      !((IS_AUTH_DISABLED || IS_MOBILE_MODE) && item.webOnly) &&
      (IS_AUTH_DISABLED || hasPermission(user?.role, item.permission)),
  );

  useEffect(() => {
    const updateOnlineStatus = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    return () => {
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell flex min-w-0 overflow-hidden app-bg">
      {!IS_MOBILE_MODE && (
        <aside className="hidden w-64 shrink-0 flex-col border-r border-surface-600/80 bg-surface-800/95 shadow-panel lg:flex xl:w-72">
          <div className="border-b border-surface-600/80 px-5 py-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary-500/30 bg-primary-500/10 shadow-glow">
                <Bot
                  size={21}
                  className="text-primary-500 dark:text-primary-300"
                />
              </div>
              <div>
                <p className="text-sm font-semibold leading-tight text-ink">
                  DevOps
                </p>
                <p className="text-xs leading-tight text-primary-700 dark:text-primary-300">
                  Assistant
                </p>
              </div>
            </div>
            <div className="mt-4 rounded-2xl border border-surface-600 bg-surface-900/70 p-3">
              <div className="flex items-center justify-between gap-3">
                <RoleBadge role={user?.role} />
                <Shield size={15} className={role.accentClass} />
              </div>
              <p className="mt-2 text-xs leading-5 text-ink-subtle">
                {role.headline}
              </p>
            </div>
          </div>

          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {visibleNavItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "border border-primary-500/30 bg-primary-500/10 text-primary-700 shadow-sm dark:text-primary-200"
                      : "text-ink-muted hover:bg-surface-700/80 hover:text-ink",
                  )
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-surface-600/80 px-3 py-4">
            <div className="mb-3">
              <ThemeToggle />
            </div>
            <div className="mb-2 flex items-center gap-2 rounded-xl bg-surface-900/70 px-3 py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full border border-surface-500 bg-surface-700">
                <Shield
                  size={14}
                  className="text-primary-500 dark:text-primary-300"
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-ink">{user?.username}</p>
                {IS_AUTH_DISABLED && (
                  <p className="truncate text-xs text-primary-700 dark:text-primary-300">
                    Local auth disabled
                  </p>
                )}
                {!IS_AUTH_DISABLED && (
                  <p className="truncate text-xs text-ink-subtle">
                    {user?.email}
                  </p>
                )}
              </div>
            </div>
            {!IS_AUTH_DISABLED && (
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-surface-700 hover:text-red-500 dark:hover:text-red-300"
              >
                <LogOut size={14} />
                Sign out
              </button>
            )}
          </div>
        </aside>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <div
          className={clsx(
            "mobile-top-bar flex items-center justify-between gap-3 border-b border-surface-600 bg-surface-800/95 px-4 py-3",
            !IS_MOBILE_MODE && "lg:hidden",
          )}
        >
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600/15 text-primary-600 dark:text-primary-300">
              <Bot size={18} />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">
                DevOps Assistant
              </p>
              <div className="mt-1">
                <RoleBadge role={user?.role} />
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <ThemeToggle compact />
            {!IS_AUTH_DISABLED && (
              <button
                onClick={handleLogout}
                className="rounded-xl border border-surface-600 bg-surface-800 p-2 text-ink-muted hover:bg-surface-700 hover:text-red-500"
              >
                <LogOut size={17} />
              </button>
            )}
          </div>
        </div>

        {!isOnline && (
          <div className="flex items-center gap-2 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs font-medium text-amber-800 dark:text-amber-100">
            <WifiOff size={14} className="shrink-0" />
            <span>
              Offline. Backend, GitHub, model, approval, and audit actions need
              a network connection.
            </span>
          </div>
        )}

        {!IS_MOBILE_MODE && (
          <div className="flex gap-2 overflow-x-auto border-b border-surface-600 bg-surface-800/90 px-3 py-2 lg:hidden">
            {visibleNavItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition",
                    isActive
                      ? "border-primary-500/30 bg-primary-500/10 text-primary-700 dark:text-primary-200"
                      : "border-surface-600 text-ink-muted",
                  )
                }
              >
                <Icon size={14} /> {label}
              </NavLink>
            ))}
          </div>
        )}

        <main
          className={clsx(
            "min-h-0 flex-1 overflow-hidden",
            IS_MOBILE_MODE && "mobile-content",
          )}
        >
          <Outlet />
        </main>
        {IS_MOBILE_MODE && (
          <nav className="mobile-bottom-nav fixed inset-x-0 bottom-0 z-40 flex gap-2 overflow-x-auto border-t border-surface-600 bg-surface-800/95 px-3 py-2 shadow-panel">
            {visibleNavItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "flex min-h-14 min-w-20 shrink-0 flex-col items-center justify-center gap-1 rounded-xl border px-3 text-[11px] font-semibold leading-tight transition",
                    isActive
                      ? "border-primary-500/30 bg-primary-500/10 text-primary-700 dark:text-primary-200"
                      : "border-surface-600 text-ink-muted",
                  )
                }
              >
                <Icon size={17} />
                <span className="max-w-20 truncate">{label}</span>
              </NavLink>
            ))}
          </nav>
        )}
      </div>
    </div>
  );
}
