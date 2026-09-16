import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Documents from '../../../pages/Documents';
import { documentsApi } from '../api/documentsApi';
import type { Document } from '../types';

// Mock the API client
vi.mock('../api/documentsApi', () => ({
  documentsApi: {
    getDocuments: vi.fn(),
    uploadDocument: vi.fn(),
  }
}));

describe('Documents Page', () => {
  const mockDocuments: Document[] = [
    {
      id: 1,
      organization: 1,
      title: 'First Document',
      file: 'first.txt',
      file_type: 'text/plain',
      file_size: 1024,
      status: 'completed',
      uploaded_by: 1,
      chunk_count: 5,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially and then the document list', async () => {
    (documentsApi.getDocuments as any).mockResolvedValueOnce(mockDocuments);
    
    render(<Documents />);
    
    // Title is present
    expect(screen.getByText('Upload Document')).toBeTruthy();
    
    // Wait for documents to load
    await waitFor(() => {
      expect(screen.getByText('First Document')).toBeTruthy();
      expect(screen.getByText('completed')).toBeTruthy();
    });
  });

  it('shows empty state when no documents exist', async () => {
    (documentsApi.getDocuments as any).mockResolvedValueOnce([]);
    
    render(<Documents />);
    
    await waitFor(() => {
      expect(screen.getByText('No documents')).toBeTruthy();
    });
  });

  it('upload button is disabled when no file is selected', async () => {
    (documentsApi.getDocuments as any).mockResolvedValueOnce([]);
    
    render(<Documents />);
    await waitFor(() => expect(screen.getByText('No documents')).toBeTruthy());
    
    const uploadBtn = screen.getByRole('button', { name: /Upload/i });
    expect((uploadBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('handles client-side validation for invalid file extension', async () => {
    (documentsApi.getDocuments as any).mockResolvedValueOnce([]);
    
    render(<Documents />);
    await waitFor(() => expect(screen.getByText('No documents')).toBeTruthy());
    
    // Set title
    const titleInput = screen.getByLabelText(/Document Title/i);
    fireEvent.change(titleInput, { target: { value: 'Bad File' } });
    
    // Set invalid file
    const fileInput = screen.getByLabelText(/File/i);
    const file = new File(['hello'], 'script.sh', { type: 'application/x-sh' });
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    const uploadBtn = screen.getByRole('button', { name: /Upload/i });
    fireEvent.click(uploadBtn);
    
    await waitFor(() => {
      expect(screen.getByText(/Unsupported file extension/i)).toBeTruthy();
    });
  });

  it('successfully uploads and refreshes document list', async () => {
    (documentsApi.getDocuments as any)
      .mockResolvedValueOnce([]) // initial load
      .mockResolvedValueOnce([   // after upload
        {
          id: 2,
          organization: 1,
          title: 'My Uploaded Doc',
          file: 'upload.txt',
          file_type: 'text/plain',
          file_size: 200,
          status: 'uploaded',
          uploaded_by: 1,
          chunk_count: 0,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z',
        }
      ]);
      
    (documentsApi.uploadDocument as any).mockResolvedValueOnce({});
    
    render(<Documents />);
    await waitFor(() => expect(screen.getByText('No documents')).toBeTruthy());
    
    const titleInput = screen.getByLabelText(/Document Title/i);
    fireEvent.change(titleInput, { target: { value: 'My Uploaded Doc' } });
    
    const fileInput = screen.getByLabelText(/File/i);
    const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    const uploadBtn = screen.getByRole('button', { name: /Upload/i });
    fireEvent.click(uploadBtn);
    
    await waitFor(() => {
      expect(screen.getByText('Document uploaded successfully!')).toBeTruthy();
      expect(screen.getByText('My Uploaded Doc')).toBeTruthy();
      expect(screen.getByText('uploaded')).toBeTruthy();
    });
    
    expect(documentsApi.uploadDocument).toHaveBeenCalledWith('My Uploaded Doc', file);
    expect(documentsApi.getDocuments).toHaveBeenCalledTimes(2); // Initial + after upload
  });

  it('handles API upload error', async () => {
    (documentsApi.getDocuments as any).mockResolvedValueOnce([]);
    (documentsApi.uploadDocument as any).mockRejectedValueOnce({
      response: { data: { detail: 'Server error during upload' } }
    });
    
    render(<Documents />);
    await waitFor(() => expect(screen.getByText('No documents')).toBeTruthy());
    
    const titleInput = screen.getByLabelText(/Document Title/i);
    fireEvent.change(titleInput, { target: { value: 'Will Fail' } });
    
    const fileInput = screen.getByLabelText(/File/i);
    const file = new File(['hello'], 'fail.txt', { type: 'text/plain' });
    fireEvent.change(fileInput, { target: { files: [file] } });
    
    const uploadBtn = screen.getByRole('button', { name: /Upload/i });
    fireEvent.click(uploadBtn);
    
    await waitFor(() => {
      expect(screen.getByText('Server error during upload')).toBeTruthy();
    });
  });
});
