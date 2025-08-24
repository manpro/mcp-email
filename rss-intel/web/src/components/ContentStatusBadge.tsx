'use client';

import { Badge } from '@/components/ui/badge';
import { Tooltip } from '@/components/ui/tooltip';
import { Download, CheckCircle, XCircle, Clock, FileText, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ContentStatusBadgeProps {
  status?: string;
  error?: string;
  extractedAt?: string;
  hasFullContent?: boolean;
  className?: string;
}

export function ContentStatusBadge({
  status,
  error,
  extractedAt,
  hasFullContent,
  className
}: ContentStatusBadgeProps) {
  const getStatusInfo = () => {
    if (status === 'success' || hasFullContent) {
      return {
        icon: CheckCircle,
        text: 'Downloaded',
        variant: 'success' as const,
        color: 'text-green-600',
        bgColor: 'bg-green-50 border-green-200',
        tooltip: `Content extracted successfully${extractedAt ? ` on ${new Date(extractedAt).toLocaleDateString()}` : ''}`
      };
    }
    
    if (status === 'failed') {
      return {
        icon: XCircle,
        text: 'Failed',
        variant: 'destructive' as const,
        color: 'text-red-600',
        bgColor: 'bg-red-50 border-red-200',
        tooltip: error ? `Extraction failed: ${error}` : 'Content extraction failed'
      };
    }
    
    if (status === 'skipped') {
      return {
        icon: AlertCircle,
        text: 'Skipped',
        variant: 'secondary' as const,
        color: 'text-gray-500',
        bgColor: 'bg-gray-50 border-gray-200',
        tooltip: error || 'Content extraction skipped'
      };
    }
    
    if (status === 'processing') {
      return {
        icon: Download,
        text: 'Processing',
        variant: 'secondary' as const,
        color: 'text-blue-600',
        bgColor: 'bg-blue-50 border-blue-200',
        tooltip: 'Content extraction in progress'
      };
    }
    
    // Default: pending or no status
    return {
      icon: Clock,
      text: 'Pending',
      variant: 'outline' as const,
      color: 'text-gray-400',
      bgColor: 'bg-gray-50 border-gray-300',
      tooltip: 'Content extraction not started'
    };
  };

  const statusInfo = getStatusInfo();
  const Icon = statusInfo.icon;

  return (
    <Tooltip content={statusInfo.tooltip}>
      <Badge 
        variant={statusInfo.variant}
        className={cn(
          'text-xs flex items-center gap-1 px-2 py-1',
          statusInfo.bgColor,
          statusInfo.color,
          className
        )}
      >
        <Icon className="h-3 w-3" />
        {statusInfo.text}
      </Badge>
    </Tooltip>
  );
}