import { useState, useRef, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { Bot, Send, AlertCircle, FileText, Loader2, StopCircle, Plus, MessageSquare } from 'lucide-react';
import { Button } from '../components/ui/button';
import { knowledgeApi } from '../features/knowledge/api/knowledgeApi';
import type { RAGSource, RAGMetrics, Conversation, Message } from '../features/knowledge/types';

export default function Copilot() {
  const [query, setQuery] = useState('');

  const renderTextWithCitations = (text: string, sources: RAGSource[] | null) => {
    if (!text) return null;

    // Split by [Source N]
    const parts = text.split(/\[Source (\d+)\]/g);

    return parts.map((part, index) => {
      // Even indices are regular text, odd indices are the captured source number
      if (index % 2 === 0) {
        return <span key={index}>{part}</span>;
      }

      const sourceNum = parseInt(part, 10);

      // If we don't have sources or the number is invalid, render as plain text
      if (!sources || isNaN(sourceNum) || sourceNum < 1 || sourceNum > sources.length) {
        return <span key={index}>[Source {part}]</span>;
      }

      const source = sources[sourceNum - 1];

      return (
        <span
          key={index}
          className="inline-flex items-center justify-center bg-blue-100 text-blue-800 text-xs font-bold px-1.5 py-0.5 rounded mx-1 cursor-help relative group"
          title={source.document_title}
        >
          {sourceNum}
          <div className="absolute bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-gray-900 text-white text-[10px] font-normal rounded shadow-lg z-10 whitespace-normal break-words leading-tight">
            {source.document_title}
            {source.score !== undefined && <span className="block text-gray-400 mt-1">Relevance: {(source.score * 100).toFixed(1)}%</span>}
          </div>
        </span>
      );
    });
  };

  // Conversations List
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);

  // Current Conversation State
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingAnswer, setStreamingAnswer] = useState('');

  // RAG Metadata for the latest answer
  const [latestSources, setLatestSources] = useState<RAGSource[] | null>(null);
  const [latestMetrics, setLatestMetrics] = useState<RAGMetrics | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingAnswer]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await knowledgeApi.getConversations();
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations', err);
    }
  };

  const loadConversation = async (id: number) => {
    if (isGenerating) return;
    try {
      const conv = await knowledgeApi.getConversation(id);
      setActiveConversationId(conv.id);
      setMessages(conv.messages);
      setStreamingAnswer('');
      setLatestSources(null);
      setLatestMetrics(null);
      setError(null);
    } catch (err) {
      setError('Failed to load conversation.');
    }
  };

  const handleNewConversation = () => {
    if (isGenerating) return;
    setActiveConversationId(null);
    setMessages([]);
    setStreamingAnswer('');
    setLatestSources(null);
    setLatestMetrics(null);
    setError(null);
  };

  const handleAsk = async () => {
    if (!query.trim() || isGenerating) return;

    const currentQuery = query.trim();
    setQuery('');
    setError(null);
    setIsGenerating(true);
    setLatestSources(null);
    setLatestMetrics(null);
    setStreamingAnswer('');

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: currentQuery,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    abortControllerRef.current = new AbortController();

    try {
      await knowledgeApi.askKnowledge(
        {
          query: currentQuery,
          conversation_id: activeConversationId
        },
        // onToken
        (token) => {
          setStreamingAnswer((prev) => prev + token);
        },
        // onDone
        (event) => {
          setIsGenerating(false);

          // Store raw sources exactly as provided to preserve positional citation numbering
          setLatestSources(event.sources || []);
          setLatestMetrics(event.metrics);

          // Move streaming answer to messages
          setStreamingAnswer((finalAnswer) => {
            const newAssistantMsg: Message = {
              id: Date.now() + 1,
              role: 'assistant',
              content: finalAnswer,
              created_at: new Date().toISOString()
            };
            setMessages((prev) => [...prev, newAssistantMsg]);
            return '';
          });

          // Update active conversation ID and refresh list if new
          if (event.conversation_id && event.conversation_id !== activeConversationId) {
            setActiveConversationId(event.conversation_id);
            loadConversations();
          }
        },
        // onError (inline SSE error)
        (event) => {
          setIsGenerating(false);
          setError(event.message || 'An error occurred during generation.');
        },
        abortControllerRef.current.signal
      );
    } catch (err: any) {
      setIsGenerating(false);
      if (err.name === 'AbortError') {
        setError('Generation stopped by user.');
      } else {
        setError(
          err.response?.data?.detail ||
          err.response?.data?.query?.[0] ||
          'Failed to communicate with Copilot. Please try again later.'
        );
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-6xl rounded-lg border bg-white shadow-sm overflow-hidden">

      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 border-r bg-gray-50 flex flex-col hidden md:flex">
        <div className="p-4 border-b">
          <Button
            onClick={handleNewConversation}
            disabled={isGenerating}
            className="w-full justify-start space-x-2 bg-white text-gray-700 border hover:bg-gray-100 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            <span>New Chat</span>
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map(conv => (
            <button
              key={conv.id}
              onClick={() => loadConversation(conv.id)}
              disabled={isGenerating}
              className={`w-full text-left px-3 py-2 rounded-md text-sm truncate flex items-center space-x-2 ${
                activeConversationId === conv.id
                  ? 'bg-blue-100 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100 disabled:opacity-50'
              }`}
            >
              <MessageSquare className="h-4 w-4 flex-shrink-0" />
              <span className="truncate">{conv.title}</span>
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="text-xs text-gray-400 text-center mt-4">No recent chats.</p>
          )}
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Header */}
        <div className="flex items-center space-x-3 border-b px-6 py-4 flex-shrink-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
            <Bot className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-gray-900">KnowledgeOS Copilot</h1>
            <p className="text-sm text-gray-500">
              AI assistant grounded securely in your organization's indexed knowledge.
            </p>
          </div>
        </div>

        {/* Conversation Area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 space-y-6"
        >
          {messages.length === 0 && !streamingAnswer && !error && (
            <div className="flex h-full flex-col items-center justify-center space-y-4 text-center">
              <Bot className="h-16 w-16 text-gray-200" />
              <div className="max-w-md">
                <h3 className="text-lg font-medium text-gray-900">How can I help you?</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Ask a question about your documents, policies, or procedures. Copilot will synthesize an answer directly from your knowledge base.
                </p>
              </div>
            </div>
          )}

          {/* Render all messages */}
          {messages.map((msg, idx) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-sm'
                  : 'bg-gray-50 border border-gray-100 rounded-tl-sm text-gray-800'
              }`}>
                <div className={`whitespace-pre-wrap ${msg.role === 'user' ? 'text-sm' : 'prose prose-sm prose-blue max-w-none'} leading-relaxed`}>
                  {msg.role === 'assistant' && idx === messages.length - 1
                    ? renderTextWithCitations(msg.content, latestSources)
                    : renderTextWithCitations(msg.content, null)}
                </div>

                {/* Append sources/metrics ONLY to the LAST assistant message in the list if they are available */}
                {msg.role === 'assistant' && idx === messages.length - 1 && latestSources && (
                  <>
                    <div className="mt-6 border-t border-gray-200 pt-4">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3 flex items-center">
                        <FileText className="w-3 h-3 mr-1" /> Sources Used
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {Array.from(new Map(latestSources.map((s) => [s.document_id, s])).values()).map((src) => (
                          <div
                            key={src.document_id}
                            className="inline-flex items-center rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700"
                          >
                            <span className="truncate max-w-[200px]">{src.document_title}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    {latestMetrics && (
                      <div className="mt-4 flex flex-wrap gap-4 text-[11px] font-medium text-gray-400">
                        {latestMetrics.ttft_ms !== null && <span>TTFT: {latestMetrics.ttft_ms}ms</span>}
                        <span>Gen: {latestMetrics.generation_ms}ms</span>
                        <span>Total: {latestMetrics.total_ms}ms</span>
                        <span>Tokens: {latestMetrics.token_count}</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}

          {/* Streaming Answer */}
          {streamingAnswer && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-gray-50 px-5 py-4 border border-gray-100">
                <div className="prose prose-sm prose-blue max-w-none text-gray-800 whitespace-pre-wrap leading-relaxed">
                  {renderTextWithCitations(streamingAnswer, latestSources)}
                  <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-blue-500 rounded-sm" />
                </div>
              </div>
            </div>
          )}

          {/* Empty Loading State (before first token) */}
          {isGenerating && !streamingAnswer && !error && (
            <div className="flex justify-start">
              <div className="flex max-w-[85%] items-center space-x-3 rounded-2xl rounded-tl-sm bg-gray-50 px-5 py-4 border border-gray-100 text-gray-500">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm font-medium">Analyzing knowledge...</span>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex justify-start">
              <div className="flex max-w-[85%] items-start space-x-3 rounded-2xl rounded-tl-sm bg-red-50 p-4 border border-red-100">
                <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-500 mt-0.5" />
                <p className="text-sm text-red-800 whitespace-pre-wrap">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t bg-white p-4 flex-shrink-0">
          <div className="relative flex items-end overflow-hidden rounded-xl border border-gray-300 bg-white shadow-sm focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
            <textarea
              rows={1}
              className="block w-full resize-none border-0 bg-transparent py-3 pl-4 pr-12 text-sm text-gray-900 placeholder:text-gray-400 focus:ring-0 max-h-32"
              placeholder="Ask a question..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                // Auto-resize
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
              }}
              onKeyDown={handleKeyDown}
              disabled={isGenerating}
            />
            <div className="absolute bottom-2 right-2 flex items-center">
              {isGenerating ? (
                <Button
                  type="button"
                  onClick={stopGeneration}
                  className="bg-transparent shadow-none h-8 w-8 p-0 text-red-500 hover:bg-red-50 hover:text-red-600 rounded-full"
                  title="Stop generation"
                >
                  <StopCircle className="h-5 w-5" />
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={handleAsk}
                  disabled={!query.trim()}
                  className="bg-transparent shadow-none h-8 w-8 p-0 text-blue-600 hover:bg-blue-50 rounded-full disabled:text-gray-300 disabled:hover:bg-transparent"
                >
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
          <div className="mt-2 text-center text-xs text-gray-400">
            Copilot can make mistakes. Check important info. Shift+Enter for new line.
          </div>
        </div>
      </div>
    </div>
  );
}
