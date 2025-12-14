/**
 * Axios API client configuration.
 *
 * Provides a pre-configured axios instance for all API calls.
 * Uses VITE_API_URL environment variable or falls back to the deployed API.
 */

import axios from 'axios';

/** Base API URL - can be overridden via environment variable */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com';

/**
 * Pre-configured axios instance for API calls.
 *
 * @example
 * ```typescript
 * const response = await apiClient.get('/workflows');
 * const workflows = response.data;
 * ```
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add response interceptor for error logging
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
