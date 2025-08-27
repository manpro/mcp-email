'use client';

import { useState, useEffect } from 'react';
import { Article, apiClient } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TrendingUp, Flame, Eye, Star, ExternalLink, Clock } from 'lucide-react';
import { ClientTime } from './ClientTime';
import ScoreBadge from './ScoreBadge';
import { ArticleImage } from './ArticleImage';

interface TrendingArticle extends Article {
  engagement_count: number;
  active_engagement: number;
  weighted_engagement: number;
  trend_score: number;
}

interface TrendingTabProps {
  onArticleClick?: (article: Article) => void;
}

export function TrendingTab({ onArticleClick }: TrendingTabProps) {
  const [articles, setArticles] = useState<TrendingArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('24');
  const [minScore, setMinScore] = useState('50');

  useEffect(() => {
    loadTrendingArticles();
  }, [timeframe, minScore]);

  const loadTrendingArticles = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getTrendingArticles(
        parseInt(timeframe), 
        parseInt(minScore), 
        20
      );
      setArticles(data.items);
    } catch (error) {
      console.error('Failed to load trending articles:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Loading trending content...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-orange-500" />
            <h1 className="text-2xl font-bold">Trending Content</h1>
          </div>
          <Badge variant="secondary" className="text-xs">
            🔥 Hot right now
          </Badge>
        </div>
        
        <p className="text-muted-foreground mb-4">
          Articles gaining traction based on user engagement, stars, and views.
        </p>
        
        {/* Controls */}
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <label className="text-sm font-medium">Timeframe:</label>
            <Select value={timeframe} onValueChange={setTimeframe}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="6">6 hours</SelectItem>
                <SelectItem value="12">12 hours</SelectItem>
                <SelectItem value="24">24 hours</SelectItem>
                <SelectItem value="48">48 hours</SelectItem>
                <SelectItem value="72">3 days</SelectItem>
                <SelectItem value="168">1 week</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Min Score:</label>
            <Select value={minScore} onValueChange={setMinScore}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">All</SelectItem>
                <SelectItem value="30">30+</SelectItem>
                <SelectItem value="50">50+</SelectItem>
                <SelectItem value="70">70+</SelectItem>
                <SelectItem value="90">90+</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {articles.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">
              No trending articles found in the last {timeframe} hours.
              <br />
              Try adjusting the timeframe or minimum score.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {articles.map((article, index) => (
            <Card key={article.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  {/* Trending rank */}
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-red-500 text-white flex items-center justify-center text-sm font-bold">
                    {index + 1}
                  </div>
                  
                  {/* Image thumbnail */}
                  {article.has_image && article.image_proxy_path && (
                    <div className="flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden">
                      <ArticleImage
                        src={`/api/img/${article.image_proxy_path}`}
                        alt={article.title}
                        width={64}
                        height={64}
                        blurhash={article.image_blurhash}
                        className="w-full h-full"
                      />
                    </div>
                  )}
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <ScoreBadge score={article.score_total} breakdown={article.scores} />
                        <Badge variant="secondary" className="text-xs">
                          {article.source}
                        </Badge>
                        <Badge variant="outline" className="text-xs bg-orange-50 text-orange-700 border-orange-200">
                          <Flame className="h-3 w-3 mr-1" />
                          Trend: {article.trend_score.toFixed(1)}
                        </Badge>
                      </div>
                      <ClientTime date={article.published_at} format="relative" />
                    </div>

                    <h3 className="font-semibold text-lg leading-tight mb-2">
                      <button
                        onClick={() => onArticleClick?.(article)}
                        className="hover:text-primary-600 hover:underline text-left"
                      >
                        {article.title}
                      </button>
                    </h3>

                    {article.content && (
                      <p className="text-muted-foreground text-sm leading-relaxed line-clamp-2 mb-3">
                        {article.content}
                      </p>
                    )}

                    {/* Engagement metrics */}
                    <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Eye className="h-3 w-3" />
                        <span>{article.engagement_count} interactions</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        <span>{article.weighted_engagement.toFixed(1)} weighted</span>
                      </div>
                      {article.active_engagement > 0 && (
                        <div className="flex items-center gap-1">
                          <Star className="h-3 w-3" />
                          <span>{article.active_engagement} active</span>
                        </div>
                      )}
                    </div>

                    {/* Topics */}
                    {article.topics.length > 0 && (
                      <div className="flex gap-1 flex-wrap mb-3">
                        {article.topics.slice(0, 4).map((topic) => (
                          <Badge key={topic} variant="outline" className="text-xs">
                            {topic}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onArticleClick?.(article)}
                        className="flex items-center gap-2"
                      >
                        Read Article
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        asChild
                      >
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2"
                        >
                          <ExternalLink className="h-4 w-4" />
                          Original
                        </a>
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}