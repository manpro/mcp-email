'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Search, Filter, Globe, Calendar, ToggleLeft, ToggleRight, X } from 'lucide-react'
import { debounce } from 'lodash'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Card, CardContent } from './ui/card'
import { Badge } from './ui/badge'
import { Skeleton } from './ui/skeleton'

interface SearchResult {
  id: string
  title: string
  content: string
  url: string
  source: string
  published_at: string
  language: string
  score: number
  highlights: string[]
  reasons: string[]
}

interface SearchFilters {
  language?: string
  freshness?: string
  source?: string
  hybrid?: boolean
}

export function SearchTab() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<SearchFilters>({
    language: searchParams.get('lang') || undefined,
    freshness: searchParams.get('fresh') || undefined,
    source: searchParams.get('source') || undefined,
    hybrid: searchParams.get('hybrid') === 'true'
  })
  const [totalResults, setTotalResults] = useState(0)
  const [page, setPage] = useState(1)

  const performSearch = useCallback(async (searchQuery: string, searchFilters: SearchFilters, searchPage: number = 1) => {
    if (!searchQuery.trim()) {
      setResults([])
      setTotalResults(0)
      return
    }

    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('q', searchQuery)
      if (searchFilters.language) params.set('language', searchFilters.language)
      if (searchFilters.freshness) params.set('freshness', searchFilters.freshness)
      if (searchFilters.source) params.set('source', searchFilters.source)
      if (searchFilters.hybrid) params.set('hybrid', 'true')
      params.set('limit', '20')
      params.set('offset', String((searchPage - 1) * 20))

      const response = await fetch(`/api/search?${params}`)
      const data = await response.json()
      
      setResults(data.results || [])
      setTotalResults(data.total || 0)
      
      // Update URL
      const newParams = new URLSearchParams()
      newParams.set('q', searchQuery)
      Object.entries(searchFilters).forEach(([key, value]) => {
        if (value) newParams.set(key, String(value))
      })
      if (searchPage > 1) newParams.set('page', String(searchPage))
      
      router.push(`?${newParams.toString()}`, { scroll: false })
    } catch (error) {
      console.error('Search error:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [router])

  const debouncedSearch = useCallback(
    debounce((q: string, f: SearchFilters) => performSearch(q, f), 500),
    [performSearch]
  )

  useEffect(() => {
    if (query) {
      debouncedSearch(query, filters)
    }
  }, [query, filters, debouncedSearch])

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const clearFilter = (key: keyof SearchFilters) => {
    setFilters(prev => ({ ...prev, [key]: undefined }))
    setPage(1)
  }

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

  const highlightText = (text: string, highlights: string[]) => {
    if (!highlights || highlights.length === 0) return text
    
    let result = text
    highlights.forEach(highlight => {
      const regex = new RegExp(`(${highlight})`, 'gi')
      result = result.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>')
    })
    return result
  }

  return (
    <div className="space-y-6">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
        <Input
          type="search"
          placeholder="Search across all content..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 pr-4 py-2 text-lg"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <Select value={filters.language || ''} onValueChange={(v) => handleFilterChange('language', v || undefined)}>
          <SelectTrigger className="w-32">
            <Globe className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Language" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All</SelectItem>
            <SelectItem value="en">English</SelectItem>
            <SelectItem value="es">Spanish</SelectItem>
            <SelectItem value="fr">French</SelectItem>
            <SelectItem value="de">German</SelectItem>
            <SelectItem value="zh">Chinese</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filters.freshness || ''} onValueChange={(v) => handleFilterChange('freshness', v || undefined)}>
          <SelectTrigger className="w-32">
            <Calendar className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Freshness" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Any time</SelectItem>
            <SelectItem value="1h">Past hour</SelectItem>
            <SelectItem value="24h">Past 24 hours</SelectItem>
            <SelectItem value="7d">Past week</SelectItem>
            <SelectItem value="30d">Past month</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant={filters.hybrid ? "default" : "outline"}
          size="sm"
          onClick={() => handleFilterChange('hybrid', !filters.hybrid)}
          className="flex items-center gap-2"
        >
          {filters.hybrid ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
          Hybrid Search
        </Button>

        {/* Active Filters */}
        {Object.entries(filters).filter(([_, v]) => v).map(([key, value]) => (
          <Badge key={key} variant="secondary" className="flex items-center gap-1">
            {key}: {String(value)}
            <X 
              className="h-3 w-3 cursor-pointer" 
              onClick={() => clearFilter(key as keyof SearchFilters)}
            />
          </Badge>
        ))}
      </div>

      {/* Results Count */}
      {query && !loading && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {totalResults > 0 ? `Found ${totalResults} results` : 'No results found'}
        </div>
      )}

      {/* Search Results */}
      <div className="space-y-4">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full mb-1" />
                <Skeleton className="h-4 w-5/6" />
                <div className="flex gap-2 mt-4">
                  <Skeleton className="h-5 w-20" />
                  <Skeleton className="h-5 w-24" />
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          results.map((result) => (
            <Card key={result.id} className="hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => window.open(result.url, '_blank')}>
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-2 text-blue-600 dark:text-blue-400">
                  {result.title}
                </h3>
                
                <div 
                  className="text-gray-600 dark:text-gray-400 text-sm mb-3 line-clamp-3"
                  dangerouslySetInnerHTML={{ 
                    __html: highlightText(result.content, result.highlights || [])
                  }}
                />
                
                <div className="flex flex-wrap gap-2 items-center text-xs">
                  <Badge variant="outline">{result.source}</Badge>
                  <span className="text-gray-500">{formatDate(result.published_at)}</span>
                  {result.language && (
                    <Badge variant="secondary">{result.language.toUpperCase()}</Badge>
                  )}
                  {result.score > 0.8 && (
                    <Badge variant="default">High relevance</Badge>
                  )}
                </div>

                {result.reasons && result.reasons.length > 0 && (
                  <div className="flex gap-2 mt-3">
                    {result.reasons.map((reason, i) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        WHY: {reason}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalResults > 20 && (
        <div className="flex justify-center gap-2 mt-6">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => {
              setPage(p => p - 1)
              performSearch(query, filters, page - 1)
            }}
          >
            Previous
          </Button>
          <span className="flex items-center px-4">
            Page {page} of {Math.ceil(totalResults / 20)}
          </span>
          <Button
            variant="outline"
            disabled={page >= Math.ceil(totalResults / 20)}
            onClick={() => {
              setPage(p => p + 1)
              performSearch(query, filters, page + 1)
            }}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}