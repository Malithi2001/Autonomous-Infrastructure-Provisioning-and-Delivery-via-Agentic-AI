import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, Eye, EyeOff } from 'lucide-react'
import { authService } from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import { getDefaultRouteForRole } from '@/lib/rbac'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!username || !password) return
    setLoading(true)
    setError('')
    try {
      const data = await authService.login(username, password)
      login(data.access_token, { id: data.user_id, username: data.username, role: data.role })
      navigate(getDefaultRouteForRole(data.role))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div className="min-h-screen bg-surface-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-primary-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-primary-900/40">
            <Bot size={28} className="text-white" />
          </div>
          <h1 className="text-xl font-semibold text-white">Smart DevOps Assistant</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to your account</p>
        </div>

        {/* Form */}
        <div className="card p-6 space-y-4">
          {error && (
            <div className="bg-red-900/30 border border-red-700/50 text-red-300 text-sm px-3 py-2.5 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="your_username"
              className="w-full bg-surface-700 border border-surface-500 focus:border-primary-500 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Password</label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="••••••••"
                className="w-full bg-surface-700 border border-surface-500 focus:border-primary-500 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-colors pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPw(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading || !username || !password}
            className="btn-primary w-full mt-2 flex items-center justify-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : 'Sign In'}
          </button>
        </div>

        <p className="text-center text-xs text-gray-600 mt-6">
          Horizon Campus · Faculty of Information Technology
        </p>
      </div>
    </div>
  )
}
