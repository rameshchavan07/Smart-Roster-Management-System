/**
 * Authentication API calls connecting to /api/v1/auth/* endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, setAccessToken } from './client';
import type { DemoAccountInfo, LoginCredentials, TokenResponse, User } from '../types/auth';

export async function loginApi(credentials: LoginCredentials): Promise<TokenResponse> {
  const data = await apiClient<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function refreshApi(): Promise<TokenResponse> {
  const data = await apiClient<TokenResponse>('/auth/refresh', {
    method: 'POST',
  });
  setAccessToken(data.access_token);
  return data;
}

export async function logoutApi(): Promise<{ message: string }> {
  try {
    return await apiClient<{ message: string }>('/auth/logout', {
      method: 'POST',
    });
  } finally {
    setAccessToken(null);
  }
}

export async function getMeApi(): Promise<User> {
  return apiClient<User>('/auth/me');
}

export async function getDemoAccountsApi(): Promise<DemoAccountInfo[]> {
  return apiClient<DemoAccountInfo[]>('/auth/demo-accounts');
}

// ----------------------------------------------------------------------------
// React Query Hooks
// ----------------------------------------------------------------------------

export function useCurrentUserQuery(enabled: boolean = true) {
  return useQuery({
    queryKey: ['auth-me'],
    queryFn: getMeApi,
    enabled,
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: false,
  });
}

export function useDemoAccountsQuery() {
  return useQuery({
    queryKey: ['auth-demo-accounts'],
    queryFn: getDemoAccountsApi,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useLoginMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => loginApi(credentials),
    onSuccess: (data) => {
      queryClient.setQueryData(['auth-me'], data.user);
    },
  });
}

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logoutApi,
    onSuccess: () => {
      queryClient.clear();
    },
  });
}


