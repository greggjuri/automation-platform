/**
 * Main layout wrapper component.
 *
 * Provides consistent page structure with header and main content area.
 */

import type { ReactNode } from 'react';
import { Header } from './Header';

interface LayoutProps {
  /** Page content */
  children: ReactNode;
}

/**
 * Main layout component wrapping all pages.
 *
 * @param props - Component props
 * @param props.children - Page content to render
 */
export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}

export default Layout;
