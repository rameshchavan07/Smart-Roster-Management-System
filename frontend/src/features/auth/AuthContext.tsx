import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import type { LoginCredentials, User, UserRole } from '../../types/auth';
import { getMeApi, loginApi, logoutApi, refreshApi } from '../../api/auth';
import { getAccessToken, setAccessToken, setOnAuthFailure } from '../../api/client';

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isOpsManager: boolean;
  isPodLead: boolean;
  isEmployee: boolean;
  hasRole: (roles: UserRole[]) => boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const handleAuthFailure = useCallback(() => {
    setUser(null);
    setAccessToken(null);
  }, []);

  useEffect(() => {
    setOnAuthFailure(handleAuthFailure);
  }, [handleAuthFailure]);

  // Initial session restoration
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      const storedToken = getAccessToken();
      try {
        if (storedToken) {
          const profile = await getMeApi();
          if (isMounted) setUser(profile);
        } else {
          // Attempt cookie-based silent refresh
          const refreshRes = await refreshApi();
          if (refreshRes && isMounted) {
            setUser(refreshRes.user);
          }
        }
      } catch {
        if (isMounted) {
          setUser(null);
          setAccessToken(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const res = await loginApi(credentials);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await logoutApi();
    } catch {
      // Ignore network errors on logout
    } finally {
      setUser(null);
      setAccessToken(null);
      setIsLoading(false);
    }
  }, []);

  const isOpsManager = user?.role === 'OPS_MANAGER';
  const isPodLead = user?.role === 'POD_LEAD';
  const isEmployee = user?.role === 'EMPLOYEE';

  const hasRole = useCallback(
    (roles: UserRole[]) => {
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      isOpsManager,
      isPodLead,
      isEmployee,
      hasRole,
      login,
      logout,
    }),
    [user, isLoading, isOpsManager, isPodLead, isEmployee, hasRole, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
