'use client';

import { clsx } from 'clsx';

interface ScoreBadgeProps {
  score: number;
  threshold?: {
    star: number;
    interesting: number;
  };
}

export default function ScoreBadge({ score, threshold = { star: 80, interesting: 60 } }: ScoreBadgeProps) {
  const getScoreColor = () => {
    if (score >= threshold.star) return 'bg-red-100 text-red-800 border-red-200';
    if (score >= threshold.interesting) return 'bg-amber-100 text-amber-800 border-amber-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getScoreLabel = () => {
    if (score >= threshold.star) return '🔥';
    if (score >= threshold.interesting) return '✨';
    return '';
  };

  return (
    <div className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
      getScoreColor()
    )}>
      <span>{score}</span>
      {getScoreLabel() && <span className="ml-1">{getScoreLabel()}</span>}
    </div>
  );
}