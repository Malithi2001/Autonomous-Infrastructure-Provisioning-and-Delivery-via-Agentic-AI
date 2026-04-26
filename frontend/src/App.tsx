import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import ChatPage from '@/pages/ChatPage'
import ApprovalsPage from '@/pages/ApprovalsPage'
import ExecutionsPage from '@/pages/ExecutionsPage'
import LoginPage from '@/pages/LoginPage'
import { useAuthStore } from '@/store/authStore'
import { canAccessChat, getDefaultRouteForRole } from '@/lib/rbac'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function RoleRoute({
  children,
  allow,
}: {
  children: React.ReactNode
  allow: (role?: string | null) => boolean
}) {
  const { user } = useAuthStore()
  return allow(user?.role) ? <>{children}</> : <Navigate to={getDefaultRouteForRole(user?.role)} replace />
}

export default function App() {
  const { user } = useAuthStore()

  return (
    <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to={getDefaultRouteForRole(user?.role)} replace />} />
          <Route
            path="chat"
            element={
              <RoleRoute allow={canAccessChat}>
                <ChatPage />
              </RoleRoute>
            }
          />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="executions" element={<ExecutionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
