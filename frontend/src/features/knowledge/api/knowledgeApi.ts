import { apiClient } from '../../../lib/apiClient';
import type { SearchResponse, SearchParams } from '../types';

export const knowledgeApi = {
  searchKnowledge: async (params: SearchParams): Promise<SearchResponse> => {
    const response = await apiClient.post<SearchResponse>('/api/v1/knowledge/search/', params);
    return response.data;
  },
};
