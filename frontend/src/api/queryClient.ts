/**
 * Configured QueryClient with global error handling and retry policies.
 */

import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { ApiError } from './client';

export type GlobalErrorHandler = (error: unknown) => void;

let globalErrorHandler: GlobalErrorHandler | null = null;

export function setGlobalErrorHandler(handler: GlobalErrorHandler | null): void {
  globalErrorHandler = handler;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => {
        if (globalErrorHandler) {
          globalErrorHandler(error);
        }
      },
    }),
    mutationCache: new MutationCache({
      onError: (error) => {
        if (globalErrorHandler) {
          globalErrorHandler(error);
        }
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        retry: (failureCount, error) => {
          // Do not retry 4xx errors (client errors, unauthenticated, forbidden, validation)
          if (error instanceof ApiError) {
            if ([400, 401, 403, 404, 409, 422].includes(error.status)) {
              return false;
            }
          }
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

