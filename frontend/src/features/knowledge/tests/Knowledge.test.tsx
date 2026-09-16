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

describe('Knowledge Page Search Controls & Grouping', () => {
  const mockGroupedResponse: SearchResponse = {
    query: 'test query',
    meta: { embedding_ms: 10, retrieval_ms: 20, total_ms: 30 },
    results: [
      { chunk_id: 1, document_id: 101, document_title: 'Doc A', content: 'Chunk A1', score: 0.9 },
      { chunk_id: 2, document_id: 101, document_title: 'Doc A', content: 'Chunk A2', score: 0.8 },
      { chunk_id: 3, document_id: 102, document_title: 'Doc B', content: 'Chunk B1', score: 0.75 },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial empty search state with default controls', () => {
    render(<Knowledge />);

    expect(screen.getByText('Semantic Search')).toBeTruthy();

    const limitInput = screen.getByLabelText(/Result Limit:/i) as HTMLInputElement;
    const similarityInput = screen.getByLabelText(/Min. Similarity:/i) as HTMLInputElement;

    expect(limitInput.value).toBe("5");
    expect(similarityInput.value).toBe("0");

    const searchBtn = screen.getByRole('button', { name: /Search/i });
    expect((searchBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('sends default search controls', async () => {
    (knowledgeApi.searchKnowledge as any).mockResolvedValueOnce(mockGroupedResponse);
    render(<Knowledge />);

    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'test query' } });

    const searchBtn = screen.getByRole('button', { name: /Search/i });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(knowledgeApi.searchKnowledge).toHaveBeenCalledWith({
        query: 'test query',
        limit: 5,
        min_similarity: 0
      });
    });
  });

  it('sends custom limit and min_similarity values', async () => {
    (knowledgeApi.searchKnowledge as any).mockResolvedValueOnce(mockGroupedResponse);
    render(<Knowledge />);

    const queryInput = screen.getByPlaceholderText(/Ask a question/i);
    const limitInput = screen.getByLabelText(/Result Limit:/i);
    const simInput = screen.getByLabelText(/Min. Similarity:/i);

    fireEvent.change(queryInput, { target: { value: 'test query' } });
    fireEvent.change(limitInput, { target: { value: '15' } });
    fireEvent.change(simInput, { target: { value: '0.7' } });

    const searchBtn = screen.getByRole('button', { name: /Search/i });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(knowledgeApi.searchKnowledge).toHaveBeenCalledWith({
        query: 'test query',
        limit: 15,
        min_similarity: 0.7
      });
    });
  });

  it('groups multiple chunks belonging to the same document and renders multiple documents', async () => {
    (knowledgeApi.searchKnowledge as any).mockResolvedValueOnce(mockGroupedResponse);
    render(<Knowledge />);

    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.click(screen.getByRole('button', { name: /Search/i }));

    await waitFor(() => {
      expect(screen.getByText('3 Results returned')).toBeTruthy();
    });

    // Group titles should render only once
    const docATitles = screen.getAllByText('Doc A');
    expect(docATitles.length).toBe(1);

    const docBTitles = screen.getAllByText('Doc B');
    expect(docBTitles.length).toBe(1);

    // All chunks should be rendered
    expect(screen.getByText('Chunk A1')).toBeTruthy();
    expect(screen.getByText('Chunk A2')).toBeTruthy();
    expect(screen.getByText('Chunk B1')).toBeTruthy();

    // Scores
    expect(screen.getByText('Score: 0.900')).toBeTruthy();
    expect(screen.getByText('Score: 0.800')).toBeTruthy();
    expect(screen.getByText('Score: 0.750')).toBeTruthy();

    // Execution metadata
    expect(screen.getByText('Retrieval: 20ms')).toBeTruthy();
    expect(screen.getByText('Total: 30ms')).toBeTruthy();
  });

  it('handles consecutive searches using updated query and controls', async () => {
    (knowledgeApi.searchKnowledge as any)
      .mockResolvedValueOnce(mockGroupedResponse)
      .mockResolvedValueOnce({
        ...mockGroupedResponse,
        query: 'new query',
        results: [{ chunk_id: 4, document_id: 103, document_title: 'Doc C', content: 'Chunk C1', score: 0.95 }]
      });

    render(<Knowledge />);

    const queryInput = screen.getByPlaceholderText(/Ask a question/i);
    const limitInput = screen.getByLabelText(/Result Limit:/i);
    const searchBtn = screen.getByRole('button', { name: /Search/i });

    // First search
    fireEvent.change(queryInput, { target: { value: 'test query' } });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(screen.getByText('3 Results returned')).toBeTruthy();
    });

    // Second search
    fireEvent.change(queryInput, { target: { value: 'new query' } });
    fireEvent.change(limitInput, { target: { value: '10' } });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(knowledgeApi.searchKnowledge).toHaveBeenLastCalledWith({
        query: 'new query',
        limit: 10,
        min_similarity: 0
      });
      expect(screen.getByText('1 Result returned')).toBeTruthy();
      expect(screen.getByText('Doc C')).toBeTruthy();
    });
  });

  it('prevents empty query submission', () => {
    render(<Knowledge />);

    const input = screen.getByPlaceholderText(/Ask a question/i);
    const searchBtn = screen.getByRole('button', { name: /Search/i });

    fireEvent.change(input, { target: { value: '   ' } });
    expect((searchBtn as HTMLButtonElement).disabled).toBe(true);
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

    expect(screen.queryByText(/Results returned/i)).toBeNull();
  });

  it('renders loading state correctly during search', async () => {
    // We want the promise to hang a bit to test the loading state
    let resolveSearch: any;
    const searchPromise = new Promise((resolve) => { resolveSearch = resolve; });
    (knowledgeApi.searchKnowledge as any).mockReturnValueOnce(searchPromise);

    render(<Knowledge />);

    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'test query' } });

    const searchBtn = screen.getByRole('button', { name: /Search/i });
    fireEvent.click(searchBtn);

    expect(screen.getByText(/Searching.../i)).toBeTruthy();
    expect((input as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText(/Result Limit:/i) as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText(/Min. Similarity:/i) as HTMLInputElement).disabled).toBe(true);

    // Resolve the promise to clean up
    resolveSearch({
      query: 'test query',
      meta: { embedding_ms: 10, retrieval_ms: 10, total_ms: 20 },
      results: []
    });

    await waitFor(() => {
      expect(screen.queryByText(/Searching.../i)).toBeNull();
    });
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
      expect(screen.getByText('0 Results returned')).toBeTruthy();
      expect(screen.getByText('No results found')).toBeTruthy();
      expect(screen.getByText(/We couldn't find any knowledge chunks/i)).toBeTruthy();
    });
  });
});
