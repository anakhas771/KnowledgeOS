import { apiClient } from '../../../lib/apiClient';
import type { User } from '../../../store/authStore';

export interface LoginCredentials {
  username?: string;
  password?: string;
}

export interface RegisterPayload {
  organization_name?: string;
  email?: string;
  username?: string;
  password?: string;
}

export interface LoginResponse {
  access: string;
  user?: User;
}

export interface RegisterResponse {
  message: string;
  user: User;
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/v1/auth/login/', credentials);
    return response.data;
  },
  register: async (data: RegisterPayload): Promise<RegisterResponse> => {
    const response = await apiClient.post<RegisterResponse>('/api/v1/auth/register/', data);
    return response.data;
  },
  me: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/v1/auth/me/');
    return response.data;
  },
  logout: async (): Promise<{ detail: string }> => {
    const response = await apiClient.post<{ detail: string }>('/api/v1/auth/logout/');
    return response.data;
  }
};
