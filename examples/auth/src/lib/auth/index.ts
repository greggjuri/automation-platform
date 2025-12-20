/**
 * Auth module barrel export
 * Provides all authentication functionality for Golf Ghost
 */

// Configuration
export { cognitoConfig, isCognitoConfigured } from './config';
export type { CognitoConfig } from './config';

// Cognito client functions
export {
  signIn,
  signOut,
  getCurrentUser,
  getAccessToken,
  isAuthenticated,
  refreshSession,
} from './cognito';
export type { AuthResult } from './cognito';

// React context and provider
export { AuthProvider, useAuthContext } from './AuthContext';

// React hook
export { useAuth } from './useAuth';
export type { UseAuthReturn } from './useAuth';
