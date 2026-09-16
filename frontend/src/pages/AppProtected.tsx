import { useNavigate } from 'react-router';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../features/auth/api/authApi';
import { Button } from '../components/ui/button';

export default function AppProtected() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

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

  if (!user) {
    return null; // The ProtectedRoute wrapper should redirect us anyway
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl rounded-lg bg-white p-8 shadow">
        <div className="flex items-center justify-between border-b pb-4">
          <h1 className="text-2xl font-bold text-gray-900">KnowledgeOS Dashboard</h1>
          <Button onClick={handleLogout} className="bg-red-50 text-red-600 hover:bg-red-100 shadow-none">
            Logout
          </Button>
        </div>
        
        <div className="mt-8 space-y-6">
          <div>
            <h2 className="text-lg font-medium text-gray-900">Welcome, {user.username}</h2>
            <p className="text-gray-500">{user.email}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded border p-4">
              <p className="text-sm text-gray-500">Role</p>
              <p className="font-medium text-gray-900">{user.role}</p>
            </div>
            
            {user.organization && (
              <div className="rounded border p-4">
                <p className="text-sm text-gray-500">Organization</p>
                <p className="font-medium text-gray-900">{user.organization.name}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
