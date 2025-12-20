'use client';

import { useState, FormEvent, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GlassCard } from '@/components/GlassCard';
import { GlassButton } from '@/components/GlassButton';
import { useAuth } from '@/lib/auth';

/**
 * Login Page
 * Allows admin users to sign in with email/password
 */
export default function LoginPage() {
  const router = useRouter();
  const { signIn, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push('/manage');
    }
  }, [authLoading, isAuthenticated, router]);

  // Handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await signIn(email, password);
      router.push('/manage');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show loading while checking auth state
  if (authLoading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-slate-400">Loading...</div>
      </main>
    );
  }

  // Don't render login form if already authenticated (will redirect)
  if (isAuthenticated) {
    return null;
  }

  return (
    <main className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3">
              <span className="text-2xl md:text-3xl">&#129302;</span>
              <h1 className="text-xl md:text-2xl font-bold text-text-primary tracking-tight">
                GOLF GHOST
              </h1>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-2">
              <Link
                href="/"
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800/50 transition-colors"
              >
                Generate
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <GlassCard className="w-full max-w-md p-6 md:p-8">
          {/* Title */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-text-primary mb-2">
              Admin Login
            </h2>
            <p className="text-text-muted text-sm">
              Sign in to manage courses
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
                className="block text-sm font-medium text-text-secondary mb-1"
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
                  bg-slate-700/50
                  border border-slate-600/50
                  rounded-lg
                  text-text-primary
                  placeholder-slate-500
                  focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50
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
                className="block text-sm font-medium text-text-secondary mb-1"
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
                  bg-slate-700/50
                  border border-slate-600/50
                  rounded-lg
                  text-text-primary
                  placeholder-slate-500
                  focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
                placeholder="Enter your password"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <GlassButton
                type="submit"
                loading={isSubmitting}
                disabled={isSubmitting || !email || !password}
                className="w-full"
              >
                Sign In
              </GlassButton>
            </div>
          </form>

          {/* Back Link */}
          <div className="mt-6 text-center">
            <Link
              href="/"
              className="text-sm text-slate-400 hover:text-cyan-400 transition-colors"
            >
              &larr; Back to score generator
            </Link>
          </div>
        </GlassCard>
      </div>

      {/* Footer */}
      <footer className="py-4 text-center text-text-muted text-sm border-t border-slate-700/50">
        <p>ghost.jurigregg.com</p>
      </footer>
    </main>
  );
}
