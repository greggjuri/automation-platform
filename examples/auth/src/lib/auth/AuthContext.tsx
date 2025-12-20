'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import {
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
  getCurrentUser,
  getAccessToken as cognitoGetAccessToken,
  isAuthenticated as cognitoIsAuthenticated,
} from './cognito';

/**
 * Auth context state interface
 */
interface AuthContextState {
  user: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  getAccessToken: () => Promise<string | null>;
}

// Create context with undefined default (will throw if used outside provider)
const AuthContext = createContext<AuthContextState | undefined>(undefined);

/**
 * Auth Provider Props
 */
interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Auth Provider Component
 * Wraps the application and provides authentication state
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = () => {
      try {
        const authenticated = cognitoIsAuthenticated();
        const currentUser = getCurrentUser();
        setIsAuthenticated(authenticated);
        setUser(authenticated ? currentUser : null);
      } catch {
        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Sign in handler
  const signIn = useCallback(async (email: string, password: string) => {
    const result = await cognitoSignIn(email, password);
    setUser(result.email);
    setIsAuthenticated(true);
  }, []);

  // Sign out handler
  const signOut = useCallback(() => {
    cognitoSignOut();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  // Get access token handler
  const getAccessToken = useCallback(async () => {
    const token = await cognitoGetAccessToken();
    // If token is null, user may have been signed out
    if (token === null && isAuthenticated) {
      setIsAuthenticated(false);
      setUser(null);
    }
    return token;
  }, [isAuthenticated]);

  const value: AuthContextState = {
    user,
    isAuthenticated,
    isLoading,
    signIn,
    signOut,
    getAccessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to use auth context
 * Throws if used outside AuthProvider
 */
export function useAuthContext(): AuthContextState {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
