/**
 * Global Error Mapping Layer conforming to API_DOCUMENTATION.md §3.
 * Maps backend error envelopes, HTTP status codes, and validation details
 * to uniform user-facing toast notifications with traceable request_id.
 */

import { ApiError } from './client';
import type { ToastContextValue } from '../components/ui/Toast';

export interface ValidationErrorDetail {
  field?: string;
  issue?: string;
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

export interface FormattedApiError {
  title: string;
  message: string;
  code: string;
  status: number;
  requestId?: string;
  details?: ValidationErrorDetail[];
}

/**
 * Format any unknown error or ApiError into structured error info.
 */
export function formatApiError(error: unknown, fallbackTitle: string = 'Operation Failed'): FormattedApiError {
  if (error instanceof ApiError) {
    let title = fallbackTitle;
    let message = error.message || 'An unexpected error occurred.';
    let details: ValidationErrorDetail[] | undefined;

    // Parse details if available
    if (Array.isArray(error.details)) {
      details = error.details as ValidationErrorDetail[];
    }

    switch (error.code) {
      case 'UNAUTHENTICATED':
        title = 'Session Expired';
        message = 'Your session has expired. Please log in again to continue.';
        break;

      case 'FORBIDDEN':
        title = 'Access Denied';
        message = 'Your user role does not have permission to perform this action.';
        break;

      case 'NOT_FOUND':
        title = 'Resource Not Found';
        break;

      case 'CONFLICT':
        title = 'Action Conflict';
        break;

      case 'ROSTER_BLOCKED':
        title = 'Publish Blocked by Integrity Rules';
        message = error.message || 'Roster cannot be published with unacknowledged blocking conflicts.';
        break;

      case 'VALIDATION_ERROR':
        title = 'Validation Failed';
        if (details && details.length > 0) {
          const detailMessages = details.map((d) => {
            const field = d.field || (d.loc ? d.loc.filter((p) => p !== 'body').join('.') : undefined);
            const issue = d.issue || d.msg || 'Invalid value';
            return field ? `${field}: ${issue}` : issue;
          });
          message = detailMessages.join(' • ');
        }
        break;

      case 'RATE_LIMITED':
        title = 'Rate Limit Exceeded';
        message = 'Too many requests. Please wait a moment and try again.';
        break;

      case 'INTERNAL_ERROR':
        title = 'Server Error';
        message = 'An unexpected server error occurred. Please contact support with the request ID.';
        break;

      default:
        if (error.status === 400) title = 'Invalid Request';
        else if (error.status === 404) title = 'Not Found';
        else if (error.status === 409) title = 'Conflict';
        else if (error.status >= 500) title = 'Server Error';
        break;
    }

    return {
      title,
      message,
      code: error.code,
      status: error.status,
      requestId: error.requestId,
      details,
    };
  }

  if (error instanceof Error) {
    return {
      title: fallbackTitle,
      message: error.message || 'An error occurred during execution.',
      code: 'CLIENT_ERROR',
      status: 0,
    };
  }

  return {
    title: fallbackTitle,
    message: typeof error === 'string' ? error : 'An unexpected error occurred.',
    code: 'UNKNOWN_ERROR',
    status: 0,
  };
}

/**
 * Trigger an error toast with formatted message and request ID badge.
 */
export function showApiErrorToast(
  error: unknown,
  toast: ToastContextValue,
  fallbackTitle: string = 'Operation Failed'
): string {
  const formatted = formatApiError(error, fallbackTitle);
  return toast.error(formatted.title, formatted.message, formatted.requestId);
}

