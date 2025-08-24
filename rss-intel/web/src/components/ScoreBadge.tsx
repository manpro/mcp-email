'use client';

import { Badge } from '@/components/ui/badge';
import { Tooltip } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface ScoreBadgeProps {
  score: number;
  breakdown?: Record<string, any>;
  threshold?: {
    star: number;
    interesting: number;
  };
  className?: string;
}

export default function ScoreBadge({ 
  score, 
  breakdown, 
  threshold = { star: 80, interesting: 60 },
  className 
}: ScoreBadgeProps) {
  const getScoreColor = () => {
    if (score >= threshold.star) return 'bg-red-100 text-red-800 border-red-200 hover:bg-red-200';
    if (score >= threshold.interesting) return 'bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200';
    return 'bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-200';
  };

  const getScoreLabel = () => {
    if (score >= threshold.star) return '🔥';
    if (score >= threshold.interesting) return '✨';
    return '';
  };

  const tooltipContent = breakdown ? (
    <div className="text-left">
      <div className="font-semibold mb-2">Score Breakdown</div>
      {breakdown.keywords && (
        <div>Keywords: {breakdown.keywords}</div>
      )}
      {breakdown.watchlist && (
        <div>Watchlist: {breakdown.watchlist}</div>
      )}
      {breakdown.source && (
        <div>Source: {breakdown.source}</div>
      )}
      {breakdown.image_bonus && (
        <div>Image: +{breakdown.image_bonus}</div>
      )}
      {breakdown.recency_factor && (
        <div>Recency: ×{breakdown.recency_factor}</div>
      )}
      {breakdown.base_score && (
        <div className="border-t pt-1 mt-1">
          Base: {breakdown.base_score} → Final: {score}
        </div>
      )}
    </div>
  ) : null;

  const badge = (
    <Badge
      variant="outline"
      className={cn(
        'font-medium cursor-pointer transition-colors',
        getScoreColor(),
        className
      )}
    >
      <span>{score}</span>
      {getScoreLabel() && <span className="ml-1">{getScoreLabel()}</span>}
    </Badge>
  );

  return tooltipContent ? (
    <Tooltip content={tooltipContent}>
      {badge}
    </Tooltip>
  ) : (
    badge
  );
}