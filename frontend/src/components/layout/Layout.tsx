import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  Bot, CheckSquare, Clock, LogOut, Terminal, Shield
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import clsx from 'clsx'
import { canAccessChat } from '@/lib/rbac'

const navItems = [
  { to: '/chat',       icon: Terminal,    label: 'Agent Chat' },
  { to: '/approvals',  icon: CheckSquare, label: 'Approvals' },
  { to: '/executions', icon: Clock,       label: 'Executions' },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const visibleNavItems = navItems.filter((item) => {
    if (item.to === '/chat') {
      return canAccessChat(user?.role)
    }
    return true
  })

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-surface-800 border-r border-surface-600 flex flex-col shrink-0">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-surface-600">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Bot size={18} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white leading-tight">DevOps</p>
              <p className="text-xs text-primary-400 leading-tight">Assistant</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {visibleNavItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-600/20 text-primary-300 border border-primary-600/30'
                    : 'text-gray-400 hover:text-white hover:bg-surface-700'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="px-3 py-4 border-t border-surface-600">
          <div className="flex items-center gap-2 px-3 py-2 mb-2">
            <div className="w-7 h-7 bg-surface-600 rounded-full flex items-center justify-center">
              <Shield size={13} className="text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{user?.username}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-red-400 hover:bg-surface-700 rounded-lg transition-colors"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <Outlet />
      </main>
    </div>
  )
}
