'use client';

import { useAuthContext } from './AuthContext';

/**
 * Auth hook return type
 */
export interface UseAuthReturn {
  /** Current user email or null if not authenticated */
  user: string | null;
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Whether auth state is being loaded */
  isLoading: boolean;
  /** Sign in with email and password */
  signIn: (email: string, password: string) => Promise<void>;
  /** Sign out and clear tokens */
  signOut: () => void;
  /** Get current access token (refreshes if needed) */
  getAccessToken: () => Promise<string | null>;
}

/**
 * Hook to access authentication state and methods
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { user, isAuthenticated, signIn, signOut } = useAuth();
 *
 *   if (!isAuthenticated) {
 *     return <button onClick={() => signIn(email, password)}>Login</button>;
 *   }
 *
 *   return (
 *     <div>
 *       <p>Welcome, {user}</p>
 *       <button onClick={signOut}>Logout</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuth(): UseAuthReturn {
  return useAuthContext();
}
