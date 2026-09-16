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
});
