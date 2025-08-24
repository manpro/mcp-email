'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Command, ArrowRight, X, Loader2 } from 'lucide-react'
import { Input } from './ui/input'
import { Badge } from './ui/badge'
import debounce from 'lodash/debounce'

interface QuickResult {
  id: string
  title: string
  type: 'article' | 'search' | 'ask'
  url?: string
  description?: string
}

export function GlobalSearch() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<QuickResult[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to open search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen(true)
        inputRef.current?.focus()
      }

      // Escape to close
      if (e.key === 'Escape') {
        setIsOpen(false)
        setQuery('')
      }

      // Navigate results with arrow keys
      if (isOpen && results.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault()
          setSelectedIndex(i => (i + 1) % results.length)
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          setSelectedIndex(i => (i - 1 + results.length) % results.length)
        } else if (e.key === 'Enter') {
          e.preventDefault()
          handleSelectResult(results[selectedIndex])
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, results, selectedIndex])

  const searchQuick = debounce(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([])
      return
    }

    setLoading(true)
    try {
      // Quick search - get top 5 results
      const response = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}&limit=5`)
      const data = await response.json()
      
      const quickResults: QuickResult[] = []
      
      // Add article results
      if (data.results) {
        data.results.forEach((item: any) => {
          quickResults.push({
            id: item.id,
            title: item.title,
            type: 'article',
            url: item.url,
            description: item.content?.substring(0, 100) + '...'
          })
        })
      }

      // Add search option
      quickResults.push({
        id: 'search-all',
        title: `Search for "${searchQuery}"`,
        type: 'search',
        description: 'View all search results'
      })

      // Add ask option
      quickResults.push({
        id: 'ask-question',
        title: `Ask: "${searchQuery}"`,
        type: 'ask',
        description: 'Get an AI-powered answer with citations'
      })

      setResults(quickResults)
      setSelectedIndex(0)
    } catch (error) {
      console.error('Quick search error:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, 300)

  const handleSelectResult = (result: QuickResult) => {
    if (result.type === 'article' && result.url) {
      window.open(result.url, '_blank')
    } else if (result.type === 'search') {
      router.push(`/?tab=search&q=${encodeURIComponent(query)}`)
    } else if (result.type === 'ask') {
      router.push(`/?tab=ask&q=${encodeURIComponent(query)}`)
    }
    
    setIsOpen(false)
    setQuery('')
    setResults([])
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'article':
        return <Badge variant="outline" className="text-xs">Article</Badge>
      case 'search':
        return <Badge variant="secondary" className="text-xs">Search</Badge>
      case 'ask':
        return <Badge className="text-xs">Ask AI</Badge>
      default:
        return null
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
        <Input
          ref={inputRef}
          type="search"
          placeholder="Search or ask... (⌘K)"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            searchQuick(e.target.value)
          }}
          onFocus={() => setIsOpen(true)}
          className="pl-9 pr-9 w-64 lg:w-96 h-9"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('')
              setResults([])
            }}
            className="absolute right-3 top-1/2 transform -translate-y-1/2"
          >
            <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
          </button>
        )}
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin text-gray-400" />
        )}
      </div>

      {/* Quick Results Dropdown */}
      {isOpen && (query || results.length > 0) && (
        <div className="absolute top-full mt-2 w-full bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 max-h-96 overflow-y-auto">
          {loading && !results.length ? (
            <div className="p-4 text-center text-sm text-gray-500">
              Searching...
            </div>
          ) : results.length > 0 ? (
            <div className="py-2">
              {results.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => handleSelectResult(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`w-full px-4 py-3 flex items-start gap-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                    index === selectedIndex ? 'bg-gray-50 dark:bg-gray-800' : ''
                  }`}
                >
                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-2 mb-1">
                      {getTypeIcon(result.type)}
                      <span className="text-sm font-medium line-clamp-1">
                        {result.title}
                      </span>
                    </div>
                    {result.description && (
                      <p className="text-xs text-gray-500 line-clamp-1">
                        {result.description}
                      </p>
                    )}
                  </div>
                  <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0 mt-1" />
                </button>
              ))}
            </div>
          ) : query ? (
            <div className="p-4 text-center text-sm text-gray-500">
              Type to search across all content...
            </div>
          ) : null}

          {/* Keyboard shortcuts hint */}
          <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center justify-between text-xs text-gray-500">
            <div className="flex gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">↑↓</kbd>
                Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">↵</kbd>
                Select
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">Esc</kbd>
                Close
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}