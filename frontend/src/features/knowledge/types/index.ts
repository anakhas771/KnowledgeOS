export interface SearchResultChunk {
  chunk_id: number;
  document_id: number;
  document_title: string;
  content: string;
  score: number;
}

export interface SearchMeta {
  embedding_ms: number;
  retrieval_ms: number;
  total_ms: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResultChunk[];
  meta: SearchMeta;
}

export interface SearchParams {
  query: string;
  limit?: number;
  min_similarity?: number;
}

// Copilot RAG Types
export interface AskRequest {
  query: string;
}

export interface RAGSource {
  chunk_id: number;
  document_id: number;
  document_title: string;
  score: number;
}

export interface RAGMetrics {
  ttft_ms: number | null;
  generation_ms: number;
  total_ms: number;
  token_count: number;
}

export interface RAGDoneEvent {
  type: 'done';
  sources: RAGSource[];
  metrics: RAGMetrics;
}

export interface RAGErrorEvent {
  type: 'error';
  message: string;
}
