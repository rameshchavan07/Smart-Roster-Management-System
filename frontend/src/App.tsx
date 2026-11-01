import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout, DashboardPlaceholder, RosterPlaceholder } from './routes';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<DashboardPlaceholder />} />
            <Route path="roster" element={<RosterPlaceholder />} />
            <Route path="conflicts" element={<DashboardPlaceholder />} />
            <Route path="leaves" element={<DashboardPlaceholder />} />
            <Route path="team" element={<DashboardPlaceholder />} />
            <Route path="brands" element={<DashboardPlaceholder />} />
            <Route path="reports" element={<DashboardPlaceholder />} />
            <Route path="settings" element={<DashboardPlaceholder />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
