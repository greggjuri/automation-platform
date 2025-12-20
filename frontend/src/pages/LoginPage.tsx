/**
 * Login page for admin authentication.
 *
 * Displays a login form with glass styling matching the app theme.
 */

import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { Button } from '../components/common';

/**
 * Login page component.
 * Redirects to /workflows if already authenticated.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const { signIn, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      navigate('/workflows');
    }
  }, [authLoading, isAuthenticated, navigate]);

  // Handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await signIn(email, password);
      navigate('/workflows');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show loading while checking auth state
  if (authLoading) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-[#c0c0c0]">Loading...</div>
      </main>
    );
  }

  // Don't render login form if already authenticated (will redirect)
  if (isAuthenticated) {
    return null;
  }

  return (
    <main className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <header className="bg-black/50 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center">
              <span className="text-xl font-bold text-[#e8e8e8]">
                Automation Platform
              </span>
            </Link>

            <nav className="flex items-center gap-2">
              <Link
                to="/workflows"
                className="px-4 py-2 text-sm font-medium text-[#c0c0c0] hover:text-[#e8e8e8] rounded-lg hover:bg-white/5 transition-colors"
              >
                Workflows
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="glass-card w-full max-w-md p-6 md:p-8">
          {/* Title */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-[#e8e8e8] mb-2">
              Admin Login
            </h2>
            <p className="text-[#c0c0c0] text-sm">
              Sign in to manage workflows and secrets
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Input */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-[#c0c0c0] mb-1"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                disabled={isSubmitting}
                className="
                  w-full px-4 py-2.5
                  bg-white/5
                  border border-white/10
                  rounded-lg
                  text-[#e8e8e8]
                  placeholder-[#808080]
                  focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
                placeholder="admin@example.com"
              />
            </div>

            {/* Password Input */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-[#c0c0c0] mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                disabled={isSubmitting}
                className="
                  w-full px-4 py-2.5
                  bg-white/5
                  border border-white/10
                  rounded-lg
                  text-[#e8e8e8]
                  placeholder-[#808080]
                  focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
                placeholder="Enter your password"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                isLoading={isSubmitting}
                disabled={isSubmitting || !email || !password}
                className="w-full"
              >
                Sign In
              </Button>
            </div>
          </form>

          {/* Back Link */}
          <div className="mt-6 text-center">
            <Link
              to="/workflows"
              className="text-sm text-[#c0c0c0] hover:text-[#e8e8e8] transition-colors"
            >
              &larr; Back to workflows
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-4 text-center text-[#808080] text-sm border-t border-white/10">
        <p>automations.jurigregg.com</p>
      </footer>
    </main>
  );
}

export default LoginPage;
