/**
 * Application header component.
 *
 * Displays the app title, navigation links, and auth controls with glass styling.
 */

import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';

/**
 * Main application header with navigation.
 */
export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, signOut, isLoading } = useAuth();

  const handleLogout = () => {
    signOut();
    navigate('/workflows');
  };

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
            {isAuthenticated && (
              <NavLink to="/secrets" current={location.pathname}>
                Secrets
              </NavLink>
            )}
            <div className="ml-4 flex items-center space-x-2">
              {isLoading ? (
                <span className="text-sm text-[#808080]">...</span>
              ) : isAuthenticated ? (
                <>
                  <span className="text-sm text-[#c0c0c0] hidden sm:inline">
                    {user}
                  </span>
                  <button
                    onClick={handleLogout}
                    className="px-4 py-2 rounded-full text-sm font-medium text-[#c0c0c0] hover:text-[#e8e8e8] hover:bg-white/5 border border-transparent transition-all duration-300"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="px-4 py-2 rounded-full text-sm font-medium text-[#c0c0c0] hover:text-[#e8e8e8] hover:bg-white/5 border border-transparent transition-all duration-300"
                >
                  Login
                </Link>
              )}
            </div>
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
