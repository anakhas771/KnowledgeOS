import { useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Search, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { knowledgeApi } from '../features/knowledge/api/knowledgeApi';
import type { SearchResponse } from '../features/knowledge/types';

export default function Knowledge() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e?: FormEvent) => {
    if (e) e.preventDefault();

    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);

    try {
      const data = await knowledgeApi.searchKnowledge({ query: query.trim() });
      setResponse(data);
      setHasSearched(true);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.query?.[0] ||
        'Failed to search knowledge. Please try again later.'
      );
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Knowledge</h1>
        <p className="mt-1 text-sm text-gray-500">
          Search and explore your organization's indexed knowledge base.
        </p>
      </div>

      {/* Search Input Section */}
      <div className="rounded-lg border bg-white shadow-sm p-6">
        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative flex-grow">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
            </div>
            <input
              type="text"
              className="block w-full rounded-md border-gray-300 pl-10 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border py-3 pr-3"
              placeholder="Ask a question or search for concepts..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSearching}
            />
          </div>
          <Button
            type="submit"
            disabled={isSearching || !query.trim()}
            className="bg-blue-600 text-white hover:bg-blue-700 px-6"
          >
            {isSearching ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Searching...
              </>
            ) : (
              'Search'
            )}
          </Button>
        </form>

        {error && (
          <div className="mt-4 rounded-md bg-red-50 p-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-red-400" aria-hidden="true" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">{error}</h3>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results Section */}
      {!hasSearched && !isSearching && !error && (
        <div className="rounded-lg border bg-white p-12 text-center shadow-sm">
          <Search className="mx-auto h-12 w-12 text-gray-300" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Semantic Search</h3>
          <p className="mt-1 text-sm text-gray-500">
            Enter a query above to search through your ingested documents.
          </p>
        </div>
      )}

      {isSearching && !response && (
        <div className="rounded-lg border bg-white p-12 flex justify-center items-center shadow-sm">
          <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
        </div>
      )}

      {hasSearched && response && !isSearching && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">
              {response.results.length} {response.results.length === 1 ? 'Result' : 'Results'}
            </h2>
            <span className="text-xs text-gray-500">
              Retrieved in {response.meta.retrieval_ms}ms
            </span>
          </div>

          {response.results.length === 0 ? (
            <div className="rounded-lg border bg-white p-12 text-center shadow-sm">
              <FileText className="mx-auto h-12 w-12 text-gray-300" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
              <p className="mt-1 text-sm text-gray-500">
                We couldn't find any knowledge chunks matching your query.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {response.results.map((result) => (
                <div key={result.chunk_id} className="rounded-lg border bg-white shadow-sm overflow-hidden">
                  <div className="border-b bg-gray-50 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">
                        {result.document_title}
                      </span>
                    </div>
                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
                      Score: {result.score.toFixed(3)}
                    </span>
                  </div>
                  <div className="p-4">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {result.content}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
