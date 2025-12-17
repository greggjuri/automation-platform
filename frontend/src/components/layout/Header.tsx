/**
 * Application header component.
 *
 * Displays the app title and navigation links with glass styling.
 */

import { Link, useLocation } from 'react-router-dom';

/**
 * Main application header with navigation.
 */
export function Header() {
  const location = useLocation();

  return (
    <header className="bg-black/50 backdrop-blur-sm border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <span className="text-xl font-bold text-[#e8e8e8]">
                Automation Platform
              </span>
            </Link>
          </div>
          <nav className="flex items-center space-x-1">
            <NavLink to="/workflows" current={location.pathname}>
              Workflows
            </NavLink>
            <NavLink to="/secrets" current={location.pathname}>
              Secrets
            </NavLink>
          </nav>
        </div>
      </div>
    </header>
  );
}

interface NavLinkProps {
  to: string;
  current: string;
  children: React.ReactNode;
}

function NavLink({ to, current, children }: NavLinkProps) {
  const isActive = current.startsWith(to);

  return (
    <Link
      to={to}
      className={`
        px-4 py-2 rounded-full text-sm font-medium transition-all duration-300
        ${
          isActive
            ? 'bg-white/10 text-[#e8e8e8] border border-white/10'
            : 'text-[#c0c0c0] hover:text-[#e8e8e8] hover:bg-white/5 border border-transparent'
        }
      `}
    >
      {children}
    </Link>
  );
}

export default Header;
