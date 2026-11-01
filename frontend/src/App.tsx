import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './routes';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { DesignSystemPage } from './features/design-system/DesignSystemPage';
import { TeamPage } from './features/team/TeamPage';
import { BrandsPage } from './features/brands/BrandsPage';
import { LeavesPage } from './features/leaves/LeavesPage';
import { RulesHolidaysPage } from './features/rules/RulesHolidaysPage';
import { RosterWorkspacePage } from './features/roster/RosterWorkspacePage';
import { MyRosterPage } from './features/roster/MyRosterPage';
import { ConflictsPage } from './features/roster/ConflictsPage';
import { ImpactSimulatorPage } from './features/roster/ImpactSimulatorPage';
import { SettingsPage } from './features/settings/SettingsPage';
import { ReportsPage } from './features/reports/ReportsPage';
import { AuthProvider, useAuth } from './features/auth/AuthContext';
import { MonthProvider } from './context/MonthContext';
import { ToastProvider } from './components/ui';
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
  return <DashboardPage />;
};

const RosterRoute: React.FC = () => {
  const { isEmployee } = useAuth();
  if (isEmployee) {
    return <MyRosterPage />;
  }
  return <RosterWorkspacePage />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MonthProvider>
          <ToastProvider>
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
              <Route path="roster" element={<RosterRoute />} />
              <Route path="my-roster" element={<MyRosterPage />} />
              <Route
                path="conflicts"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <ConflictsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="simulator"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <ImpactSimulatorPage />
                  </ProtectedRoute>
                }
              />
              <Route path="leaves" element={<LeavesPage />} />
              <Route
                path="team"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <TeamPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="brands"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <BrandsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="rules"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <RulesHolidaysPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="reports"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER', 'POD_LEAD']}>
                    <ReportsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="settings"
                element={
                  <ProtectedRoute allowedRoles={['OPS_MANAGER']}>
                    <SettingsPage />
                  </ProtectedRoute>
                }
              />
              <Route path="design-system" element={<DesignSystemPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        </ToastProvider>
        </MonthProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;

