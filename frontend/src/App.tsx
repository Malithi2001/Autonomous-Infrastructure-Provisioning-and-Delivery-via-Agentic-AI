import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import ChatPage from '@/pages/ChatPage'
import ApprovalsPage from '@/pages/ApprovalsPage'
import ExecutionsPage from '@/pages/ExecutionsPage'
import LoginPage from '@/pages/LoginPage'
import { useAuthStore } from '@/store/authStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
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
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="executions" element={<ExecutionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
