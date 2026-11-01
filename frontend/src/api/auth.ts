/**
 * Authentication API calls connecting to /api/v1/auth/* endpoints.
 */

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
