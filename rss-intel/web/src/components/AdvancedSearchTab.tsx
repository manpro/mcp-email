import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, X, Save, Clock, TrendingUp, Calendar, Star, Image } from 'lucide-react';

interface SearchFilters {
  sources: string[];
  categories: string[];
  min_score: number | null;
  max_score: number | null;
  date_from: string | null;
  date_to: string | null;
  has_image: boolean | null;
  is_starred: boolean | null;
  labels: string[];
  exclude_spam: boolean;
  content_quality_min: number | null;
  sentiment: string | null;
  word_count_min: number | null;
  word_count_max: number | null;
  language: string | null;
}

interface SearchSettings {
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: string;
  enable_semantic: boolean;
  highlight: boolean;
}

interface SearchResult {
  id: number;
  title: string;
  url: string;
  source: string;
  published_at: string;
  score: number | null;
  content_preview: string | null;
  image_proxy_path: string | null;
  relevance_score: number;
  match_highlights: string[];
  match_reason: string;
  has_image: boolean;
  is_starred: boolean;
  labels: string[];
  spam_detected: boolean | null;
  content_quality_score: number | null;
}

interface SearchResponse {
  results: SearchResult[];
  total_count: number;
  search_time_ms: number;
  page: number;
  page_size: number;
  total_pages: number;
  filters_applied: Record<string, any>;
  suggestions: string[];
  facets: {
    sources: Record<string, number>;
    score_ranges: Record<string, number>;
    date_ranges: Record<string, number>;
  };
}

interface SavedSearch {
  id: number;
  name: string;
  description: string;
  search_params: {
    query: string;
    filters: SearchFilters;
    settings: SearchSettings;
  };
  created_at: string;
}

