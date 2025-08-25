'use client';

import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Tag,
  Calendar,
  User,
  Star,
  Clock,
  Sparkles,
  X
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface SearchFilters {
  query: string;
  date_range: 'all' | 'today' | 'week' | 'month' | 'year';
  sources: string[];
  topics: string[];
  min_score: number;
  content_type: 'all' | 'articles' | 'videos' | 'podcasts';
  reading_time: 'all' | 'short' | 'medium' | 'long';
  personalized: boolean;
}

interface SearchResult {
  id: string;
  title: string;
  description: string;
  source: string;
  published_date: string;
  score: number;
  reading_time_minutes: number;
  topics: string[];
  url: string;
  image_url?: string;
  content_type: 'article' | 'video' | 'podcast';
  personalization_score?: number;
}

export const SearchInterface: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    date_range: 'all',
    sources: [],
    topics: [],
    min_score: 0,
    content_type: 'all',
    reading_time: 'all',
    personalized: true
  });
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [availableSources, setAvailableSources] = useState<string[]>([]);
  const [availableTopics, setAvailableTopics] = useState<string[]>([]);

  useEffect(() => {
    // Load available sources and topics
    const fetchOptions = async () => {
      try {
        const response = await fetch('/api/proxy/search/options', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          setAvailableSources(data.sources || []);
          setAvailableTopics(data.topics || []);
        }
      } catch (error) {
        console.error('Failed to fetch search options:', error);
        // Mock data for demonstration
        setAvailableSources([
          'TechCrunch', 'Hacker News', 'MIT Technology Review', 'The Verge', 
          'Ars Technica', 'Wired', 'IEEE Spectrum', 'Nature', 'Science'
        ]);
        setAvailableTopics([
          'AI & Machine Learning', 'Web Development', 'Cybersecurity', 'Blockchain',
          'Cloud Computing', 'Mobile Development', 'Data Science', 'DevOps',
          'IoT', 'Quantum Computing', 'Robotics', 'Biotech'
        ]);
      }
    };

    fetchOptions();
  }, []);

  const performSearch = async () => {
    if (!filters.query.trim() && filters.sources.length === 0 && filters.topics.length === 0) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/proxy/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(filters),
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
      }
    } catch (error) {
      console.error('Search failed:', error);
      // Mock search results
      const mockResults: SearchResult[] = [
        {
          id: '1',
          title: 'Revolutionary AI Model Achieves Human-Level Performance',
          description: 'New transformer architecture shows unprecedented capabilities in reasoning and code generation, potentially changing the landscape of AI development.',
          source: 'MIT Technology Review',
          published_date: '2024-01-25',
          score: 9.2,
          reading_time_minutes: 8,
          topics: ['AI & Machine Learning', 'Research'],
          url: 'https://example.com/ai-breakthrough',
          content_type: 'article',
          personalization_score: 0.94
        },
        {
          id: '2',
          title: 'Quantum Computing Breakthrough: Error-Free Calculations',
          description: 'Scientists achieve quantum error correction milestone that could lead to practical quantum computers within the decade.',
          source: 'Nature',
          published_date: '2024-01-24',
          score: 8.8,
          reading_time_minutes: 12,
          topics: ['Quantum Computing', 'Physics'],
          url: 'https://example.com/quantum-breakthrough',
          content_type: 'article',
          personalization_score: 0.87
        },
        {
          id: '3',
          title: 'The Future of Web Development: What\'s Next?',
          description: 'Industry experts discuss emerging trends in web development, from AI-powered coding to the evolution of JavaScript frameworks.',
          source: 'TechCrunch',
          published_date: '2024-01-23',
          score: 7.5,
          reading_time_minutes: 15,
          topics: ['Web Development', 'JavaScript'],
          url: 'https://example.com/web-future',
          content_type: 'article',
          personalization_score: 0.92
        }
      ];
      
      // Filter results based on search criteria
      let filteredResults = mockResults;
      
      if (filters.query.trim()) {
        const query = filters.query.toLowerCase();
        filteredResults = filteredResults.filter(result => 
          result.title.toLowerCase().includes(query) ||
          result.description.toLowerCase().includes(query) ||
          result.topics.some(topic => topic.toLowerCase().includes(query))
        );
      }
      
      if (filters.topics.length > 0) {
        filteredResults = filteredResults.filter(result =>
          result.topics.some(topic => filters.topics.includes(topic))
        );
      }
      
      if (filters.sources.length > 0) {
        filteredResults = filteredResults.filter(result =>
          filters.sources.includes(result.source)
        );
      }
      
      setResults(filteredResults);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      performSearch();
    }
  };

  const toggleFilter = (type: 'sources' | 'topics', value: string) => {
    setFilters(prev => ({
      ...prev,
      [type]: prev[type].includes(value)
        ? prev[type].filter(item => item !== value)
        : [...prev[type], value]
    }));
  };

  const clearFilters = () => {
    setFilters({
      query: '',
      date_range: 'all',
      sources: [],
      topics: [],
      min_score: 0,
      content_type: 'all',
      reading_time: 'all',
      personalized: true
    });
    setResults([]);
  };

  const getReadingTimeLabel = (minutes: number) => {
    if (minutes <= 3) return 'Quick read';
    if (minutes <= 10) return 'Short read';
    if (minutes <= 20) return 'Medium read';
    return 'Long read';
  };

  const getContentTypeColor = (type: string) => {
    switch (type) {
      case 'video':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      case 'podcast':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400';
      default:
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Semantic Search</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Find relevant content with AI-powered search and personalization
          </p>
        </div>
        {isAuthenticated && (
          <Badge variant="secondary" className="mt-2 sm:mt-0">
            <Sparkles className="w-4 h-4 mr-1" />
            Personalized Results
          </Badge>
        )}
      </div>

      {/* Search Bar */}
      <div className="relative">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <Input
              type="text"
              placeholder="Search articles, topics, or keywords..."
              value={filters.query}
              onChange={(e) => setFilters(prev => ({ ...prev, query: e.target.value }))}
              onKeyPress={handleKeyPress}
              className="pl-10 pr-4"
            />
          </div>
          <Button
            onClick={() => setShowFilters(!showFilters)}
            variant="outline"
            size="default"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
            {(filters.sources.length + filters.topics.length) > 0 && (
              <Badge variant="secondary" className="ml-2 text-xs">
                {filters.sources.length + filters.topics.length}
              </Badge>
            )}
          </Button>
          <Button onClick={performSearch} disabled={loading}>
            {loading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-r-transparent" />
            ) : (
              <Search className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Search Filters</h3>
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="h-4 w-4 mr-1" />
              Clear All
            </Button>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Calendar className="h-4 w-4 inline mr-1" />
              Date Range
            </label>
            <div className="flex flex-wrap gap-2">
              {(['all', 'today', 'week', 'month', 'year'] as const).map((range) => (
                <Button
                  key={range}
                  variant={filters.date_range === range ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilters(prev => ({ ...prev, date_range: range }))}
                >
                  {range === 'all' ? 'All Time' : range.charAt(0).toUpperCase() + range.slice(1)}
                </Button>
              ))}
            </div>
          </div>

          {/* Sources */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <User className="h-4 w-4 inline mr-1" />
              Sources ({filters.sources.length} selected)
            </label>
            <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
              {availableSources.map((source) => (
                <Button
                  key={source}
                  variant={filters.sources.includes(source) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => toggleFilter('sources', source)}
                >
                  {source}
                </Button>
              ))}
            </div>
          </div>

          {/* Topics */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Tag className="h-4 w-4 inline mr-1" />
              Topics ({filters.topics.length} selected)
            </label>
            <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
              {availableTopics.map((topic) => (
                <Button
                  key={topic}
                  variant={filters.topics.includes(topic) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => toggleFilter('topics', topic)}
                >
                  {topic}
                </Button>
              ))}
            </div>
          </div>

          {/* Content Type & Reading Time */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Content Type
              </label>
              <div className="flex flex-wrap gap-2">
                {(['all', 'articles', 'videos', 'podcasts'] as const).map((type) => (
                  <Button
                    key={type}
                    variant={filters.content_type === type ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilters(prev => ({ ...prev, content_type: type }))}
                  >
                    {type === 'all' ? 'All Types' : type.charAt(0).toUpperCase() + type.slice(1)}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                <Clock className="h-4 w-4 inline mr-1" />
                Reading Time
              </label>
              <div className="flex flex-wrap gap-2">
                {(['all', 'short', 'medium', 'long'] as const).map((time) => (
                  <Button
                    key={time}
                    variant={filters.reading_time === time ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilters(prev => ({ ...prev, reading_time: time }))}
                  >
                    {time === 'all' ? 'Any Length' : 
                     time === 'short' ? '< 5 min' :
                     time === 'medium' ? '5-15 min' : '> 15 min'}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      <div className="space-y-4">
        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600 dark:text-gray-400">Searching...</p>
          </div>
        )}

        {!loading && results.length === 0 && filters.query && (
          <div className="text-center py-8">
            <Search className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No results found</h3>
            <p className="text-gray-600 dark:text-gray-400">Try adjusting your search terms or filters.</p>
          </div>
        )}

        {!loading && results.length > 0 && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Found {results.length} results
              </p>
              {isAuthenticated && filters.personalized && (
                <Badge variant="secondary">
                  <Sparkles className="w-3 h-3 mr-1" />
                  Ranked by relevance
                </Badge>
              )}
            </div>

            <div className="space-y-4">
              {results.map((result) => (
                <div
                  key={result.id}
                  className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
                        {result.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 text-sm mb-3 line-clamp-3">
                        {result.description}
                      </p>
                    </div>
                    {result.personalization_score && isAuthenticated && (
                      <div className="ml-4 text-right">
                        <div className="text-sm text-gray-500 dark:text-gray-400">Relevance</div>
                        <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                          {Math.round(result.personalization_score * 100)}%
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 mb-3">
                    <Badge className={getContentTypeColor(result.content_type)}>
                      {result.content_type}
                    </Badge>
                    <Badge variant="outline">
                      <Star className="w-3 h-3 mr-1" />
                      {result.score}/10
                    </Badge>
                    <Badge variant="outline">
                      <Clock className="w-3 h-3 mr-1" />
                      {result.reading_time_minutes} min • {getReadingTimeLabel(result.reading_time_minutes)}
                    </Badge>
                    {result.topics.slice(0, 2).map(topic => (
                      <Badge key={topic} variant="secondary">
                        {topic}
                      </Badge>
                    ))}
                  </div>

                  <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-2">
                      <span>{result.source}</span>
                      <span>•</span>
                      <span>{new Date(result.published_date).toLocaleDateString()}</span>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <a href={result.url} target="_blank" rel="noopener noreferrer">
                        Read More
                      </a>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};