import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Copilot from '../../../pages/Copilot';
import { knowledgeApi } from '../api/knowledgeApi';

// Mock the API layer
vi.mock('../api/knowledgeApi', () => ({
  knowledgeApi: {
    askKnowledge: vi.fn(),
  }
}));

describe('Copilot UI Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders initial empty state', () => {
    render(<Copilot />);
    
    expect(screen.getByText('KnowledgeOS Copilot')).toBeTruthy();
    expect(screen.getByText('How can I help you?')).toBeTruthy();
    
    const input = screen.getByPlaceholderText('Ask a question...');
    expect(input).toBeTruthy();
    
    // Send button should be disabled initially
    const sendBtn = screen.getByRole('button');
    expect((sendBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('prevents empty query submission', () => {
    render(<Copilot />);
    
    const input = screen.getByPlaceholderText('Ask a question...');
    const sendBtn = screen.getByRole('button');
    
    fireEvent.change(input, { target: { value: '   ' } });
    expect((sendBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('handles successful generation with tokens and final done event', async () => {
    // Mock the askKnowledge implementation to simulate streaming
    (knowledgeApi.askKnowledge as any).mockImplementation(
      async (_req: any, onToken: any, onDone: any) => {
        // 1. Simulate tokens
        onToken('Hello');
        onToken(' World');
        
        // 2. Simulate done event with sources and metrics
        onDone({
          type: 'done',
          sources: [
            { chunk_id: 1, document_id: 101, document_title: 'Company Policy', score: 0.95 },
            { chunk_id: 2, document_id: 101, document_title: 'Company Policy', score: 0.90 }, // Duplicate doc
            { chunk_id: 3, document_id: 102, document_title: 'Employee Handbook', score: 0.85 }
          ],
          metrics: { ttft_ms: 50, generation_ms: 100, total_ms: 200, token_count: 2 }
        });
      }
    );

    render(<Copilot />);
    
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'What is the policy?' } });
    
    const sendBtn = screen.getByRole('button');
    fireEvent.click(sendBtn);

    // Verify loading state and input clear
    expect((input as HTMLTextAreaElement).value).toBe('');
    
    await waitFor(() => {
      // The user query should be displayed
      expect(screen.getByText('What is the policy?')).toBeTruthy();
      
      // The answer tokens should be assembled
      expect(screen.getByText('Hello World')).toBeTruthy();
      
      // The sources should be deduplicated (only one "Company Policy")
      const policyLabels = screen.getAllByText('Company Policy');
      expect(policyLabels.length).toBe(1);
      
      expect(screen.getByText('Employee Handbook')).toBeTruthy();
      
      // Metrics should render
      expect(screen.getByText('TTFT: 50ms')).toBeTruthy();
      expect(screen.getByText('Tokens: 2')).toBeTruthy();
    });
  });

  it('handles inline SSE error during generation', async () => {
    (knowledgeApi.askKnowledge as any).mockImplementation(
      async (_req: any, onToken: any, _onDone: any, onError: any) => {
        onToken('Partial answer');
        // Simulate stream error
        onError({
          type: 'error',
          message: 'AI generation service unavailable'
        });
      }
    );

    render(<Copilot />);
    
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Query' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      // Partial answer should still be visible
      expect(screen.getByText('Partial answer')).toBeTruthy();
      // Error message should be rendered
      expect(screen.getByText('AI generation service unavailable')).toBeTruthy();
    });
  });

  it('handles pre-stream API error', async () => {
    (knowledgeApi.askKnowledge as any).mockRejectedValueOnce({
      response: { data: { detail: 'Service down' } }
    });

    render(<Copilot />);
    
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Query' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByText('Service down')).toBeTruthy();
    });
  });

  it('allows starting a new query after completion', async () => {
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, onDone: any) => {
        onToken('First answer');
        onDone({ type: 'done', sources: [], metrics: { ttft_ms: 10, generation_ms: 20, total_ms: 30, token_count: 1 } });
      }
    );

    render(<Copilot />);
    
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'First query' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByText('First answer')).toBeTruthy();
    });

    // Setup mock for second query
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, onDone: any) => {
        onToken('Second answer');
        onDone({ type: 'done', sources: [], metrics: { ttft_ms: 10, generation_ms: 20, total_ms: 30, token_count: 1 } });
      }
    );

    fireEvent.change(input, { target: { value: 'Second query' } });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      // The first answer should be gone
      expect(screen.queryByText('First answer')).toBeNull();
      // The second query and answer should be visible
      expect(screen.getByText('Second query')).toBeTruthy();
      expect(screen.getByText('Second answer')).toBeTruthy();
    });
  });
});