const AdvancedSearchTab: React.FC = () => {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    sources: [],
    categories: [],
    min_score: null,
    max_score: null,
    date_from: null,
    date_to: null,
    has_image: null,
    is_starred: null,
    labels: [],
    exclude_spam: true,
    content_quality_min: null,
    sentiment: null,
    word_count_min: null,
    word_count_max: null,
    language: null,
  });
  
  const [settings, setSettings] = useState<SearchSettings>({
    page: 1,
    page_size: 20,
    sort_by: 'relevance',
    sort_order: 'desc',
    enable_semantic: true,
    highlight: true,
  });

  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [availableSources, setAvailableSources] = useState<string[]>([]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [showSavedSearches, setShowSavedSearches] = useState(false);
  const [saveSearchName, setSaveSearchName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Debounced search
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);

  const performSearch = useCallback(async () => {
    if (!query.trim() && !hasActiveFilters()) return;
    
    setLoading(true);
    try {
      const searchRequest = {
        query,
        ...filters,
        ...settings,
      };

      const response = await fetch('/api/proxy/api/advanced-search/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchRequest),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data);
      
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  }, [query, filters, settings]);

  const hasActiveFilters = () => {
    return filters.sources.length > 0 ||
           filters.categories.length > 0 ||
           filters.min_score !== null ||
           filters.max_score !== null ||
           filters.date_from !== null ||
           filters.date_to !== null ||
           filters.has_image !== null ||
           filters.is_starred !== null ||
           filters.labels.length > 0 ||
           !filters.exclude_spam ||
           filters.content_quality_min !== null ||
           filters.sentiment !== null ||
           filters.word_count_min !== null ||
           filters.word_count_max !== null ||
           filters.language !== null;
  };

  // Debounced search
  useEffect(() => {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    const timeout = setTimeout(() => {
      if (query.trim() || hasActiveFilters()) {
        performSearch();
      }
    }, 500);

    setSearchTimeout(timeout);

    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, [query, filters, settings]);

  // Load available sources and saved searches
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        // Load facets to get available sources
        const facetsResponse = await fetch('/api/proxy/api/advanced-search/search/facets');
        const facetsData = await facetsResponse.json();
        setAvailableSources(Object.keys(facetsData.facets.sources || {}));

        // Load saved searches
        const savedResponse = await fetch('/api/proxy/api/advanced-search/search/saved');
        const savedData = await savedResponse.json();
        setSavedSearches(savedData.saved_searches || []);
      } catch (error) {
        console.error('Failed to load search metadata:', error);
      }
    };

    loadMetadata();
  }, []);

  const clearFilters = () => {
    setFilters({
      sources: [],
      categories: [],
      min_score: null,
      max_score: null,
      date_from: null,
      date_to: null,
      has_image: null,
      is_starred: null,
      labels: [],
      exclude_spam: true,
      content_quality_min: null,
      sentiment: null,
      word_count_min: null,
      word_count_max: null,
      language: null,
    });
  };

  const saveSearch = async () => {
    if (!saveSearchName.trim()) return;

    try {
      const savedSearch = {
        name: saveSearchName,
        description: `Search for: ${query}`,
        search_params: {
          query,
          ...filters,
          ...settings,
        },
      };

      const response = await fetch('/api/proxy/api/advanced-search/search/saved', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(savedSearch),
      });

      if (response.ok) {
        setSaveSearchName('');
        setShowSaveDialog(false);
        // Reload saved searches
        const savedResponse = await fetch('/api/proxy/api/advanced-search/search/saved');
        const savedData = await savedResponse.json();
        setSavedSearches(savedData.saved_searches || []);
      }
    } catch (error) {
      console.error('Failed to save search:', error);
    }
  };

  const loadSavedSearch = (search: SavedSearch) => {
    setQuery(search.search_params.query);
    setFilters(search.search_params.filters);
    setSettings(search.search_params.settings);
    setShowSavedSearches(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatScore = (score: number | null) => {
    if (score === null) return 'N/A';
    return score > 0 ? `+${score}` : score.toString();
  };

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-gray-500';
    if (score >= 50) return 'text-green-600';
    if (score >= 0) return 'text-blue-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-4 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search articles with advanced semantic understanding..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center space-x-2 px-4 py-3 rounded-lg border transition-colors ${
              showFilters || hasActiveFilters()
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Filter size={20} />
            <span>Filters</span>
            {hasActiveFilters() && (
              <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
                {Object.values(filters).filter(v => v !== null && v !== false && (!Array.isArray(v) || v.length > 0)).length}
              </span>
            )}
          </button>
          <button
            onClick={() => setShowSavedSearches(!showSavedSearches)}
            className="flex items-center space-x-2 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Clock size={20} />
            <span>Saved</span>
          </button>
          <button
            onClick={() => setShowSaveDialog(true)}
            className="flex items-center space-x-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Save size={20} />
            <span>Save Search</span>
          </button>
        </div>

        {/* Search Settings */}
        <div className="flex items-center justify-between text-sm text-gray-600">
          <div className="flex items-center space-x-4">
            <select
              value={settings.sort_by}
              onChange={(e) => setSettings(prev => ({ ...prev, sort_by: e.target.value }))}
              className="border border-gray-200 rounded px-2 py-1"
            >
              <option value="relevance">Relevance</option>
              <option value="date">Date</option>
              <option value="score">Score</option>
              <option value="title">Title</option>
            </select>
            <select
              value={settings.sort_order}
              onChange={(e) => setSettings(prev => ({ ...prev, sort_order: e.target.value }))}
              className="border border-gray-200 rounded px-2 py-1"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={settings.enable_semantic}
                onChange={(e) => setSettings(prev => ({ ...prev, enable_semantic: e.target.checked }))}
              />
              <span>Semantic Search</span>
            </label>
          </div>
          {searchResults && (
            <div className="text-sm text-gray-500">
              {searchResults.total_count} results in {searchResults.search_time_ms.toFixed(1)}ms
            </div>
          )}
        </div>
      </div>

      {/* Advanced Filters Panel */}
      {showFilters && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">Advanced Filters</h3>
            <div className="flex items-center space-x-2">
              <button
                onClick={clearFilters}
                className="text-sm text-red-600 hover:text-red-800"
              >
                Clear All
              </button>
              <button
                onClick={() => setShowFilters(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Source Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sources</label>
              <select
                multiple
                value={filters.sources}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  sources: Array.from(e.target.selectedOptions, option => option.value)
                }))}
                className="w-full border border-gray-300 rounded-lg p-2 h-24"
              >
                {availableSources.map(source => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </div>

            {/* Score Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Score Range</label>
              <div className="flex space-x-2">
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.min_score || ''}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    min_score: e.target.value ? parseInt(e.target.value) : null
                  }))}
                  className="flex-1 border border-gray-300 rounded-lg p-2"
                />
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.max_score || ''}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    max_score: e.target.value ? parseInt(e.target.value) : null
                  }))}
                  className="flex-1 border border-gray-300 rounded-lg p-2"
                />
              </div>
            </div>

            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
              <div className="space-y-2">
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    date_from: e.target.value || null
                  }))}
                  className="w-full border border-gray-300 rounded-lg p-2"
                />
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    date_to: e.target.value || null
                  }))}
                  className="w-full border border-gray-300 rounded-lg p-2"
                />
              </div>
            </div>

            {/* Content Filters */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Content</label>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={filters.has_image === true}
                    onChange={(e) => setFilters(prev => ({
                      ...prev,
                      has_image: e.target.checked ? true : null
                    }))}
                  />
                  <span>Has Image</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={filters.is_starred === true}
                    onChange={(e) => setFilters(prev => ({
                      ...prev,
                      is_starred: e.target.checked ? true : null
                    }))}
                  />
                  <span>Starred</span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={filters.exclude_spam}
                    onChange={(e) => setFilters(prev => ({
                      ...prev,
                      exclude_spam: e.target.checked
                    }))}
                  />
                  <span>Exclude Spam</span>
                </label>
              </div>
            </div>

            {/* Quality Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Quality</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={filters.content_quality_min || 0}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  content_quality_min: parseFloat(e.target.value)
                }))}
                className="w-full"
              />
              <div className="text-xs text-gray-500 mt-1">
                Min Quality: {(filters.content_quality_min || 0).toFixed(1)}
              </div>
            </div>

            {/* Sentiment Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sentiment</label>
              <select
                value={filters.sentiment || ''}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  sentiment: e.target.value || null
                }))}
                className="w-full border border-gray-300 rounded-lg p-2"
              >
                <option value="">Any</option>
                <option value="positive">Positive</option>
                <option value="negative">Negative</option>
                <option value="neutral">Neutral</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Saved Searches Panel */}
      {showSavedSearches && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">Saved Searches</h3>
            <button
              onClick={() => setShowSavedSearches(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={20} />
            </button>
          </div>
          <div className="space-y-3">
            {savedSearches.map(search => (
              <div
                key={search.id}
                onClick={() => loadSavedSearch(search)}
                className="p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <div className="font-medium">{search.name}</div>
                <div className="text-sm text-gray-600">{search.description}</div>
                <div className="text-xs text-gray-400 mt-1">
                  Created: {formatDate(search.created_at)}
                </div>
              </div>
            ))}
            {savedSearches.length === 0 && (
              <p className="text-gray-500 text-center py-4">No saved searches yet</p>
            )}
          </div>
        </div>
      )}

      {/* Save Search Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium mb-4">Save Search</h3>
            <input
              type="text"
              value={saveSearchName}
              onChange={(e) => setSaveSearchName(e.target.value)}
              placeholder="Search name..."
              className="w-full border border-gray-300 rounded-lg p-3 mb-4"
              autoFocus
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={saveSearch}
                disabled={!saveSearchName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Results */}
      {loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Searching...</p>
        </div>
      )}

      {searchResults && !loading && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <h3 className="text-lg font-medium">
                  {searchResults.total_count} Results
                </h3>
                {searchResults.suggestions.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-500">Suggestions:</span>
                    {searchResults.suggestions.slice(0, 3).map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setQuery(suggestion)}
                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="text-sm text-gray-500">
                Page {searchResults.page} of {searchResults.total_pages}
              </div>
            </div>
          </div>

          <div className="divide-y divide-gray-200">
            {searchResults.results.map(result => (
              <div key={result.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <h4 className="text-lg font-medium text-blue-600 hover:text-blue-800">
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline"
                        >
                          {result.title}
                        </a>
                      </h4>
                      {result.has_image && <Image className="text-green-500" size={16} />}
                      {result.is_starred && <Star className="text-yellow-500 fill-current" size={16} />}
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
                      <span>{result.source}</span>
                      <span>{formatDate(result.published_at)}</span>
                      <span className={`font-medium ${getScoreColor(result.score)}`}>
                        Score: {formatScore(result.score)}
                      </span>
                      <span className="text-purple-600">
                        Relevance: {(result.relevance_score * 100).toFixed(1)}%
                      </span>
                      <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                        {result.match_reason}
                      </span>
                    </div>

                    {result.content_preview && (
                      <p className="text-gray-700 text-sm mb-2">
                        {result.content_preview}
                      </p>
                    )}

                    {result.match_highlights.length > 0 && (
                      <div className="text-xs text-gray-600">
                        <strong>Highlights:</strong>
                        <ul className="mt-1">
                          {result.match_highlights.slice(0, 3).map((highlight, index) => (
                            <li key={index} className="ml-2">• {highlight}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {result.labels.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {result.labels.map(label => (
                          <span
                            key={label}
                            className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                          >
                            {label}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {result.image_proxy_path && (
                    <div className="ml-4 flex-shrink-0">
                      <img
                        src={result.image_proxy_path}
                        alt=""
                        className="w-24 h-16 object-cover rounded"
                        loading="lazy"
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {searchResults.total_pages > 1 && (
            <div className="p-4 border-t border-gray-200 flex items-center justify-center space-x-4">
              <button
                onClick={() => setSettings(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                disabled={searchResults.page <= 1}
                className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {searchResults.page} of {searchResults.total_pages}
              </span>
              <button
                onClick={() => setSettings(prev => ({ ...prev, page: Math.min(searchResults.total_pages, prev.page + 1) }))}
                disabled={searchResults.page >= searchResults.total_pages}
                className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {searchResults && searchResults.results.length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="text-gray-400 mb-4">
            <Search size={48} className="mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
          <p className="text-gray-600 mb-4">
            Try adjusting your search query or filters to find what you're looking for.
          </p>
          {searchResults.suggestions.length > 0 && (
            <div className="space-x-2">
              <span className="text-sm text-gray-500">Try:</span>
              {searchResults.suggestions.slice(0, 3).map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setQuery(suggestion)}
                  className="inline-block bg-blue-100 text-blue-800 text-sm px-3 py-1 rounded-full hover:bg-blue-200 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdvancedSearchTab;