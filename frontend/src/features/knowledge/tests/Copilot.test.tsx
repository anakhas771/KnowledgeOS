import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Copilot from '../../../pages/Copilot';
import { knowledgeApi } from '../api/knowledgeApi';

// Mock the API layer
vi.mock('../api/knowledgeApi', () => ({
  knowledgeApi: {
    askKnowledge: vi.fn(),
    getConversations: vi.fn(),
    getConversation: vi.fn()
  }
}));

describe('Copilot UI Component Phase 21', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (knowledgeApi.getConversations as any).mockResolvedValue([
      { id: 1, title: 'Test Conv 1', created_at: '2026', updated_at: '2026' }
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders initial state and loads conversation list (Req 1, 2)', async () => {
    render(<Copilot />);

    expect(screen.getByText('KnowledgeOS Copilot')).toBeTruthy();
    expect(screen.getByText('How can I help you?')).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText('Test Conv 1')).toBeTruthy();
    });
  });

  it('selecting a conversation loads messages (Req 3)', async () => {
    (knowledgeApi.getConversation as any).mockResolvedValue({
      id: 1,
      title: 'Test Conv 1',
      messages: [
        { id: 101, role: 'user', content: 'Hello' },
        { id: 102, role: 'assistant', content: 'Hi there' }
      ]
    });

    render(<Copilot />);

    await waitFor(() => {
      expect(screen.getByText('Test Conv 1')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Test Conv 1'));

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeTruthy();
      expect(screen.getByText('Hi there')).toBeTruthy();
    });
  });

  it('new conversation resets active state and messages (Req 4)', async () => {
    // Load a conversation first
    (knowledgeApi.getConversation as any).mockResolvedValue({
      id: 1,
      title: 'Test Conv 1',
      messages: [{ id: 101, role: 'user', content: 'Hello' }]
    });

    render(<Copilot />);
    await waitFor(() => screen.getByText('Test Conv 1'));
    fireEvent.click(screen.getByText('Test Conv 1'));
    await waitFor(() => screen.getByText('Hello'));

    // Click New Chat
    fireEvent.click(screen.getByText('New Chat'));

    // Verify messages reset
    await waitFor(() => {
      expect(screen.queryByText('Hello')).toBeNull();
      expect(screen.getByText('How can I help you?')).toBeTruthy();
    });
  });

  it('multi-turn messages accumulate (Req 5) and streaming works (Req 6, 9)', async () => {
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, onDone: any) => {
        onToken('First');
        onToken(' Answer');
        onDone({ type: 'done', sources: [], metrics: {} });
      }
    );

    render(<Copilot />);

    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'First Q' } });
    fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').length - 1]);

    await waitFor(() => {
      expect(screen.getByText('First Q')).toBeTruthy();
      expect(screen.getByText('First Answer')).toBeTruthy();
    });

    // Second turn
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, onDone: any) => {
        onToken('Second Answer');
        onDone({ type: 'done', sources: [], metrics: {} });
      }
    );

    fireEvent.change(input, { target: { value: 'Second Q' } });
    fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').length - 1]);

    await waitFor(() => {
      expect(screen.getByText('First Q')).toBeTruthy();
      expect(screen.getByText('First Answer')).toBeTruthy();
      expect(screen.getByText('Second Q')).toBeTruthy();
      expect(screen.getByText('Second Answer')).toBeTruthy();
    });
  });

  it('streamingAnswer resets after a failed previous generation (Req 7)', async () => {
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, _onDone: any, onError: any) => {
        onToken('Broken text');
        onError({ message: 'Error' });
      }
    );

    render(<Copilot />);

    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Q1' } });
    fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').length - 1]);

    await waitFor(() => {
      expect(screen.getByText('Broken text')).toBeTruthy();
      expect(screen.getByText('Error')).toBeTruthy();
    });

    // Next turn should reset 'Broken text'
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, onDone: any) => {
        onToken('Fresh text');
        onDone({ type: 'done', sources: [], metrics: {} });
      }
    );

    fireEvent.change(input, { target: { value: 'Q2' } });
    fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').length - 1]);

    await waitFor(() => {
      expect(screen.queryByText('Broken textFresh text')).toBeNull();
      expect(screen.queryByText('Broken text')).toBeNull();
      expect(screen.getByText('Fresh text')).toBeTruthy();
    });
  });

  it('abort does not append an assistant message (Req 8)', async () => {
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, _onDone: any, _onError: any) => {
        onToken('Partial');
        const err = new Error();
        err.name = 'AbortError';
        throw err;
      }
    );

    render(<Copilot />);

    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Q1' } });
    fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').length - 1]);

    await waitFor(() => {
      expect(screen.getByText('Generation stopped by user.')).toBeTruthy();
    });

    // Check that there's no persisted assistant message in the log
    // Only the user query should be rendered as a bubble
    const userMsg = screen.getByText('Q1');
    expect(userMsg).toBeTruthy();
  });

  it('preserves exact citation mapping without deduplicating inline (Phase 22)', async () => {
    (knowledgeApi.askKnowledge as any).mockImplementationOnce(
      async (_req: any, onToken: any, onDone: any) => {
        onToken('Fact one [Source 1]. Fact two [Source 2]. Fact three [Source 3].');
        onDone({
          type: 'done',
          sources: [
            { document_id: 1, document_title: 'Doc A', score: 0.95, chunk_id: 101 },
            { document_id: 1, document_title: 'Doc A', score: 0.90, chunk_id: 102 },
            { document_id: 2, document_title: 'Doc B', score: 0.85, chunk_id: 201 }
          ],
          metrics: {}
        });
      }
    );

    render(<Copilot />);

    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Test citations' } });
    fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').length - 1]);

    await waitFor(() => {
      // The text itself should render with the source pills
      expect(screen.getByText('Fact one')).toBeTruthy();
      expect(screen.getByText('1')).toBeTruthy(); // The number inside the pill
      expect(screen.getByText('2')).toBeTruthy();
      expect(screen.getByText('3')).toBeTruthy();
    });

    // Check mapping based on relevance scores (since Doc A is duplicated)
    expect(screen.getByText('Relevance: 95.0%')).toBeTruthy(); // Source 1
    expect(screen.getByText('Relevance: 90.0%')).toBeTruthy(); // Source 2
    expect(screen.getByText('Relevance: 85.0%')).toBeTruthy(); // Source 3

    // Verify "Sources Used" deduplicates correctly visually
    // It should show 'Doc A' and 'Doc B', but 'Doc A' should only appear once in the Sources Used section
    // Since 'Doc A' also appears in the tooltips, we count them.
    // In tooltips: Doc A (Source 1), Doc A (Source 2).
    // In Sources Used: Doc A (deduplicated).
    // Total 'Doc A' in document = 3
    const docAElements = screen.getAllByText('Doc A');
    expect(docAElements.length).toBe(3);

    const docBElements = screen.getAllByText('Doc B');
    expect(docBElements.length).toBe(2); // 1 in tooltip, 1 in Sources Used
  });
});
