'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RotateCcw, Eye, EyeOff, ExternalLink, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Article } from '@/lib/api';

interface SpamReport {
  article_id: number;
  title: string;
  url: string;
  source: string;
  reported_at: string;
  report_count: number;
  report_source: string;
  reason: string;
  quality_score: number;
  spam_score: number;
  ml_metadata: Record<string, any>;
}

interface SpamTabProps {
  onArticleClick?: (article: Article) => void;
}

export function SpamTab({ onArticleClick }: SpamTabProps) {
  const [spamReports, setSpamReports] = useState<SpamReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const { toast } = useToast();

  const pageSize = 20;

  const fetchSpamReports = async (pageNum: number = 1) => {
    try {
      setLoading(pageNum === 1);
      
      // Get articles with spam flags or low quality scores
      const response = await fetch(`/api/proxy/items?limit=${pageSize}&page=${pageNum}&has_flags=spam_detected,low_quality`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch spam reports');
      }

      const data = await response.json();
      
      // Convert articles to spam report format
      const reports: SpamReport[] = (data.items || []).map((article: any) => ({
        article_id: article.id,
        title: article.title,
        url: article.url,
        source: article.source,
        reported_at: article.created_at || new Date().toISOString(),
        report_count: 1,
        report_source: article.flags?.spam_detected ? 'ml_detection' : 'quality_check',
        reason: article.flags?.spam_signals?.join(', ') || 'Low content quality detected',
        quality_score: Math.round((article.flags?.content_score || 0.5) * 100),
        spam_score: article.flags?.spam_probability || 0.8,
        ml_metadata: article.flags || {}
      }));
      
      if (pageNum === 1) {
        setSpamReports(reports);
      } else {
        setSpamReports(prev => [...prev, ...reports]);
      }
      
      setTotal(data.total || reports.length);
      setPage(pageNum);
    } catch (error) {
      console.error('Error fetching spam reports:', error);
      toast({
        title: "Fel",
        description: "Kunde inte hämta spam-rapporter",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const restoreArticle = async (articleId: number) => {
    try {
      setActionLoading(articleId);
      const response = await fetch(`/api/articles/${articleId}/restore`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to restore article');
      }

      toast({
        title: "Återställd",
        description: "Artikeln har återställts till huvudflödet",
        type: "success",
      });

      // Remove from spam reports
      setSpamReports(prev => prev.filter(report => report.article_id !== articleId));
    } catch (error) {
      console.error('Error restoring article:', error);
      toast({
        title: "Fel",
        description: "Kunde inte återställa artikeln",
        type: "error",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const permanentlyDelete = async (articleId: number) => {
    if (!confirm('Är du säker på att du vill ta bort denna artikel permanent?')) {
      return;
    }

    try {
      setActionLoading(articleId);
      const response = await fetch(`/api/articles/${articleId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to delete article');
      }

      toast({
        title: "Borttagen",
        description: "Artikeln har tagits bort permanent",
        type: "success",
      });

      // Remove from spam reports
      setSpamReports(prev => prev.filter(report => report.article_id !== articleId));
    } catch (error) {
      console.error('Error deleting article:', error);
      toast({
        title: "Fel",
        description: "Kunde inte ta bort artikeln",
        type: "error",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const runSpamAnalysis = async () => {
    try {
      setActionLoading(-1); // Use -1 to indicate batch operation
      
      // Get recent articles to analyze
      const articlesResponse = await fetch('/api/proxy/items?limit=50&sort=created_at', {
        credentials: 'include'
      });
      
      if (!articlesResponse.ok) {
        throw new Error('Failed to fetch articles for analysis');
      }
      
      const articlesData = await articlesResponse.json();
      const articleIds = (articlesData.items || []).map((a: any) => a.id);
      
      if (articleIds.length === 0) {
        toast({
          title: "Info",
          description: "Inga artiklar att analysera",
          type: "default",
        });
        return;
      }
      
      // Run batch spam analysis
      const analysisResponse = await fetch('/api/proxy/api/intelligence/spam/batch-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ article_ids: articleIds })
      });
      
      if (!analysisResponse.ok) {
        throw new Error('Failed to run spam analysis');
      }
      
      const analysisData = await analysisResponse.json();
      
      toast({
        title: "Analys Klar",
        description: `Analyserade ${analysisData.summary.total_articles} artiklar. ${analysisData.summary.spam_detected} spam hittades.`,
        type: "success",
      });
      
      // Refresh the spam reports to show newly detected spam
      fetchSpamReports(1);
      
    } catch (error) {
      console.error('Error running spam analysis:', error);
      toast({
        title: "Fel",
        description: "Kunde inte köra spam-analys",
        type: "error",
      });
    } finally {
      setActionLoading(null);
    }
  };

  useEffect(() => {
    fetchSpamReports(1);
  }, []);

  const loadMore = () => {
    if (spamReports.length < total) {
      fetchSpamReports(page + 1);
    }
  };

  if (loading && page === 1) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Hämtar spam-rapporter...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-orange-500" />
            Spam & Oönskade Artiklar
          </h2>
          <p className="text-gray-600 mt-1">
            Hantera artiklar som har filtrerats bort som spam eller reklam
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => fetchSpamReports(1)}
            variant="outline"
            size="sm"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Uppdatera
          </Button>
          <Button
            onClick={runSpamAnalysis}
            variant="default"
            size="sm"
            disabled={actionLoading !== null}
          >
            <AlertTriangle className="h-4 w-4 mr-2" />
            {actionLoading ? 'Analyserar...' : 'Kör Spam-Analys'}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Totala Rapporter</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{total}</div>
            <p className="text-xs text-gray-600">spam-rapporter</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Automatiskt Filtrerade</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {spamReports.filter(r => r.report_source === 'ml_detection').length}
            </div>
            <p className="text-xs text-gray-600">av AI-system</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Användarrapporter</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {spamReports.filter(r => r.report_source === 'user_feedback').length}
            </div>
            <p className="text-xs text-gray-600">från användare</p>
          </CardContent>
        </Card>
      </div>

      {spamReports.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertTriangle className="h-12 w-12 text-green-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">Inga Spam-Artiklar</h3>
            <p className="text-gray-600 text-center">
              Inga artiklar har rapporterats som spam eller reklam ännu.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {spamReports.map((report) => (
            <Card key={report.article_id} className="border-orange-200">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg leading-tight mb-2">
                      {report.title}
                    </CardTitle>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary" className="text-xs">
                        {report.source}
                      </Badge>
                      <Badge 
                        variant={report.report_source === 'user_feedback' ? 'destructive' : 'outline'}
                        className="text-xs"
                      >
                        {report.report_source === 'user_feedback' ? 'Användarrapport' : 'Auto-detekterad'}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        Spam Score: {(report.spam_score * 100).toFixed(0)}%
                      </Badge>
                      {report.quality_score && (
                        <Badge variant="outline" className="text-xs">
                          Kvalitet: {report.quality_score}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-3">
                  <div className="text-sm text-gray-600">
                    <p><strong>Anledning:</strong> {report.reason}</p>
                    <p><strong>Rapporterad:</strong> {new Date(report.reported_at).toLocaleString('sv-SE')}</p>
                    {report.report_count > 1 && (
                      <p><strong>Antal rapporter:</strong> {report.report_count}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      onClick={() => restoreArticle(report.article_id)}
                      disabled={actionLoading === report.article_id}
                      size="sm"
                      variant="outline"
                      className="text-green-600 hover:text-green-700"
                    >
                      <RotateCcw className="h-4 w-4 mr-2" />
                      {actionLoading === report.article_id ? 'Återställer...' : 'Återställ'}
                    </Button>
                    
                    <Button
                      onClick={() => {
                        // Convert spam report to article format for reader
                        const article: Article = {
                          id: report.article_id,
                          title: report.title,
                          url: report.url,
                          source: report.source,
                          published_at: report.reported_at,
                          content: '',
                          summary: '',
                          score_total: report.quality_score ?? 0,
                          scores: {},
                          image_proxy_path: undefined,
                          guid: '',
                          tags: []
                        };
                        onArticleClick?.(article);
                      }}
                      size="sm"
                      variant="outline"
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      Förhandsgranska
                    </Button>

                    <Button
                      onClick={() => window.open(report.url, '_blank')}
                      size="sm"
                      variant="outline"
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Öppna källa
                    </Button>

                    <Button
                      onClick={() => permanentlyDelete(report.article_id)}
                      disabled={actionLoading === report.article_id}
                      size="sm"
                      variant="destructive"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Ta bort permanent
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {spamReports.length < total && (
            <div className="flex justify-center pt-4">
              <Button 
                onClick={loadMore}
                variant="outline"
                disabled={loading}
              >
                {loading ? 'Laddar...' : `Visa fler (${spamReports.length} av ${total})`}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}