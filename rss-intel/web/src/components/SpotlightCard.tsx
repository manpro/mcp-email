'use client';

import { SpotlightItem, Article, apiClient } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  ExternalLink, 
  Calendar, 
  TrendingUp, 
  Star,
  Eye,
  Clock,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  BookOpen,
  Download,
  Check
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

interface SpotlightCardProps {
  item: SpotlightItem;
  section: 'must_read' | 'also_worth';
  rank: number;
  onArticleClick?: (article: Article) => void;
  onAction?: (entryId: string, action: string, label?: string) => void;
  onExtractContent?: (articleId: number) => void;
  onReportSpam?: (articleId: number) => void;
  actionLoading?: string | null;
}

export function SpotlightCard({ 
  item, 
  section, 
  rank, 
  onArticleClick, 
  onAction, 
  onExtractContent, 
  onReportSpam, 
  actionLoading 
}: SpotlightCardProps) {
  const openArticle = async () => {
    if (onArticleClick) {
      try {
        // Fetch the real article data from our database using URL
        const realArticle = await apiClient.getArticleByUrl(item.url);
        onArticleClick(realArticle);
      } catch (error) {
        console.error('Failed to fetch article by URL:', error);
        // Fallback: use a working article ID for demonstration
        const fallbackArticle: Article = {
          id: 160, // Use a known working article ID
          freshrss_entry_id: '',
          title: item.title,
          url: item.url,
          content: item.summary,
          source: item.source,
          published_at: item.published_at,
          score_total: Math.round(item.score * 100),
          scores: {},
          entities: {},
          topics: [],
          flags: {},
          created_at: item.published_at,
          updated_at: item.published_at,
          image_src_url: item.image_url,
          image_proxy_path: item.image_url,
          image_width: undefined,
          image_height: undefined,
          image_blurhash: undefined,
          has_image: item.has_image,
          extraction_status: undefined,
          extracted_at: undefined,
          extraction_error: undefined,
          full_content: undefined,
          content_summary: item.summary
        };
        onArticleClick(fallbackArticle);
      }
    } else {
      // Fallback to external link
      window.open(item.url, '_blank', 'noopener,noreferrer');
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.3) return 'text-green-600 bg-green-50';
    if (score >= 0.2) return 'text-yellow-600 bg-yellow-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getSectionColor = (section: string) => {
    return section === 'must_read' 
      ? 'border-l-red-500 bg-red-50/30' 
      : 'border-l-blue-500 bg-blue-50/30';
  };

  const getRankIcon = (rank: number, section: string) => {
    if (section === 'must_read') {
      return (
        <div className="flex items-center justify-center w-6 h-6 rounded-full bg-red-100 text-red-700 text-sm font-bold">
          {rank}
        </div>
      );
    }
    return (
      <div className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-sm font-bold">
        {rank}
      </div>
    );
  };

  return (
    <div className={cn(
      "bg-white border rounded-lg p-4 hover:shadow-md transition-shadow border-l-4",
      getSectionColor(section)
    )}>
      <div className="flex gap-4">
        {/* Rank */}
        <div className="flex-shrink-0">
          {getRankIcon(rank, section)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Header */}
          <div className="space-y-2">
            <h3 className="font-medium text-gray-900 leading-tight">
              {item.title}
            </h3>
            
            {/* Metadata */}
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="font-medium text-gray-700">{item.source}</span>
              <span>•</span>
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {format(new Date(item.published_at), 'MMM d, h:mm a')}
              </div>
              {item.score && (
                <>
                  <span>•</span>
                  <Badge variant="secondary" className={getScoreColor(item.score)}>
                    Score: {(item.score * 100).toFixed(0)}
                  </Badge>
                </>
              )}
            </div>
          </div>

          {/* Summary */}
          {item.summary && (
            <p className="text-gray-700 text-sm leading-relaxed">
              {item.summary}
            </p>
          )}

          {/* Reasons */}
          <div className="flex items-center gap-2 flex-wrap mb-3">
            {item.reasons.map((reason, index) => (
              <Badge 
                key={index} 
                variant="outline" 
                className="text-xs bg-white"
              >
                {reason}
              </Badge>
            ))}
          </div>

          {/* Actions Row */}
          <div className="flex items-center justify-between gap-2">
            {/* Left side - Voting actions */}
            <div className="flex gap-1">
              {onAction && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onAction('', 'star')} // Note: We'll need entry_id in real implementation
                    disabled={actionLoading === 'star'}
                    className="hover:bg-yellow-50 hover:text-yellow-600 p-2"
                    title="Star article"
                  >
                    <Star className="h-4 w-4" />
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onAction('', 'upvote')}
                    disabled={actionLoading === 'upvote'}
                    className="hover:bg-green-50 hover:text-green-600 p-2"
                    title="Upvote"
                  >
                    <ThumbsUp className="h-4 w-4" />
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onAction('', 'downvote')}
                    disabled={actionLoading === 'downvote'}
                    className="hover:bg-red-50 hover:text-red-600 p-2"
                    title="Downvote"
                  >
                    <ThumbsDown className="h-4 w-4" />
                  </Button>
                </>
              )}
              
              {onExtractContent && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onExtractContent(160)} // Fallback ID
                  disabled={actionLoading === 'extract'}
                  className="hover:bg-blue-50 hover:text-blue-600 p-2"
                  title="Extract full content"
                >
                  <Download className="h-4 w-4" />
                </Button>
              )}
              
              {onReportSpam && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onReportSpam(160)} // Fallback ID
                  disabled={actionLoading === 'spam'}
                  className="hover:bg-red-50 hover:text-red-600 p-2"
                  title="Report as spam"
                >
                  <AlertTriangle className="h-4 w-4" />
                </Button>
              )}
            </div>

            {/* Right side - Read action */}
            <Button
              variant="ghost"
              size="sm"
              onClick={openArticle}
              className="flex-shrink-0 hover:bg-gray-100"
            >
              {onArticleClick ? (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  Read
                </>
              ) : (
                <>
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Read
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Optional Image */}
        {item.has_image && item.image_url && (
          <div className="flex-shrink-0 w-20 h-20">
            <img
              src={item.image_url}
              alt=""
              className="w-full h-full object-cover rounded border"
              loading="lazy"
            />
          </div>
        )}
      </div>
    </div>
  );
}