import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Knowledge from '../../../pages/Knowledge';
import { knowledgeApi } from '../api/knowledgeApi';
import type { SearchResponse } from '../types';

vi.mock('../api/knowledgeApi', () => ({
  knowledgeApi: {
    searchKnowledge: vi.fn(),
  }
}));

describe('Knowledge Page', () => {
  const mockSearchResponse: SearchResponse = {
    query: 'test query',
    meta: {
      embedding_ms: 10,
      retrieval_ms: 20,
      total_ms: 30,
    },
    results: [
      {
        chunk_id: 1,
        document_id: 101,
        document_title: 'Test Document.pdf',
        content: 'This is a test chunk content that should be rendered.',
        score: 0.892,
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial empty search state', () => {
    render(<Knowledge />);
    
    expect(screen.getByText('Semantic Search')).toBeTruthy();
    expect(screen.getByText(/Enter a query above/i)).toBeTruthy();
    
    const searchBtn = screen.getByRole('button', { name: /Search/i });
    expect((searchBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('prevents empty query submission and enables button only when there is text', () => {
    render(<Knowledge />);
    
    const input = screen.getByPlaceholderText(/Ask a question/i);
    const searchBtn = screen.getByRole('button', { name: /Search/i });
    
    expect((searchBtn as HTMLButtonElement).disabled).toBe(true);
    
    fireEvent.change(input, { target: { value: '   ' } });
    expect((searchBtn as HTMLButtonElement).disabled).toBe(true);
    
    fireEvent.change(input, { target: { value: 'test query' } });
    expect((searchBtn as HTMLButtonElement).disabled).toBe(false);
  });

  it('handles successful search and renders results', async () => {
    (knowledgeApi.searchKnowledge as any).mockResolvedValueOnce(mockSearchResponse);
    
    render(<Knowledge />);
    
    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'test query' } });
    
    const searchBtn = screen.getByRole('button', { name: /Search/i });
    fireEvent.click(searchBtn);
    
    // Loading state check
    expect(screen.getByText(/Searching.../i)).toBeTruthy();
    expect((input as HTMLInputElement).disabled).toBe(true);
    
    await waitFor(() => {
      expect(screen.getByText('1 Result')).toBeTruthy();
    });
    
    expect(screen.getByText('Test Document.pdf')).toBeTruthy();
    expect(screen.getByText('This is a test chunk content that should be rendered.')).toBeTruthy();
    expect(screen.getByText('Score: 0.892')).toBeTruthy();
    
    expect(knowledgeApi.searchKnowledge).toHaveBeenCalledWith({ query: 'test query' });
  });

  it('handles submission via Enter key', async () => {
    (knowledgeApi.searchKnowledge as any).mockResolvedValueOnce(mockSearchResponse);
    
    render(<Knowledge />);
    
    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'test query' } });
    
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('1 Result')).toBeTruthy();
    });
    
    expect(knowledgeApi.searchKnowledge).toHaveBeenCalledTimes(1);
  });

  it('handles API error state properly', async () => {
    (knowledgeApi.searchKnowledge as any).mockRejectedValueOnce({
      response: { data: { detail: 'Server unavailable' } }
    });
    
    render(<Knowledge />);
    
    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'test query' } });
    
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('Server unavailable')).toBeTruthy();
    });
    
    // Results shouldn't show
    expect(screen.queryByText('1 Result')).toBeNull();
  });

  it('renders no-results state properly', async () => {
    (knowledgeApi.searchKnowledge as any).mockResolvedValueOnce({
      query: 'fake',
      meta: { embedding_ms: 0, retrieval_ms: 0, total_ms: 0 },
      results: []
    });
    
    render(<Knowledge />);
    
    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'fake' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('0 Results')).toBeTruthy();
      expect(screen.getByText('No results found')).toBeTruthy();
      expect(screen.getByText(/We couldn't find any knowledge chunks/i)).toBeTruthy();
    });
  });
});
