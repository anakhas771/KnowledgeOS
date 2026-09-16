import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

interface FailedRequest {
  resolve: (value: string) => void;
  reject: (reason?: any) => void;
}

let isRefreshing = false;
let failedQueue: FailedRequest[] = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token as string);
    }
  });
  failedQueue = [];
};

export const refreshTokenHelper = (): Promise<string> => {
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      failedQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;

  return new Promise(async (resolve, reject) => {
    try {
      const { data } = await axios.post(
        `${API_BASE_URL}/api/v1/auth/refresh/`,
        {},
        { withCredentials: true }
      );

      const newAccessToken = data.access;
      // Keep the existing user profile but update token
      const currentUser = useAuthStore.getState().user;
      if (currentUser) {
          useAuthStore.getState().setAuth(currentUser, newAccessToken);
      }

      apiClient.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;

      resolve(newAccessToken);
      processQueue(null, newAccessToken);
    } catch (err) {
      processQueue(err, null);
      useAuthStore.getState().clearAuth();
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
          window.location.href = '/login';
      }
      reject(err);
    } finally {
      isRefreshing = false;
    }
  });
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/api/v1/auth/refresh/') {
      originalRequest._retry = true;

      try {
        const token = await refreshTokenHelper();
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return apiClient(originalRequest);
      } catch (err) {
        return Promise.reject(err);
      }
    }
    return Promise.reject(error);
  }
);

