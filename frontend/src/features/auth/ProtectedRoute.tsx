import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { UserRole } from '../../types/auth';
import { Skeleton } from '../../components/ui/Skeleton';
import { AlertTriangle } from 'lucide-react';
import { Button } from '../../components/ui/Button';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-bg p-6">
        <div className="w-full max-w-sm space-y-4">
          <Skeleton className="h-8 w-40 mx-auto" />
          <Skeleton className="h-28 w-full rounded-ctl" />
          <Skeleton className="h-10 w-full rounded-ctl" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center p-8 text-center bg-surface rounded-ctl border border-border">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-warn/10 text-warn mb-4">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h2 className="text-base font-semibold text-ink">Access Restricted</h2>
        <p className="mt-1 text-xs text-ink-2 max-w-md">
          Your current role (<span className="font-mono font-medium text-ink">{user.role}</span>) does not have
          permission to access this section.
        </p>
        <div className="mt-5">
          <Button variant="secondary" onClick={() => window.history.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

