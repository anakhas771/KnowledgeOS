import { apiClient } from '../../../lib/apiClient';

export const authApi = {
  login: async (credentials: any) => {
    const response = await apiClient.post('/api/v1/auth/login/', credentials);
    return response.data;
  },
  register: async (data: any) => {
    const response = await apiClient.post('/api/v1/auth/register/', data);
    return response.data;
  },
  me: async () => {
    const response = await apiClient.get('/api/v1/auth/me/');
    return response.data;
  },
  logout: async () => {
    const response = await apiClient.post('/api/v1/auth/logout/');
    return response.data;
  }
};
