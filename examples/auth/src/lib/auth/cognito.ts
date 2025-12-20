/**
 * Cognito client wrapper for Golf Ghost authentication
 * Provides signIn, signOut, and token management functions
 */

import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';
import { cognitoConfig, isCognitoConfigured } from './config';

// Session storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'golf_ghost_access_token',
  ID_TOKEN: 'golf_ghost_id_token',
  REFRESH_TOKEN: 'golf_ghost_refresh_token',
  USER_EMAIL: 'golf_ghost_user_email',
} as const;

// Create user pool instance (lazily, to avoid SSR issues)
let userPool: CognitoUserPool | null = null;

function getUserPool(): CognitoUserPool | null {
  if (typeof window === 'undefined') return null;
  if (!isCognitoConfigured()) return null;

  if (!userPool) {
    userPool = new CognitoUserPool({
      UserPoolId: cognitoConfig.userPoolId,
      ClientId: cognitoConfig.clientId,
    });
  }
  return userPool;
}

/**
 * Authentication result returned from signIn
 */
export interface AuthResult {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  email: string;
}

/**
 * Sign in with email and password
 * Returns tokens on success, throws error on failure
 */
export function signIn(email: string, password: string): Promise<AuthResult> {
  return new Promise((resolve, reject) => {
    const pool = getUserPool();
    if (!pool) {
      reject(new Error('Cognito not configured'));
      return;
    }

    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: pool,
    });

    const authDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    cognitoUser.authenticateUser(authDetails, {
      onSuccess: (session: CognitoUserSession) => {
        const result: AuthResult = {
          accessToken: session.getAccessToken().getJwtToken(),
          idToken: session.getIdToken().getJwtToken(),
          refreshToken: session.getRefreshToken().getToken(),
          email,
        };

        // Store tokens in sessionStorage
        storeTokens(result);

        resolve(result);
      },
      onFailure: (err) => {
        reject(formatCognitoError(err));
      },
      newPasswordRequired: () => {
        reject(new Error('Password change required. Please contact admin.'));
      },
    });
  });
}

/**
 * Sign out and clear stored tokens
 */
export function signOut(): void {
  // Clear stored tokens
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    sessionStorage.removeItem(STORAGE_KEYS.ID_TOKEN);
    sessionStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    sessionStorage.removeItem(STORAGE_KEYS.USER_EMAIL);
  }

  // Sign out from Cognito
  const pool = getUserPool();
  if (pool) {
    const currentUser = pool.getCurrentUser();
    if (currentUser) {
      currentUser.signOut();
    }
  }
}

/**
 * Get current user email from storage
 */
export function getCurrentUser(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(STORAGE_KEYS.USER_EMAIL);
}

/**
 * Get current access token
 * Returns null if not authenticated or token expired
 * Attempts to refresh if token is expired
 */
export async function getAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;

  const token = sessionStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  if (!token) return null;

  // Check if token is expired
  if (isTokenExpired(token)) {
    try {
      const refreshed = await refreshSession();
      return refreshed ? sessionStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) : null;
    } catch {
      signOut();
      return null;
    }
  }

  return token;
}

/**
 * Check if user is authenticated (has valid tokens)
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  const token = sessionStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  return token !== null && !isTokenExpired(token);
}

/**
 * Refresh the session using refresh token
 */
export function refreshSession(): Promise<boolean> {
  return new Promise((resolve, reject) => {
    const pool = getUserPool();
    if (!pool) {
      resolve(false);
      return;
    }

    const email = sessionStorage.getItem(STORAGE_KEYS.USER_EMAIL);
    if (!email) {
      resolve(false);
      return;
    }

    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: pool,
    });

    // Get the refresh token
    const refreshToken = sessionStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    if (!refreshToken) {
      resolve(false);
      return;
    }

    // Use the SDK's refresh method
    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) {
        reject(err || new Error('Failed to refresh session'));
        return;
      }

      // Store new tokens
      storeTokens({
        accessToken: session.getAccessToken().getJwtToken(),
        idToken: session.getIdToken().getJwtToken(),
        refreshToken: session.getRefreshToken().getToken(),
        email,
      });

      resolve(true);
    });
  });
}

/**
 * Store tokens in sessionStorage
 */
function storeTokens(result: AuthResult): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, result.accessToken);
  sessionStorage.setItem(STORAGE_KEYS.ID_TOKEN, result.idToken);
  sessionStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, result.refreshToken);
  sessionStorage.setItem(STORAGE_KEYS.USER_EMAIL, result.email);
}

/**
 * Check if JWT token is expired
 */
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    // Consider expired if less than 5 minutes remaining
    return Date.now() > exp - 5 * 60 * 1000;
  } catch {
    return true;
  }
}

/**
 * Format Cognito error messages for user display
 */
function formatCognitoError(error: Error & { code?: string }): Error {
  const code = error.code || '';
  const message = error.message || 'Authentication failed';

  switch (code) {
    case 'NotAuthorizedException':
      return new Error('Incorrect email or password');
    case 'UserNotFoundException':
      return new Error('User not found');
    case 'UserNotConfirmedException':
      return new Error('User not confirmed. Please contact admin.');
    case 'PasswordResetRequiredException':
      return new Error('Password reset required. Please contact admin.');
    case 'InvalidParameterException':
      return new Error('Invalid email or password format');
    case 'NetworkError':
      return new Error('Network error. Please check your connection.');
    default:
      return new Error(message);
  }
}
