import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authService = {
  login: async (username: string, password: string) => {
    const form = new FormData()
    form.append('username', username)
    form.append('password', password)
    const res = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },
}

// ── Agent ─────────────────────────────────────────────────────────────────────

export const agentService = {
  chat: async (message: string, sessionId?: string) => {
    const res = await api.post('/agent/chat', { message, session_id: sessionId })
    return res.data
  },
  clearSession: async (sessionId: string) => {
    await api.delete(`/agent/session/${sessionId}`)
  },
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export const approvalService = {
  list: async () => {
    const res = await api.get('/approvals')
    return res.data
  },
  decide: async (approvalId: string, approved: boolean, note?: string) => {
    const res = await api.post(`/approvals/${approvalId}/decide`, { approved, note })
    return res.data
  },
}

// ── Executions ────────────────────────────────────────────────────────────────

export const executionService = {
  list: async (limit = 50) => {
    const res = await api.get('/executions', { params: { limit } })
    return res.data
  },
  get: async (id: string) => {
    const res = await api.get(`/executions/${id}`)
    return res.data
  },
}
