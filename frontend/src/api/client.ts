/**
 * Axios API client configuration.
 *
 * Provides a pre-configured axios instance for all API calls.
 * Uses VITE_API_URL environment variable or falls back to the deployed API.
 * Automatically includes JWT auth headers when user is authenticated.
 */

import axios from 'axios';
import { getAccessToken } from '../lib/auth';

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

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
  async (config) => {
    const token = await getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error logging
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
