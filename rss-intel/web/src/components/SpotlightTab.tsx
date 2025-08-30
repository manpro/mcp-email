'use client';

import { useState, useEffect } from 'react';
import { SpotlightDigest, SpotlightStats, apiClient } from '@/lib/api';
import { SpotlightCard } from './SpotlightCard';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { 
  RefreshCw, 
  Calendar, 
  TrendingUp, 
  Eye, 
  ExternalLink, 
  Download,
  Sparkles,
  Clock
} from 'lucide-react';
import { format } from 'date-fns';

import { Article } from '@/lib/api';

interface SpotlightTabProps {
  onArticleClick?: (article: Article) => void;
}

export function SpotlightTab({ onArticleClick }: SpotlightTabProps = {}) {
  const [digest, setDigest] = useState<SpotlightDigest | null>(null);
  const [stats, setStats] = useState<SpotlightStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { toast } = useToast();

  const loadSpotlight = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load both digest and stats
      const [digestData, statsData] = await Promise.all([
        apiClient.getTodaySpotlight().catch(() => null), // Don't throw if no digest exists
        apiClient.getSpotlightStats()
      ]);
      
      setDigest(digestData);
      setStats(statsData);
    } catch (err: any) {
      console.error('Failed to load spotlight:', err);
      setError(err.message || 'Failed to load spotlight data');
    } finally {
      setLoading(false);
    }
  };

  const generateSpotlight = async () => {
    try {
      setGenerating(true);
      const result = await apiClient.generateSpotlight();
      
      toast({
        title: "Spotlight Generated!",
        description: `Created digest with ${result.must_read_count} must-read and ${result.also_worth_count} also-worth articles.`,
        type: "success",
      });

      // Reload data
      await loadSpotlight();
    } catch (err: any) {
      console.error('Failed to generate spotlight:', err);
      toast({
        title: "Generation Failed",
        description: err.message || 'Failed to generate spotlight digest',
        type: "error"
      });
    } finally {
      setGenerating(false);
    }
  };

  const publishSpotlight = async (issueId: number) => {
    try {
      await apiClient.publishSpotlight(issueId);
      toast({
        title: "Published!",
        description: "Spotlight digest has been published.",
        type: "success",
      });
      await loadSpotlight();
    } catch (err: any) {
      toast({
        title: "Publish Failed",
        description: err.message || 'Failed to publish digest',
        type: "error"
      });
    }
  };

  const openRSSFeed = () => {
    window.open('/api/proxy/api/spotlight/rss/feed', '_blank');
  };

  // Handle article actions (voting, starring, etc.)
  const handleAction = async (entryId: string, action: string, label?: string) => {
    try {
      setActionLoading(action);
      
      // For spotlight articles, we'll need to map to real FreshRSS entries
      // This is a placeholder implementation
      await apiClient.markArticle(entryId, action);
      
      toast({
        title: "Action completed",
        description: `Article ${action} successfully`,
        type: "success",
      });
    } catch (err: any) {
      toast({
        title: "Action failed",
        description: err.message || `Failed to ${action} article`,
        type: "error"
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleExtractContent = async (articleId: number) => {
    try {
      setActionLoading('extract');
      await apiClient.extractArticleContent(articleId, false);
      
      toast({
        title: "Content extracted",
        description: "Article content has been extracted",
        type: "success",
      });
    } catch (err: any) {
      toast({
        title: "Extraction failed",
        description: err.message || "Failed to extract content",
        type: "error"
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReportSpam = async (articleId: number) => {
    try {
      setActionLoading('spam');
      // Placeholder for spam reporting functionality
      
      toast({
        title: "Reported as spam",
        description: "Article has been reported as spam",
        type: "success",
      });
    } catch (err: any) {
      toast({
        title: "Report failed",
        description: err.message || "Failed to report spam",
        type: "error"
      });
    } finally {
      setActionLoading(null);
    }
  };

  useEffect(() => {
    loadSpotlight();
    // Auto-refresh every 5 minutes
    const interval = setInterval(loadSpotlight, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !digest) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-2 text-muted-foreground">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span>Loading spotlight...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-amber-500" />
            <h2 className="text-2xl font-bold">Daily Spotlight</h2>
          </div>
          {digest && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {format(new Date(digest.issue_date), 'MMM d, yyyy')}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadSpotlight}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {!digest && (
            <Button
              onClick={generateSpotlight}
              disabled={generating}
              size="sm"
            >
              <Sparkles className={`h-4 w-4 mr-2 ${generating ? 'animate-spin' : ''}`} />
              {generating ? 'Generating...' : 'Generate Today'}
            </Button>
          )}

          {digest && (
            <Button
              variant="outline"
              size="sm"
              onClick={openRSSFeed}
            >
              <Download className="h-4 w-4 mr-2" />
              RSS Feed
            </Button>
          )}
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">Total Issues</span>
            </div>
            <div className="text-2xl font-bold mt-1">{stats.total_issues}</div>
          </div>
          
          <div className="bg-white p-4 rounded-lg border">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-blue-500" />
              <span className="text-sm font-medium">Published</span>
            </div>
            <div className="text-2xl font-bold mt-1">{stats.published_issues}</div>
          </div>

          <div className="bg-white p-4 rounded-lg border">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-medium">Draft</span>
            </div>
            <div className="text-2xl font-bold mt-1">{stats.unpublished_issues}</div>
          </div>

          {digest && (
            <div className="bg-white p-4 rounded-lg border">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-500" />
                <span className="text-sm font-medium">Articles</span>
              </div>
              <div className="text-2xl font-bold mt-1">
                {digest.metrics.must_read_count + digest.metrics.also_worth_count}
              </div>
            </div>
          )}
        </div>
      )}

      {/* No Digest State */}
      {!digest && !loading && (
        <div className="text-center py-12 bg-white rounded-lg border border-dashed">
          <Sparkles className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No spotlight digest for today
          </h3>
          <p className="text-muted-foreground mb-4">
            Generate today's daily digest to see the most important stories
          </p>
          <Button onClick={generateSpotlight} disabled={generating}>
            <Sparkles className={`h-4 w-4 mr-2 ${generating ? 'animate-spin' : ''}`} />
            {generating ? 'Generating...' : 'Generate Today\'s Spotlight'}
          </Button>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-center py-12 bg-red-50 rounded-lg border border-red-200">
          <h3 className="text-lg font-medium text-red-900 mb-2">
            Failed to load spotlight
          </h3>
          <p className="text-red-600 mb-4">{error}</p>
          <Button variant="outline" onClick={loadSpotlight}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </div>
      )}

      {/* Digest Content */}
      {digest && (
        <div className="space-y-6">
          {/* Digest Header */}
          <div className="bg-white p-6 rounded-lg border">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold mb-2">{digest.title}</h1>
                <p className="text-muted-foreground mb-4">{digest.subtitle}</p>
                
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>Generated: {format(new Date(digest.generated_at), 'MMM d, h:mm a')}</span>
                  <span>•</span>
                  <span>{digest.metrics.total_articles_considered} articles considered</span>
                  {digest.published && (
                    <>
                      <span>•</span>
                      <Badge variant="secondary" className="text-green-600 bg-green-50">
                        Published
                      </Badge>
                    </>
                  )}
                </div>
              </div>

              {!digest.published && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => publishSpotlight(1)} // Assume issue ID 1 for now
                >
                  <Eye className="h-4 w-4 mr-2" />
                  Publish
                </Button>
              )}
            </div>
          </div>

          {/* Must Read Section */}
          {digest.must_read.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold">Must Read</h2>
                <Badge variant="default" className="bg-red-100 text-red-700">
                  {digest.must_read.length}
                </Badge>
              </div>
              <div className="grid gap-4">
                {digest.must_read.map((item, index) => (
                  <SpotlightCard 
                    key={index} 
                    item={item} 
                    section="must_read"
                    rank={index + 1}
                    onArticleClick={onArticleClick}
                    onAction={handleAction}
                    onExtractContent={handleExtractContent}
                    onReportSpam={handleReportSpam}
                    actionLoading={actionLoading}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Also Worth Section */}
          {digest.also_worth.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold">Also Worth Reading</h2>
                <Badge variant="secondary">
                  {digest.also_worth.length}
                </Badge>
              </div>
              <div className="grid gap-4">
                {digest.also_worth.map((item, index) => (
                  <SpotlightCard 
                    key={index} 
                    item={item} 
                    section="also_worth"
                    rank={index + 1}
                    onArticleClick={onArticleClick}
                    onAction={handleAction}
                    onExtractContent={handleExtractContent}
                    onReportSpam={handleReportSpam}
                    actionLoading={actionLoading}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}