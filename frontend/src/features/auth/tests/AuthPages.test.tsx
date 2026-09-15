import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router';
import Login from '../../../pages/Login';
import Register from '../../../pages/Register';
import { authApi } from '../api/authApi';
import { useAuthStore } from '../../../store/authStore';

// Mock authApi
vi.mock('../api/authApi', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    me: vi.fn(),
  },
}));

// Mock component to verify navigation
const MockApp = () => <div>App Page</div>;

describe('Authentication Pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
  });

  it('TEST 1: Login Success - updates store and navigates', async () => {
    (authApi.login as any).mockResolvedValueOnce({ access: 'mock-access-token' });
    (authApi.me as any).mockResolvedValueOnce({ username: 'testuser' });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/app" element={<MockApp />} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'password123' } });
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({ username: 'testuser', password: 'password123' });
      expect(authApi.me).toHaveBeenCalled();
    });

    // Check store
    expect(useAuthStore.getState().accessToken).toBe('mock-access-token');
    expect(useAuthStore.getState().user?.username).toBe('testuser');

    // Check navigation
    expect(await screen.findByText('App Page')).toBeTruthy();
  });

  it('TEST 2: Login Failure - shows error, clears state, no navigation', async () => {
    (authApi.login as any).mockRejectedValueOnce({
      response: { data: { detail: 'Invalid credentials' } }
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/app" element={<MockApp />} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'wronguser' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'wrongpass' } });
    
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Wait for error to appear
    expect(await screen.findByText('Invalid credentials')).toBeTruthy();

    // Check store
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();

    // Check we are not navigated
    expect(screen.queryByText('App Page')).toBeNull();
  });

  it('TEST 3: Registration Success - calls API with proper payload and navigates', async () => {
    (authApi.register as any).mockResolvedValueOnce({});

    render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Organization Name'), { target: { value: 'Acme Corp' } });
    fireEvent.change(screen.getByPlaceholderText('Organization Slug (e.g. acme-corp)'), { target: { value: 'acme' } });
    fireEvent.change(screen.getByPlaceholderText('Email Address'), { target: { value: 'admin@acme.com' } });
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'admin' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'pass123' } });
    
    fireEvent.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalledWith({
        organization_name: 'Acme Corp',
        organization_slug: 'acme',
        email: 'admin@acme.com',
        username: 'admin',
        password: 'pass123'
      });
    });

    // Verify navigation
    expect(await screen.findByText('Login Page')).toBeTruthy();
  });

  it('TEST 3: Registration Failure - displays validation errors', async () => {
    (authApi.register as any).mockRejectedValueOnce({
      response: { data: { username: ['This field must be unique.'] } }
    });

    render(
      <MemoryRouter initialEntries={['/register']}>
        <Register />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Organization Name'), { target: { value: 'Acme Corp' } });
    fireEvent.change(screen.getByPlaceholderText('Organization Slug (e.g. acme-corp)'), { target: { value: 'acme' } });
    fireEvent.change(screen.getByPlaceholderText('Email Address'), { target: { value: 'admin@acme.com' } });
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'existing_admin' } });
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'pass123' } });

    fireEvent.click(screen.getByRole('button', { name: /register/i }));

    const errorStr = JSON.stringify({ username: ['This field must be unique.'] });
    expect(await screen.findByText(errorStr)).toBeTruthy();
  });
});
