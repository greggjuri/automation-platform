/**
 * Centralized error handling utilities.
 *
 * Provides consistent error message extraction and toast notifications.
 */

import { toast } from 'react-hot-toast';
import axios from 'axios';

/**
 * Extract a user-friendly error message from various error types.
 *
 * @param error - The error to extract message from
 * @returns A user-friendly error message string
 *
 * @example
 * ```ts
 * try {
 *   await api.post('/workflows');
 * } catch (err) {
 *   const message = getErrorMessage(err);
 *   console.error(message);
 * }
 * ```
 */
export function getErrorMessage(error: unknown): string {
  // Axios error
  if (axios.isAxiosError(error)) {
    // Network error (no response)
    if (!error.response) {
      return 'Connection lost. Please check your network.';
    }

    // API error with message field
    const data = error.response.data as Record<string, unknown> | undefined;
    if (data?.message && typeof data.message === 'string') {
      return truncateMessage(data.message);
    }

    // API error with error field
    if (data?.error && typeof data.error === 'string') {
      return truncateMessage(data.error);
    }

    // Status-based fallbacks
    const status = error.response.status;
    if (status === 400) return 'Invalid request. Please check your input.';
    if (status === 401) return 'Authentication required.';
    if (status === 403) return 'Permission denied.';
    if (status === 404) return 'Resource not found.';
    if (status === 409) return 'Conflict. Resource may already exist.';
    if (status >= 500) return 'Server error. Please try again later.';

    return error.message || 'Request failed';
  }

  // Standard Error object
  if (error instanceof Error) {
    return truncateMessage(error.message);
  }

  // String error
  if (typeof error === 'string') {
    return truncateMessage(error);
  }

  // Unknown error type
  return 'Something went wrong';
}

/**
 * Handle an API error by showing a toast notification.
 *
 * @param error - The error to handle
 * @param context - Optional context to prepend to the message
 *
 * @example
 * ```ts
 * try {
 *   await api.delete(`/workflows/${id}`);
 * } catch (err) {
 *   handleApiError(err, 'Failed to delete workflow');
 * }
 * ```
 */
export function handleApiError(error: unknown, context?: string): void {
  const message = getErrorMessage(error);
  const fullMessage = context ? `${context}: ${message}` : message;
  toast.error(fullMessage);
}

/**
 * Truncate long error messages for display in toasts.
 *
 * @param message - Message to truncate
 * @param maxLength - Maximum length (default: 100)
 * @returns Truncated message
 */
function truncateMessage(message: string, maxLength = 100): string {
  if (message.length <= maxLength) return message;
  return `${message.slice(0, maxLength - 3)}...`;
}
