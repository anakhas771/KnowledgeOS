export type DocumentStatus = 'uploaded' | 'processing' | 'completed' | 'failed' | 'archived';

export interface Document {
  id: number;
  organization: number;
  title: string;
  file: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  uploaded_by: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}
