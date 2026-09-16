import { useState, useMemo } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Search, FileText, AlertCircle, Loader2, SlidersHorizontal } from 'lucide-react';
import { Button } from '../components/ui/button';
import { knowledgeApi } from '../features/knowledge/api/knowledgeApi';
import type { SearchResponse, SearchResultChunk } from '../features/knowledge/types';

export default function Knowledge() {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(5);
  const [minSimilarity, setMinSimilarity] = useState(0.0);

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
      const data = await knowledgeApi.searchKnowledge({
        query: query.trim(),
        limit,
        min_similarity: minSimilarity
      });
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

  const groupedResults = useMemo(() => {
    if (!response?.results) return [];

    const groups: Record<number, { document_title: string; chunks: SearchResultChunk[] }> = {};

    response.results.forEach(result => {
      if (!groups[result.document_id]) {
        groups[result.document_id] = {
          document_title: result.document_title,
          chunks: []
        };
      }
      groups[result.document_id].chunks.push(result);
    });

    return Object.values(groups);
  }, [response]);

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
        <form onSubmit={handleSearch} className="flex flex-col gap-4">
          <div className="flex gap-4">
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
          </div>

          <div className="flex flex-wrap gap-6 items-center rounded-md bg-gray-50 p-4 border border-gray-100 mt-2">
            <div className="flex items-center space-x-2 text-sm text-gray-700 w-full sm:w-auto">
              <SlidersHorizontal className="h-4 w-4 text-gray-400" />
              <span className="font-medium">Search Controls</span>
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <label htmlFor="limit" className="text-sm text-gray-600 whitespace-nowrap">Result Limit:</label>
              <input
                id="limit"
                type="number"
                min="1"
                max="20"
                className="block w-20 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border py-1.5 px-3"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value, 10) || 5)}
                disabled={isSearching}
              />
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <label htmlFor="min_similarity" className="text-sm text-gray-600 whitespace-nowrap">Min. Similarity:</label>
              <input
                id="min_similarity"
                type="number"
                min="0.0"
                max="1.0"
                step="0.1"
                className="block w-24 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border py-1.5 px-3"
                value={minSimilarity}
                onChange={(e) => setMinSimilarity(parseFloat(e.target.value) || 0.0)}
                disabled={isSearching}
              />
            </div>
          </div>
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
          <div className="flex items-center justify-between bg-white border rounded-md px-4 py-3 shadow-sm">
            <h2 className="text-sm font-medium text-gray-900">
              {response.results.length} {response.results.length === 1 ? 'Result' : 'Results'} returned
            </h2>
            <div className="flex text-xs text-gray-500 space-x-4">
              <span>Retrieval: {response.meta.retrieval_ms}ms</span>
              <span className="hidden sm:inline">Embedding: {response.meta.embedding_ms}ms</span>
              <span className="font-medium">Total: {response.meta.total_ms}ms</span>
            </div>
          </div>

          {response.results.length === 0 ? (
            <div className="rounded-lg border bg-white p-12 text-center shadow-sm">
              <FileText className="mx-auto h-12 w-12 text-gray-300" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
              <p className="mt-1 text-sm text-gray-500">
                We couldn't find any knowledge chunks matching your query with the current settings.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {groupedResults.map((group, groupIdx) => (
                <div key={groupIdx} className="rounded-lg border bg-white shadow-sm overflow-hidden">
                  <div className="border-b bg-gray-50 px-4 py-3 flex items-center">
                    <FileText className="h-5 w-5 text-gray-400 mr-2" />
                    <span className="text-sm font-semibold text-gray-900">
                      {group.document_title}
                    </span>
                  </div>

                  <div className="divide-y divide-gray-100">
                    {group.chunks.map((result) => (
                      <div key={result.chunk_id} className="p-4">
                        <div className="flex justify-between items-center mb-2">
                          <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 border border-blue-100">
                            Score: {result.score.toFixed(3)}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                          {result.content}
                        </p>
                      </div>
                    ))}
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
