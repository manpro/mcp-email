'use client'

import { ExternalLink, Calendar, Globe, BarChart3, Clock } from 'lucide-react'
import { Card, CardContent } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'

interface SourceCardProps {
  title: string
  url: string
  source: string
  publishedAt: string
  excerpt?: string
  language?: string
  relevanceScore?: number
  readTime?: number
  imageUrl?: string
  compact?: boolean
  onClick?: () => void
}

export function SourceCard({
  title,
  url,
  source,
  publishedAt,
  excerpt,
  language,
  relevanceScore,
  readTime,
  imageUrl,
  compact = false,
  onClick
}: SourceCardProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffHours < 48) return 'Yesterday'
    if (diffHours < 168) return `${Math.floor(diffHours / 24)}d ago`
    return date.toLocaleDateString()
  }

  const getRelevanceBadge = (score: number) => {
    if (score >= 0.8) return { variant: 'default' as const, label: 'High match' }
    if (score >= 0.6) return { variant: 'secondary' as const, label: 'Good match' }
    return { variant: 'outline' as const, label: 'Relevant' }
  }

  const handleClick = () => {
    if (onClick) {
      onClick()
    } else {
      window.open(url, '_blank')
    }
  }

  if (compact) {
    return (
      <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={handleClick}>
        <CardContent className="p-3">
          <div className="flex justify-between items-start gap-3">
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm line-clamp-2 mb-1">
                {title}
              </h4>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>{source}</span>
                <span>•</span>
                <span>{formatDate(publishedAt)}</span>
                {relevanceScore && (
                  <>
                    <span>•</span>
                    <span>{Math.round(relevanceScore * 100)}%</span>
                  </>
                )}
              </div>
            </div>
            <ExternalLink className="h-4 w-4 text-gray-400 flex-shrink-0" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="hover:shadow-lg transition-shadow overflow-hidden">
      <div className="flex">
        {imageUrl && (
          <div className="w-48 h-32 flex-shrink-0">
            <img 
              src={imageUrl} 
              alt={title}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          </div>
        )}
        
        <CardContent className="flex-1 p-4">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex justify-between items-start gap-2">
              <h3 className="font-semibold text-base line-clamp-2 flex-1">
                {title}
              </h3>
              {relevanceScore && (
                <Badge {...getRelevanceBadge(relevanceScore)}>
                  <BarChart3 className="h-3 w-3 mr-1" />
                  {Math.round(relevanceScore * 100)}%
                </Badge>
              )}
            </div>

            {/* Excerpt */}
            {excerpt && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                {excerpt}
              </p>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Globe className="h-3 w-3" />
                <span>{source}</span>
              </div>
              
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>{formatDate(publishedAt)}</span>
              </div>
              
              {language && (
                <Badge variant="outline" className="text-xs">
                  {language.toUpperCase()}
                </Badge>
              )}
              
              {readTime && (
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{readTime} min read</span>
                </div>
              )}
            </div>

            {/* Action */}
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClick}
                className="flex items-center gap-1"
              >
                <ExternalLink className="h-3 w-3" />
                Open Article
              </Button>
            </div>
          </div>
        </CardContent>
      </div>
    </Card>
  )
}