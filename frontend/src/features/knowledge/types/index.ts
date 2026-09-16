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
