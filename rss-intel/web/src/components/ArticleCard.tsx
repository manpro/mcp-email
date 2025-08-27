'use client';

import { Article } from '@/lib/api';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { ArticleImage } from './ArticleImage';
import { ClientTime } from './ClientTime';
import ScoreBadge from './ScoreBadge';
import { Star, ExternalLink, Check, BookOpen, Download, ThumbsDown, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ArticleCardProps {
  article: Article;
  onAction: (entryId: string, action: string, label?: string) => void;
  loading: boolean;
  imageProxyBase?: string;
  onExtractContent?: (articleId: number) => void;
  onArticleClick?: (article: Article) => void;
  onReportSpam?: (articleId: number) => void;
}

export function ArticleCard({
  article,
  onAction,
  loading,
  imageProxyBase = "/img",
  onExtractContent,
  onArticleClick,
  onReportSpam
}: ArticleCardProps) {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const imageUrl = article.image_proxy_path 
    ? `${backendUrl}/img/${article.image_proxy_path}`
    : undefined;

  return (
    <Card className="flex flex-col h-full hover:shadow-md transition-shadow">
      {/* Image */}
      {imageUrl && (
        <div className="aspect-video w-full overflow-hidden rounded-t-lg">
          <ArticleImage
            src={imageUrl}
            alt={article.title}
            width={article.image_width || 400}
            height={article.image_height || 250}
            blurhash={article.image_blurhash}
            className="w-full h-full"
          />
        </div>
      )}

      <CardContent className="flex-1 p-4">
        {/* Header with source and score */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="secondary" className="text-xs">
              {article.source}
            </Badge>
            <ScoreBadge 
              score={article.score_total} 
              breakdown={article.scores}
            />
            {/* Simple text status indicator */}
            <Badge variant="outline" className="text-xs">
              {article.url?.includes('example.com') ? '📄 Test Article' : 
               article.extraction_status === 'success' ? '✅ Downloaded' : 
               article.extraction_status === 'failed' ? '❌ Failed' : '⏳ Pending'}
            </Badge>
          </div>
          <Tooltip content={
            <div>
              <div>Published: {new Date(article.published_at).toLocaleString()}</div>
              <div>Fetched: {new Date(article.created_at).toLocaleString()}</div>
              {article.extracted_at && (
                <div>Extracted: {new Date(article.extracted_at).toLocaleString()}</div>
              )}
            </div>
          }>
            <div className="text-xs text-muted-foreground">
              <ClientTime date={article.published_at} format="relative" />
            </div>
          </Tooltip>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-sm leading-tight mb-2 line-clamp-2">
          <button
            onClick={() => onArticleClick?.(article)}
            className="hover:text-primary-600 hover:underline text-left"
          >
            {article.title}
          </button>
        </h3>

        {/* Content preview */}
        {article.content && (
          <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3 mb-3">
            {article.content}
          </p>
        )}

        {/* Labels/Topics */}
        <div className="flex gap-1 flex-wrap mb-3">
          {article.flags?.hot && (
            <Badge variant="destructive" className="text-xs">
              🔥 Hot
            </Badge>
          )}
          {article.flags?.interesting && (
            <Badge className="text-xs bg-amber-100 text-amber-800">
              ✨ Interesting
            </Badge>
          )}
          {article.flags?.starred && (
            <Badge className="text-xs bg-yellow-100 text-yellow-800">
              ⭐ Starred
            </Badge>
          )}
          {article.flags?.downvoted && (
            <Badge className="text-xs bg-red-100 text-red-800">
              👎 Poor Quality
            </Badge>
          )}
          {article.topics?.slice(0, 2).map((topic) => (
            <Badge key={topic} variant="outline" className="text-xs">
              {topic}
            </Badge>
          ))}
        </div>
      </CardContent>

      {/* Actions */}
      <CardFooter className="p-4 pt-0">
        <div className="flex gap-2 w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAction(
              article.freshrss_entry_id,
              article.flags?.starred ? 'unstar' : 'star'
            )}
            disabled={loading}
            className={cn(
              "flex-1",
              article.flags?.starred 
                ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100' 
                : 'hover:bg-gray-100'
            )}
          >
            <Star 
              className={cn(
                "h-4 w-4 mr-2",
                article.flags?.starred ? "fill-current" : ""
              )} 
            />
            {article.flags?.starred ? 'Starred' : 'Star'}
          </Button>
          
          {article.score_total >= 80 && !article.flags?.hot && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAction(article.freshrss_entry_id, 'label_add', 'hot')}
              disabled={loading}
              className="px-3"
            >
              + Hot
            </Button>
          )}
          
          {article.score_total >= 60 && !article.flags?.interesting && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAction(article.freshrss_entry_id, 'label_add', 'interesting')}
              disabled={loading}
              className="px-3"
            >
              + Int
            </Button>
          )}
          
          {!article.flags?.read && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAction(article.freshrss_entry_id, 'mark_read')}
              disabled={loading}
              className="px-3"
            >
              <Check className="h-4 w-4" />
            </Button>
          )}
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAction(
              article.freshrss_entry_id,
              article.flags?.downvoted ? 'undownvote' : 'downvote'
            )}
            disabled={loading}
            className={cn(
              "px-3",
              article.flags?.downvoted 
                ? 'text-red-600 bg-red-50 hover:bg-red-100' 
                : 'hover:bg-gray-100'
            )}
            title={article.flags?.downvoted ? "Remove downvote" : "Mark as poor quality"}
          >
            <ThumbsDown 
              className={cn(
                "h-4 w-4",
                article.flags?.downvoted ? "fill-current" : ""
              )} 
            />
          </Button>
          
          {article.extraction_status !== 'success' && !article.full_content && onExtractContent && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onExtractContent(article.id)}
              disabled={loading || article.extraction_status === 'processing'}
              className="px-3"
              title="Extract full content"
            >
              <Download className="h-4 w-4" />
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => onArticleClick?.(article)}
            disabled={loading}
            className="px-3"
            title="Read saved copy"
          >
            <BookOpen className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="sm"
            asChild
            className="px-3"
            title="Open original article"
          >
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>

          {onReportSpam && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onReportSpam(article.id)}
              disabled={loading}
              className="px-3 text-orange-600 hover:bg-orange-50"
              title="Report as spam/advertisement"
            >
              <AlertTriangle className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}