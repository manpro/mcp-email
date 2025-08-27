'use client';

import { useState, useEffect } from 'react';
import { ArticleCard } from './ArticleCard';
import { eventTracker, impressionTracker } from '../lib/events';

interface RecommendedArticle {
  id: number;
  title: string;
  url: string;
  source: string;
  published_at: string | null;
  score_total: number;
  has_image: boolean;
  p_read: number;
  rule_score: number;
  why: string[];
  exploration?: boolean;
}

interface RecommendationResponse {
  articles: RecommendedArticle[];
  total: number;
  user_id: string;
  timestamp: string;
}

interface RecommendedTabProps {
  onArticleClick?: (articleId: number) => void;
  onExternalClick?: (articleId: number) => void;
  onStar?: (articleId: number) => void;
  onDismiss?: (articleId: number) => void;
}

export function RecommendedTab({
  onArticleClick,
  onExternalClick,
  onStar,
  onDismiss
}: RecommendedTabProps) {
  const [articles, setArticles] = useState<RecommendedArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchRecommendations = async () => {
    try {
      setError(null);
      
      // Try ML recommendations first via direct backend port (bypass nginx)
      let data: RecommendationResponse | null = null;
      try {
        const mlResponse = await fetch('http://localhost:8000/api/ml/recommend?limit=200');
        if (mlResponse.ok) {
          data = await mlResponse.json();
          if (data && data.articles && data.articles.length > 0) {
            setArticles(data.articles);
            // Track impressions for visible articles
            const articleIds = data.articles.map(a => a.id);
            eventTracker.trackImpressions(articleIds.slice(0, 10)); // Track first 10
            return;
          }
        }
      } catch (mlError) {
        console.warn('ML recommendations failed, falling back to rule-based:', mlError);
      }
      
      // Fallback to rule-based recommendations using items endpoint
      const itemsResponse = await fetch('/api/items?limit=200');
      if (!itemsResponse.ok) {
        throw new Error(`Failed to fetch recommendations: ${itemsResponse.statusText}`);
      }
      
      const itemsData = await itemsResponse.json();
      
      // Convert items to recommendation format
      const fallbackArticles: RecommendedArticle[] = itemsData.items
        .filter((item: any) => item.score_total > 0) // Only items with positive scores
        .sort((a: any, b: any) => {
          // Sort by score and recency
          const scoreA = a.score_total || 0;
          const scoreB = b.score_total || 0;
          const timeA = new Date(a.published_at || 0).getTime();
          const timeB = new Date(b.published_at || 0).getTime();
          
          // Boost recent articles
          const hoursSinceA = (Date.now() - timeA) / (1000 * 60 * 60);
          const hoursSinceB = (Date.now() - timeB) / (1000 * 60 * 60);
          const boostedScoreA = hoursSinceA < 24 ? scoreA * 1.5 : scoreA;
          const boostedScoreB = hoursSinceB < 24 ? scoreB * 1.5 : scoreB;
          
          return boostedScoreB - boostedScoreA;
        })
        .slice(0, 20) // Limit to top 20
        .map((item: any) => ({
          id: item.id,
          title: item.title,
          url: item.url,
          source: item.source,
          published_at: item.published_at,
          score_total: item.score_total || 0,
          has_image: item.has_image || false,
          p_read: Math.min(1.0, (item.score_total || 0) / 100.0), // Normalize score to 0-1
          rule_score: item.score_total || 0,
          why: generateWhyChips(item),
          exploration: false
        }));
      
      setArticles(fallbackArticles);
      
      // Track impressions for visible articles
      if (fallbackArticles.length > 0) {
        const articleIds = fallbackArticles.map(a => a.id);
        eventTracker.trackImpressions(articleIds.slice(0, 10)); // Track first 10
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  // Set up impression tracking for articles
  useEffect(() => {
    if (articles.length === 0) return;

    const observer = impressionTracker;
    
    // Observe all article elements
    const articleElements = document.querySelectorAll('[data-article-id]');
    articleElements.forEach(element => {
      observer.observe(element);
    });

    return () => {
      // Clean up when component unmounts or articles change
      articleElements.forEach(element => {
        observer.unobserve(element);
      });
    };
  }, [articles]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchRecommendations();
  };

  const handleArticleOpen = (article: RecommendedArticle) => {
    eventTracker.trackOpen(article.id);
    onArticleClick?.(article.id);
  };

  const handleExternalClick = (article: RecommendedArticle) => {
    eventTracker.trackExternalClick(article.id);
    if (article.url) {
      window.open(article.url, '_blank', 'noopener,noreferrer');
    }
    onExternalClick?.(article.id);
  };

  const handleStar = (article: RecommendedArticle) => {
    eventTracker.trackStar(article.id);
    onStar?.(article.id);
  };

  const handleDismiss = (article: RecommendedArticle) => {
    eventTracker.trackDismiss(article.id);
    
    // Remove from UI
    setArticles(prev => prev.filter(a => a.id !== article.id));
    
    onDismiss?.(article.id);
  };

  const generateWhyChips = (item: any): string[] => {
    const chips: string[] = [];
    
    if (item.score_total > 50) {
      chips.push("High quality");
    }
    
    if (item.has_image) {
      chips.push("Has image");
    }
    
    // Check recency
    if (item.published_at) {
      const hoursOld = (Date.now() - new Date(item.published_at).getTime()) / (1000 * 60 * 60);
      if (hoursOld < 24) {
        chips.push("Fresh");
      } else if (hoursOld < 72) {
        chips.push("Recent");
      }
    }
    
    // Source-based
    if (['TechCrunch AI', 'OpenAI Blog', 'Nature AI'].includes(item.source)) {
      chips.push("Top source");
    }
    
    // Topic-based
    if (item.topics && Array.isArray(item.topics)) {
      const hotTopics = ['ai', 'bitcoin', 'crypto', 'blockchain'];
      if (item.topics.some((topic: string) => hotTopics.includes(topic.toLowerCase()))) {
        chips.push("Hot topic");
      }
    }
    
    return chips.slice(0, 3); // Limit to 3 chips
  };

  const formatPercentage = (pRead: number) => {
    return `${Math.round(pRead * 100)}%`;
  };

  const getWhyChipColor = (chip: string) => {
    if (chip === "High confidence") return "bg-green-100 text-green-800";
    if (chip === "Good match") return "bg-blue-100 text-blue-800";
    if (chip === "Trending") return "bg-orange-100 text-orange-800";
    if (chip === "Popular") return "bg-purple-100 text-purple-800";
    if (chip.startsWith("source:")) return "bg-gray-100 text-gray-800";
    if (chip.includes("⭐")) return "bg-yellow-100 text-yellow-800";
    return "bg-slate-100 text-slate-800";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center space-x-3">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="text-gray-600">Loading personalized recommendations...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">{error}</div>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-600 mb-4">
          No personalized recommendations available yet.
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Interact with articles (star, read, click) to improve recommendations.
        </p>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <h2 className="text-lg font-semibold text-gray-900">
            Recommended for You
          </h2>
          <span className="text-sm text-gray-500">
            ({articles.length} articles)
          </span>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Articles list */}
      <div className="space-y-3">
        {articles.map((article, index) => (
          <div
            key={article.id}
            className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
            data-article-id={article.id}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                {/* Title and source */}
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="text-lg font-medium text-gray-900 line-clamp-2">
                    <button
                      onClick={() => handleArticleOpen(article)}
                      className="text-left hover:text-blue-600 focus:text-blue-600"
                    >
                      {article.title}
                    </button>
                  </h3>
                  {article.exploration && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Explore
                    </span>
                  )}
                </div>

                {/* Source and published date */}
                <div className="flex items-center space-x-3 text-sm text-gray-600 mb-3">
                  <span className="font-medium">{article.source}</span>
                  {article.published_at && (
                    <>
                      <span>•</span>
                      <span>{new Date(article.published_at).toLocaleDateString()}</span>
                    </>
                  )}
                </div>

                {/* Why chips */}
                {article.why && article.why.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <span className="text-xs text-gray-500">Why:</span>
                    {article.why.map((chip, chipIndex) => (
                      <span
                        key={chipIndex}
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getWhyChipColor(chip)}`}
                      >
                        {chip}
                      </span>
                    ))}
                  </div>
                )}

                {/* ML scores */}
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <span>ML confidence:</span>
                    <span className="font-semibold text-blue-600">
                      {formatPercentage(article.p_read)}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span>Rule score:</span>
                    <span className="font-medium">{article.rule_score}</span>
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => handleExternalClick(article)}
                  className="p-2 text-gray-400 hover:text-blue-600 focus:text-blue-600"
                  title="Open article"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </button>
                
                <button
                  onClick={() => handleStar(article)}
                  className="p-2 text-gray-400 hover:text-yellow-500 focus:text-yellow-500"
                  title="Star article"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.196-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                </button>

                <button
                  onClick={() => handleDismiss(article)}
                  className="p-2 text-gray-400 hover:text-red-500 focus:text-red-500"
                  title="Not interested"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}