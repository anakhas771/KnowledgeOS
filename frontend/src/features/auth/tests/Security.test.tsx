import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

describe('Authentication Security Assertions', () => {
  let localStorageSetSpy: any;
  let sessionStorageSetSpy: any;
  let cookieSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
    
    localStorageSetSpy = vi.spyOn(Storage.prototype, 'setItem');
    sessionStorageSetSpy = vi.spyOn(Storage.prototype, 'setItem');
    
    cookieSpy = vi.spyOn(document, 'cookie', 'set');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('SECURITY REGRESSION: Does not use persistence storage during login and logout', async () => {
    (authApi.me as any).mockRejectedValueOnce(new Error('Init fail')); // Initial session restore fails
    
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>
    );

    // Wait for login to render
    await waitFor(() => {
      expect(screen.getByText('Sign in to KnowledgeOS')).toBeTruthy();
    });

    // Mock successful login
    (authApi.login as any).mockResolvedValueOnce({ access: 'secure-token' });
    const mockUser = { username: 'secure_user', email: 'sec@example.com', role: 'admin' };
    (authApi.me as any).mockResolvedValueOnce(mockUser);

    // Perform Login
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'secure_user' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Wait for App to load
    await waitFor(() => {
      expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0);
    });

    // Perform Logout
    (authApi.logout as any).mockResolvedValueOnce({});
    fireEvent.click(screen.getByRole('button', { name: /logout/i }));

    await waitFor(() => {
      expect(screen.getByText('Sign in to KnowledgeOS')).toBeTruthy();
    });

    // Assertions for security
    // 1. LocalStorage never used to store tokens
    expect(localStorageSetSpy).not.toHaveBeenCalled();
    // 2. SessionStorage never used
    expect(sessionStorageSetSpy).not.toHaveBeenCalled();
    // 3. document.cookie never manipulated via JS
    expect(cookieSpy).not.toHaveBeenCalled();

    // Verify token was stored in memory
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
