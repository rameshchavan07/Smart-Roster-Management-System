import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout, DashboardPlaceholder, RosterPlaceholder } from './routes';
import { DesignSystemPage } from './features/design-system/DesignSystemPage';
import { AuthProvider, useAuth } from './features/auth/AuthContext';
import { ProtectedRoute } from './features/auth/ProtectedRoute';
import { LoginPage } from './features/auth/LoginPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

const RootRedirect: React.FC = () => {
  const { isEmployee } = useAuth();
  // Employees default to /roster ("My Roster"), Managers to / (Dashboard)
  if (isEmployee) {
    return <Navigate to="/roster" replace />;
  }
  return <DashboardPlaceholder />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Authentication Route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Application Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<RootRedirect />} />
              <Route path="roster" element={<RosterPlaceholder />} />
              <Route
                path="conflicts"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <DashboardPlaceholder />
                  </ProtectedRoute>
                }
              />
              <Route path="leaves" element={<DashboardPlaceholder />} />
              <Route
                path="team"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <DashboardPlaceholder />
                  </ProtectedRoute>
                }
              />
              <Route
                path="brands"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <DashboardPlaceholder />
                  </ProtectedRoute>
                }
              />
              <Route
                path="reports"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <DashboardPlaceholder />
                  </ProtectedRoute>
                }
              />
              <Route
                path="settings"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER']}>
                    <DashboardPlaceholder />
                  </ProtectedRoute>
                }
              />
              <Route path="design-system" element={<DesignSystemPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;

