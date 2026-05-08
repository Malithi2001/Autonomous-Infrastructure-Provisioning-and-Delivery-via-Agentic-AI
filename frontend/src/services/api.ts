import axios from 'axios'
import type { RoleProfile, User, UserRole } from '@/types'
import { normalizeRole } from '@/lib/rbac'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const API_BASE_URL = BASE_URL.replace(/\/$/, '')

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    const url = err.config?.url || ''
    const isAuthProbe =
      url.includes('/auth/me') ||
      url.includes('/auth/login') ||
      url.includes('/auth/logout') ||
      url.includes('/auth/register') ||
      url.includes('/auth/roles')
    if (status === 401 && !isAuthProbe) {
      window.dispatchEvent(new CustomEvent('devops-auth:unauthorized'))
    }
    return Promise.reject(err)
  },
)

export interface LoginResponse {
  user?: User
  user_id?: string
  username?: string
  role?: string
  email?: string
  id?: string
  is_active?: boolean
  created_at?: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
  role: Extract<UserRole, 'developer' | 'viewer'>
}

export interface AdminCreateUserRequest {
  email: string
  username: string
  password: string
  role: UserRole
  is_active?: boolean
}

function normalizeUser(data: LoginResponse | User): User {
  if ('user' in data && data.user) return { ...data.user, role: normalizeRole(data.user.role) }
  return {
    id: data.id || ('user_id' in data && data.user_id ? data.user_id : ''),
    email: data.email,
    username: data.username || '',
    role: normalizeRole(data.role),
    is_active: data.is_active,
    created_at: data.created_at,
  }
}

export const authService = {
  login: async (email: string, password: string): Promise<User> => {
    const res = await api.post<LoginResponse>('/auth/login', { email, password })
    return normalizeUser(res.data)
  },
  register: async ({ email, username, password, role }: RegisterRequest): Promise<User> => {
    const res = await api.post<LoginResponse>('/auth/register', { email, username, password, role })
    return normalizeUser(res.data)
  },
  me: async (): Promise<User> => {
    const res = await api.get<User>('/auth/me')
    return normalizeUser(res.data)
  },
  logout: async (): Promise<void> => {
    await api.post('/auth/logout')
  },
  roles: async (): Promise<RoleProfile[]> => {
    const res = await api.get<{ roles: RoleProfile[] }>('/auth/roles')
    return res.data.roles
  },
  listUsers: async (): Promise<User[]> => {
    const res = await api.get<User[]>('/auth/users')
    return res.data.map(normalizeUser)
  },
  createUser: async (payload: AdminCreateUserRequest): Promise<User> => {
    const res = await api.post<User>('/auth/users', payload)
    return normalizeUser(res.data)
  },
}

export const agentService = {
  chat: async (message: string, sessionId?: string) => {
    const res = await api.post('/agent/chat', { message, session_id: sessionId })
    return res.data
  },
  clearSession: async (sessionId: string) => {
    await api.delete(`/agent/session/${sessionId}`)
  },
}

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
