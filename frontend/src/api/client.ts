/**
 * Typed HTTP client with Bearer auth injection, automatic token rotation,
 * and uniform error parsing conforming to API_DOCUMENTATION.md §1 & §3.
 */

const RAW_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const API_BASE_URL = RAW_API_URL.endsWith('/api/v1')
  ? RAW_API_URL
  : `${RAW_API_URL.replace(/\/$/, '')}/api/v1`;

const ACCESS_TOKEN_STORAGE_KEY = 'rosterops_access_token';

let currentAccessToken: string | null = localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
let onAuthFailureCallback: (() => void) | null = null;
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

export function setAccessToken(token: string | null): void {
  currentAccessToken = token;
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  }
}

export function getAccessToken(): string | null {
  return currentAccessToken;
}

export function setOnAuthFailure(callback: () => void): void {
  onAuthFailureCallback = callback;
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;
  requestId?: string;

  constructor(message: string, status: number, code: string = 'API_ERROR', details?: unknown, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export async function apiClientBlob(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ blob: Blob; filename: string }> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (currentAccessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${currentAccessToken}`);
  }

  if (!headers.has('X-Request-ID')) {
    const genId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `req-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    headers.set('X-Request-ID', genId);
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include',
  };

  const response = await fetch(url, fetchOptions);

  if (!response.ok) {
    let errMsg = `Export request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      errMsg = errJson?.error?.message || errJson?.detail || errMsg;
    } catch {
      // not JSON
    }
    throw new ApiError(errMsg, response.status);
  }

  const disposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
  let filename = 'roster-export';
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  return { blob, filename };
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (currentAccessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${currentAccessToken}`);
  }

  if (!headers.has('X-Request-ID')) {
    const genId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `req-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    headers.set('X-Request-ID', genId);
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include', // sends and receives HttpOnly refresh_token cookie
  };

  const response = await fetch(url, fetchOptions);

  // Handle 401 Unauthorized - attempt silent refresh
  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          setAccessToken(data.access_token);
          isRefreshing = false;
          onRefreshed(data.access_token);

          // Retry initial request with new access token
          headers.set('Authorization', `Bearer ${data.access_token}`);
          return apiClient<T>(endpoint, { ...options, headers });
        } else {
          isRefreshing = false;
          setAccessToken(null);
          if (onAuthFailureCallback) onAuthFailureCallback();
          throw new ApiError('Session expired. Please log in again.', 401, 'UNAUTHENTICATED');
        }
      } catch (err) {
        isRefreshing = false;
        setAccessToken(null);
        if (onAuthFailureCallback) onAuthFailureCallback();
        throw err;
      }
    }

    // If refresh is already in progress, queue this request
    return new Promise<T>((resolve, reject) => {
      addRefreshSubscriber((newToken: string) => {
        headers.set('Authorization', `Bearer ${newToken}`);
        apiClient<T>(endpoint, { ...options, headers }).then(resolve).catch(reject);
      });
    });
  }

  // Parse response
  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    const errorEnvelope = data?.error;
    const message = errorEnvelope?.message || data?.detail || response.statusText || 'An error occurred';
    const code = errorEnvelope?.code || 'HTTP_ERROR';
    const requestId = errorEnvelope?.request_id || response.headers.get('X-Request-ID') || response.headers.get('x-request-id') || undefined;
    const details = errorEnvelope?.details;

    throw new ApiError(message, response.status, code, details, requestId);
  }

  return data as T;
}

