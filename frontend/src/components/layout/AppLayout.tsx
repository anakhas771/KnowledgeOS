import { Outlet, useNavigate, useLocation, Link } from 'react-router';
import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { authApi } from '../../features/auth/api/authApi';
import { Button } from '../ui/button';
import {
  LayoutDashboard,
  Library,
  FileText,
  Search,
  Settings,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import clsx from 'clsx';

const NAVIGATION = [
  { name: 'Dashboard', href: '/app/dashboard', icon: LayoutDashboard },
  { name: 'Knowledge', href: '/app/knowledge', icon: Library },
  { name: 'Documents', href: '/app/documents', icon: FileText },
  { name: 'Search', href: '/app/search', icon: Search },
  { name: 'Settings', href: '/app/settings', icon: Settings },
];

export default function AppLayout() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (e) {
      console.error('Logout error', e);
    } finally {
      clearAuth();
      navigate('/login');
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden">
      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-900/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-white transition-transform md:static md:translate-x-0",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b px-6">
          <h1 className="text-xl font-bold tracking-tight">KnowledgeOS</h1>
          <Button
            className="md:hidden bg-transparent shadow-none hover:bg-gray-100 text-gray-500 px-2 h-auto py-1"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="flex-1 space-y-1 p-4">
          {NAVIGATION.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={clsx(
                  'group flex items-center rounded-md px-3 py-2 text-sm font-medium',
                  isActive
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                <item.icon
                  className={clsx(
                    'mr-3 h-5 w-5 flex-shrink-0',
                    isActive ? 'text-gray-900' : 'text-gray-400 group-hover:text-gray-500'
                  )}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="border-t p-4">
          <Button
            className="w-full justify-start text-red-600 bg-transparent hover:bg-red-50 hover:text-red-700 shadow-none font-medium"
            onClick={handleLogout}
          >
            <LogOut className="mr-3 h-5 w-5" />
            Logout
          </Button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b bg-white px-4 md:px-8">
          <div className="flex flex-1 items-center">
            <Button
              className="mr-4 px-2 text-gray-600 bg-transparent shadow-none hover:bg-gray-100 md:hidden h-auto py-1"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-6 w-6" />
            </Button>
          </div>

          <div className="flex items-center space-x-4">
            {user && (
              <div className="text-sm flex items-center">
                <span className="font-medium text-gray-900">{user.username}</span>
                {user.organization && (
                  <span className="ml-3 inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                    {user.organization.name}
                  </span>
                )}
              </div>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
