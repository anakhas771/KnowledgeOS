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

export interface ChunkEvidence {
  chunk_id: number;
  document_id: number;
  document_title: string;
  content: string;
}

export interface SearchParams {
  query: string;
  limit?: number;
  min_similarity?: number;
}

// Copilot RAG Types
export interface AskRequest {
  query: string;
  conversation_id?: number | null;
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
  conversation_id: number;
  sources: RAGSource[];
  metrics: RAGMetrics;
}

export interface RAGErrorEvent {
  type: 'error';
  message: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}
