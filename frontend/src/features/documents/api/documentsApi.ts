import { apiClient } from '../../../lib/apiClient';
import type { Document } from '../types';

export const documentsApi = {
  getDocuments: async (): Promise<Document[]> => {
    const response = await apiClient.get('/api/v1/documents/');
    return response.data;
  },

  uploadDocument: async (title: string, file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('file', file);
    
    const response = await apiClient.post('/api/v1/documents/', formData);
    return response.data;
  },
};
