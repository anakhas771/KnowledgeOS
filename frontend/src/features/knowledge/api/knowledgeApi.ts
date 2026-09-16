import { apiClient } from '../../../lib/apiClient';
import { useAuthStore } from '../../../store/authStore';
import type { SearchResponse, SearchParams, AskRequest, RAGDoneEvent, RAGErrorEvent } from '../types';

export const knowledgeApi = {
  searchKnowledge: async (params: SearchParams): Promise<SearchResponse> => {
    const response = await apiClient.post<SearchResponse>('/api/v1/knowledge/search/', params);
    return response.data;
  },

  askKnowledge: async (
    request: AskRequest,
    onToken: (token: string) => void,
    onDone: (event: RAGDoneEvent) => void,
    onError: (event: RAGErrorEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

    const response = await fetch(`${baseUrl}/api/v1/knowledge/ask/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(request),
      signal
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => null);
      throw {
        response: {
          status: response.status,
          data: errData
        }
      };
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by the browser.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double newlines
        const parts = buffer.split('\n\n');

        // The last part might be incomplete, so keep it in the buffer
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;

          const payload = part.substring('data: '.length);

          try {
            // Try to parse as JSON first (done/error events)
            const jsonPayload = JSON.parse(payload);
            if (jsonPayload.type === 'done') {
              onDone(jsonPayload);
            } else if (jsonPayload.type === 'error') {
              onError(jsonPayload);
            } else {
              // Unknown JSON, fallback to raw token
              onToken(payload);
            }
          } catch (e) {
            // Not JSON, so it's a raw token string
            onToken(payload);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
};
