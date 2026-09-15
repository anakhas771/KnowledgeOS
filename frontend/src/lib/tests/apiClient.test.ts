import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import { apiClient } from '../apiClient';
import { useAuthStore } from '../../store/authStore';

// Mock axios.post for the refresh endpoint
vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal<typeof import('axios')>();
  return {
    default: {
      ...actual.default,
      post: vi.fn(),
      create: actual.default.create,
    },
  };
});

describe('apiClient Interceptors', () => {
  let adapterMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    adapterMock = vi.fn();
    apiClient.defaults.adapter = adapterMock as any;
    useAuthStore.getState().clearAuth();
    vi.clearAllMocks();
    
    // Prevent window.location.href from actually navigating during tests
    Object.defineProperty(window, 'location', {
      value: { pathname: '/app', href: '/app' },
      writable: true
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('TEST 7: Axios Refresh Interceptor - exact once, retry once, updates token', async () => {
    // Setup state
    useAuthStore.getState().setAuth({ username: 'testuser' } as any, 'old-token');

    // Adapter responds with 401 first, then 200 on retry
    adapterMock
      .mockRejectedValueOnce({
        config: { url: '/protected', headers: {} },
        response: { status: 401 }
      })
      .mockResolvedValueOnce({
        status: 200,
        data: 'success'
      });

    // Mock the refresh endpoint to succeed
    (axios.post as any).mockResolvedValueOnce({
      data: { access: 'new-token' }
    });

    const response = await apiClient.get('/protected');

    expect(response.data).toBe('success');
    expect(axios.post).toHaveBeenCalledTimes(1);
    expect(adapterMock).toHaveBeenCalledTimes(2);
    
    // Check if new token replaced old one
    expect(useAuthStore.getState().accessToken).toBe('new-token');
    
    // Check if retry request had the new token
    const retryCall = adapterMock.mock.calls[1][0];
    expect(retryCall.headers.Authorization).toBe('Bearer new-token');
  });

  it('TEST 7: Axios Refresh Interceptor - fails, clears auth, redirects', async () => {
    useAuthStore.getState().setAuth({ username: 'testuser' } as any, 'old-token');

    adapterMock.mockRejectedValueOnce({
      config: { url: '/protected', headers: {} },
      response: { status: 401 }
    });

    (axios.post as any).mockRejectedValueOnce(new Error('Refresh failed'));

    await expect(apiClient.get('/protected')).rejects.toThrow();

    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  it('TEST 8: Concurrent 401 requests trigger refresh exactly once', async () => {
    useAuthStore.getState().setAuth({ username: 'testuser' } as any, 'old-token');

    // Both initial requests fail with 401
    adapterMock
      .mockRejectedValueOnce({
        config: { url: '/protected-1', headers: {} },
        response: { status: 401 }
      })
      .mockRejectedValueOnce({
        config: { url: '/protected-2', headers: {} },
        response: { status: 401 }
      })
      // Both retries succeed
      .mockResolvedValueOnce({ status: 200, data: 'success-1' })
      .mockResolvedValueOnce({ status: 200, data: 'success-2' });

    // Refresh succeeds once
    (axios.post as any).mockImplementationOnce(() => {
      return new Promise((resolve) => {
        setTimeout(() => resolve({ data: { access: 'new-concurrent-token' } }), 50);
      });
    });

    // Fire two requests concurrently
    const [res1, res2] = await Promise.all([
      apiClient.get('/protected-1'),
      apiClient.get('/protected-2')
    ]);

    expect(res1.data).toBe('success-1');
    expect(res2.data).toBe('success-2');
    
    // Refresh should only be called ONCE
    expect(axios.post).toHaveBeenCalledTimes(1);
    
    // Adapter called 4 times (2 initial fails, 2 retries)
    expect(adapterMock).toHaveBeenCalledTimes(4);
    expect(useAuthStore.getState().accessToken).toBe('new-concurrent-token');
  });
});
