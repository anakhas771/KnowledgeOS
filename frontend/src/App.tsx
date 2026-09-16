import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router';
import { useAuthStore } from './store/authStore';
import { authApi } from './features/auth/api/authApi';
import Login from './pages/Login';
import Register from './pages/Register';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Knowledge from './pages/Knowledge';
import Documents from './pages/Documents';
import Search from './pages/Search';
import Settings from './pages/Settings';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center">Loading session...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const { setAuth, clearAuth, setLoading } = useAuthStore();
  
  useEffect(() => {
    // Attempt session restoration on initial load
    const restoreSession = async () => {
      try {
        // We call /refresh/ which uses HttpOnly cookie.
        // It returns a new access token.
        const response = await authApi.me(); // This will fail and trigger interceptor if we have no access token but have a refresh cookie
        setAuth(response, useAuthStore.getState().accessToken || '');
      } catch (e) {
        clearAuth();
      } finally {
        setLoading(false);
      }
    };
    restoreSession();
  }, [setAuth, clearAuth, setLoading]);

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route 
        path="/app"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        } 
      >
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="documents" element={<Documents />} />
        <Route path="search" element={<Search />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
