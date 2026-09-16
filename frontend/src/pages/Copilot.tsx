import { useState, useRef, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { Bot, Send, AlertCircle, FileText, Loader2, StopCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { knowledgeApi } from '../features/knowledge/api/knowledgeApi';
import type { RAGSource, RAGMetrics } from '../features/knowledge/types';

export default function Copilot() {
  const [query, setQuery] = useState('');
  const [currentQuery, setCurrentQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<RAGSource[] | null>(null);
  const [metrics, setMetrics] = useState<RAGMetrics | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of answer as it generates
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [answer]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleAsk = async () => {
    if (!query.trim() || isGenerating) return;

    // Reset state for new query
    setCurrentQuery(query.trim());
    setAnswer('');
    setSources(null);
    setMetrics(null);
    setError(null);
    setIsGenerating(true);
    setQuery(''); // clear input box

    abortControllerRef.current = new AbortController();

    try {
      await knowledgeApi.askKnowledge(
        { query: query.trim() },
        // onToken
        (token) => {
          setAnswer((prev) => prev + token);
        },
        // onDone
        (event) => {
          setIsGenerating(false);
          // Deduplicate sources by document_id
          const uniqueSourcesMap = new Map<number, RAGSource>();
          event.sources.forEach((source) => {
            if (!uniqueSourcesMap.has(source.document_id)) {
              uniqueSourcesMap.set(source.document_id, source);
            }
          });
          setSources(Array.from(uniqueSourcesMap.values()));
          setMetrics(event.metrics);
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
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-4xl flex-col rounded-lg border bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center space-x-3 border-b bg-gray-50 px-6 py-4">
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

      {/* Main Conversation Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-6"
      >
        {!currentQuery && !error && !answer && (
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

        {/* User Query */}
        {currentQuery && (
          <div className="flex justify-end">
            <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-blue-600 px-5 py-3 text-white shadow-sm">
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{currentQuery}</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex justify-start">
            <div className="flex max-w-[80%] items-start space-x-3 rounded-2xl rounded-tl-sm bg-red-50 p-4 border border-red-100">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-500 mt-0.5" />
              <p className="text-sm text-red-800 whitespace-pre-wrap">{error}</p>
            </div>
          </div>
        )}

        {/* Assistant Response */}
        {answer && (
          <div className="flex justify-start">
            <div className="max-w-[90%] rounded-2xl rounded-tl-sm bg-gray-50 px-5 py-4 border border-gray-100">
              <div className="prose prose-sm prose-blue max-w-none text-gray-800 whitespace-pre-wrap leading-relaxed">
                {answer}
                {isGenerating && <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-blue-500 rounded-sm" />}
              </div>

              {/* Sources */}
              {sources && sources.length > 0 && (
                <div className="mt-6 border-t border-gray-200 pt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3 flex items-center">
                    <FileText className="w-3 h-3 mr-1" /> Sources Used
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {sources.map((src) => (
                      <div 
                        key={src.document_id} 
                        className="inline-flex items-center rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700"
                      >
                        <span className="truncate max-w-[200px]">{src.document_title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metrics */}
              {metrics && (
                <div className="mt-4 flex flex-wrap gap-4 text-[11px] font-medium text-gray-400">
                  {metrics.ttft_ms !== null && <span>TTFT: {metrics.ttft_ms}ms</span>}
                  <span>Gen: {metrics.generation_ms}ms</span>
                  <span>Total: {metrics.total_ms}ms</span>
                  <span>Tokens: {metrics.token_count}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty Loading State (before first token) */}
        {isGenerating && !answer && !error && (
          <div className="flex justify-start">
            <div className="flex max-w-[80%] items-center space-x-3 rounded-2xl rounded-tl-sm bg-gray-50 px-5 py-4 border border-gray-100 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm font-medium">Analyzing knowledge...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t bg-white p-4">
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
  );
}
