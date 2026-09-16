import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router';
import App from '../../../App';
import { authApi } from '../api/authApi';
import { useAuthStore } from '../../../store/authStore';

vi.mock('../api/authApi', () => ({
  authApi: {
    me: vi.fn(),
    logout: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
  },
}));

describe('App & Protected Routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
    // Start with loading true since App's useEffect handles it
    useAuthStore.getState().setLoading(true);
  });

  it('TEST 4: Protected Route - unauthenticated redirects to /login', async () => {
    (authApi.me as any).mockRejectedValueOnce(new Error('Unauthorized'));

    render(
      <MemoryRouter initialEntries={['/app']}>
        <App />
      </MemoryRouter>
    );

    // Should initially show loading
    expect(screen.getByText('Loading session...')).toBeTruthy();

    // After me() fails, it clears auth and redirects to login
    await waitFor(() => {
      expect(screen.getByText('Sign in to KnowledgeOS')).toBeTruthy();
    });
  });

  it('TEST 4: Protected Route - authenticated allows access', async () => {
    const mockUser = { username: 'john_doe', email: 'john@example.com', role: 'admin' };
    useAuthStore.getState().setAuth(mockUser as any, 'fake-token');

    // App mount calls me()
    (authApi.me as any).mockResolvedValueOnce(mockUser);

    render(
      <MemoryRouter initialEntries={['/app']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeTruthy();
      expect(screen.getByText('john_doe')).toBeTruthy();
    });
  });

  it('TEST 5: Session Restoration - success', async () => {
    const mockUser = { username: 'restored_user', email: 'restored@example.com', role: 'user' };
    (authApi.me as any).mockResolvedValueOnce(mockUser);

    render(
      <MemoryRouter initialEntries={['/app']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(authApi.me).toHaveBeenCalledTimes(1);
      // Protected content rendered
      expect(screen.getByText('restored_user')).toBeTruthy();
    });
    
    // Auth state updated
    expect(useAuthStore.getState().user?.username).toBe('restored_user');
  });

  it('TEST 5: Session Restoration - failure', async () => {
    (authApi.me as any).mockRejectedValueOnce(new Error('Session expired'));

    render(
      <MemoryRouter initialEntries={['/app']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Directed to login
      expect(screen.getByText('Sign in to KnowledgeOS')).toBeTruthy();
    });

    expect(useAuthStore.getState().user).toBeNull();
  });

  it('TEST 6: Logout - clears store and navigates', async () => {
    const mockUser = { username: 'testuser', email: 'test@example.com', role: 'admin' };
    useAuthStore.getState().setAuth(mockUser as any, 'fake-token');
    (authApi.me as any).mockResolvedValueOnce(mockUser);
    (authApi.logout as any).mockResolvedValueOnce({});

    render(
      <MemoryRouter initialEntries={['/app']}>
        <App />
      </MemoryRouter>
    );

    // Wait for App load
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeTruthy();
    });

    // Click logout
    fireEvent.click(screen.getByRole('button', { name: /logout/i }));

    await waitFor(() => {
      expect(authApi.logout).toHaveBeenCalledTimes(1);
      // Redirected to login
      expect(screen.getByText('Sign in to KnowledgeOS')).toBeTruthy();
    });

    // Store is cleared
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
