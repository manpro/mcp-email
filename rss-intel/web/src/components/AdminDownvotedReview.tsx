'use client';

import { useState, useEffect } from 'react';
import { Article, apiClient } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ExternalLink, Eye } from 'lucide-react';
import { ClientTime } from './ClientTime';
import ScoreBadge from './ScoreBadge';
import ArticleReader from './ArticleReader';

export default function AdminDownvotedReview() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  useEffect(() => {
    loadDownvotedArticles();
  }, [page]);

  const loadDownvotedArticles = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getDownvotedArticles(page, 20);
      setArticles(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to load downvoted articles:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading && articles.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Loading downvoted articles...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Downvoted Articles Review</h1>
        <p className="text-muted-foreground mb-4">
          Review articles marked as poor quality to identify content issues and improve filtering.
        </p>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="text-sm">
            Total: {total} downvoted articles
          </Badge>
          {total > 0 && (
            <Badge variant="secondary" className="text-sm">
              Page {page} of {Math.ceil(total / 20)}
            </Badge>
          )}
        </div>
      </div>

      {articles.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground">No downvoted articles found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {articles.map((article) => (
            <Card key={article.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <ScoreBadge score={article.score_total} breakdown={article.scores} />
                    <Badge variant="secondary">{article.source}</Badge>
                    <Badge variant="destructive" className="text-xs">
                      👎 Downvoted
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <ClientTime date={article.published_at} format="relative" />
                  </div>
                </div>

                <h3 className="font-semibold text-lg mb-2 leading-tight">
                  {article.title}
                </h3>

                {article.content && (
                  <p className="text-muted-foreground mb-3 line-clamp-3">
                    {article.content}
                  </p>
                )}

                {/* Quality Issues Section */}
                <div className="bg-red-50 p-3 rounded-lg mb-4">
                  <h4 className="font-medium text-red-900 mb-2">Potential Quality Issues:</h4>
                  <div className="space-y-1 text-sm text-red-800">
                    {article.score_total < 20 && (
                      <div>• Very low relevance score ({article.score_total})</div>
                    )}
                    {article.content && article.content.length < 100 && (
                      <div>• Very short content ({article.content.length} characters)</div>
                    )}
                    {article.title.toLowerCase().includes('webinar') && (
                      <div>• Appears to be promotional webinar content</div>
                    )}
                    {new Date(article.published_at) > new Date() && (
                      <div>• Future-dated article (likely event/webinar)</div>
                    )}
                    {!article.content && (
                      <div>• Missing content/summary</div>
                    )}
                  </div>
                </div>

                {/* Article Topics/Entities */}
                {(article.topics.length > 0 || Object.keys(article.entities).length > 0) && (
                  <div className="mb-4">
                    <div className="flex flex-wrap gap-2">
                      {article.topics.slice(0, 5).map((topic) => (
                        <Badge key={topic} variant="outline" className="text-xs">
                          {topic}
                        </Badge>
                      ))}
                      {Object.entries(article.entities).slice(0, 3).map(([key, value]) => (
                        <Badge key={key} variant="outline" className="text-xs bg-blue-50 text-blue-700">
                          {key}: {String(value).slice(0, 20)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedArticle(article)}
                    className="flex items-center gap-2"
                  >
                    <Eye className="h-4 w-4" />
                    Review Content
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
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between mt-8">
          <Button
            variant="outline"
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1 || loading}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage(page + 1)}
            disabled={page >= Math.ceil(total / 20) || loading}
          >
            Next
          </Button>
        </div>
      )}

      {/* Article Reader Modal */}
      {selectedArticle && (
        <ArticleReader
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
        />
      )}
    </div>
  );
}