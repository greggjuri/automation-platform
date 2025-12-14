/**
 * Application header component.
 *
 * Displays the app title and navigation links.
 */

import { Link } from 'react-router-dom';

/**
 * Main application header with navigation.
 */
export function Header() {
  return (
    <header className="bg-slate-800 border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <span className="text-xl font-bold text-white">
                Automation Platform
              </span>
            </Link>
          </div>
          <nav className="flex items-center space-x-4">
            <Link
              to="/workflows"
              className="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Workflows
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}

export default Header;
