'use client';

import { useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Article } from '@/lib/api';
import { ArticleCard } from './ArticleCard';
import { ArticleImage } from './ArticleImage';
import { ClientTime } from './ClientTime';
import ScoreBadge from './ScoreBadge';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { Star, ExternalLink, Check, ThumbsDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ViewMode = 'list' | 'cards';

interface VirtualizedListProps {
  articles: Article[];
  viewMode: ViewMode;
  onAction: (entryId: string, action: string, label?: string) => void;
  onExtractContent?: (articleId: number) => void;
  loading: string | null;
  imageProxyBase?: string;
  onArticleClick?: (article: Article) => void;
  onReportSpam?: (articleId: number) => void;
}

export function VirtualizedList({
  articles,
  viewMode,
  onAction,
  onExtractContent,
  loading,
  imageProxyBase = "/img",
  onArticleClick,
  onReportSpam
}: VirtualizedListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const columnCount = viewMode === 'cards' ? 3 : 1;
  
  // For cards, we virtualize by rows (each virtual item is a row of cards)
  // For list, we virtualize by individual articles
  const virtualCount = viewMode === 'cards' 
    ? Math.ceil(articles.length / columnCount)
    : articles.length;

  const rowVirtualizer = useVirtualizer({
    count: virtualCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => (viewMode === 'cards' ? 450 : 120), // Further increased card row height
    overscan: 5,
  });

  const renderListItem = (article: Article, isLoading: boolean) => (
    <div className="flex items-start gap-4 p-4 border-b hover:bg-gray-50 transition-colors">
      {/* Image thumbnail */}
      {article.has_image && article.image_proxy_path && (
        <div className="flex-shrink-0 w-14 h-14 rounded overflow-hidden">
          <ArticleImage
            src={`${imageProxyBase}/${article.image_proxy_path}`}
            alt={article.title}
            width={56}
            height={56}
            blurhash={article.image_blurhash}
            className="w-full h-full"
          />
        </div>
      )}
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <ScoreBadge 
              score={article.score_total} 
              breakdown={article.scores}
            />
            <Badge variant="secondary" className="text-xs">
              {article.source}
            </Badge>
          </div>
          <Tooltip content={
            <div>
              <div>Published: {new Date(article.published_at).toLocaleString()}</div>
              <div>Fetched: {new Date(article.created_at).toLocaleString()}</div>
            </div>
          }>
            <div className="text-xs text-muted-foreground">
              <ClientTime date={article.published_at} format="relative" />
            </div>
          </Tooltip>
        </div>

        <h3 className="font-medium text-sm leading-tight mb-2">
          <button
            onClick={() => onArticleClick?.(article)}
            className="hover:text-primary-600 hover:underline text-left"
          >
            {article.title}
          </button>
        </h3>

        {article.content && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
            {article.content}
          </p>
        )}

        {/* Labels */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 flex-wrap">
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
            {article.topics?.slice(0, 3).map((topic) => (
              <Badge key={topic} variant="outline" className="text-xs">
                {topic}
              </Badge>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAction(
                article.freshrss_entry_id,
                article.flags?.starred ? 'unstar' : 'star'
              )}
              disabled={isLoading}
              className={cn(
                "px-2",
                article.flags?.starred 
                  ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100' 
                  : 'hover:bg-gray-100'
              )}
            >
              <Star 
                className={cn(
                  "h-4 w-4",
                  article.flags?.starred ? "fill-current" : ""
                )} 
              />
            </Button>
            
            {article.score_total >= 80 && !article.flags?.hot && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onAction(article.freshrss_entry_id, 'label_add', 'hot')}
                disabled={isLoading}
                className="px-2 text-xs"
              >
                + Hot
              </Button>
            )}
            
            {!article.flags?.read && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onAction(article.freshrss_entry_id, 'mark_read')}
                disabled={isLoading}
                className="px-2"
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
              disabled={isLoading}
              className={cn(
                "px-2",
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

            <Button
              variant="ghost"
              size="sm"
              asChild
              className="px-2"
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
          </div>
        </div>
      </div>
    </div>
  );

  const renderCardGrid = (startIndex: number) => {
    const itemsInRow = Math.min(columnCount, articles.length - startIndex);
    const items = [];
    
    for (let i = 0; i < itemsInRow; i++) {
      const article = articles[startIndex + i];
      if (article) {
        items.push(
          <div key={article.id} className="w-full">
            <ArticleCard
              article={article}
              onAction={onAction}
              onExtractContent={onExtractContent}
              onArticleClick={onArticleClick}
              onReportSpam={onReportSpam}
              loading={loading === article.freshrss_entry_id || loading === `extract_${article.id}`}
              imageProxyBase={imageProxyBase}
            />
          </div>
        );
      }
    }
    
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4 pb-8">
        {items}
      </div>
    );
  };

  const virtualItems = rowVirtualizer.getVirtualItems();

  return (
    <div
      ref={parentRef}
      className="h-full overflow-auto"
      style={{ contain: 'strict' }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualItems.map((virtualItem) => {
          const { index } = virtualItem;
          
          if (viewMode === 'cards') {
            // For cards, each virtual item represents a row of cards
            const startIndex = index * columnCount;
            // Make sure we don't render beyond available articles
            const endIndex = Math.min(startIndex + columnCount, articles.length);
            const articlesInRow = articles.slice(startIndex, endIndex);
            
            if (articlesInRow.length === 0) return null;
            
            return (
              <div
                key={`row-${index}`}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualItem.size}px`,
                  transform: `translateY(${virtualItem.start}px)`,
                }}
              >
                {renderCardGrid(startIndex)}
              </div>
            );
          } else {
            // For list, each virtual item is a single article
            const article = articles[index];
            if (!article) return null;
            
            return (
              <div
                key={article.id}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualItem.size}px`,
                  transform: `translateY(${virtualItem.start}px)`,
                }}
              >
                {renderListItem(article, loading === article.freshrss_entry_id)}
              </div>
            );
          }
        })}
      </div>
    </div>
  );
}