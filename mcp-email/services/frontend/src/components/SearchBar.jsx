import { useState } from 'react'
import { Search, Sparkles } from 'lucide-react'
import useEmailStore from '../store/emailStore'
import { searchWithAI } from '../services/aiService'

export default function SearchBar() {
  const [query, setQuery] = useState('')
  const [isAiSearch, setIsAiSearch] = useState(true)
  const [isSearching, setIsSearching] = useState(false)
  const { setSearchQuery, setSearchResults, selectedAccountId } = useEmailStore()

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsSearching(true)
    setSearchQuery(query)

    try {
      if (isAiSearch) {
        // AI-powered natural language search
        const results = await searchWithAI(query, selectedAccountId)
        setSearchResults(results)
      } else {
        // Regular search via API
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
        const response = await fetch(`${apiUrl}/api/search?q=${encodeURIComponent(query)}${selectedAccountId ? `&account=${selectedAccountId}` : ''}`)
        const data = await response.json()
        setSearchResults(data.emails || [])
      }
    } catch (error) {
      console.error('Search failed:', error)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="p-4 border-b border-gray-200">
      <form onSubmit={handleSearch} className="space-y-2">
        <div className="relative">
          {isSearching ? (
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent"></div>
            </div>
          ) : (
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          )}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={isAiSearch ? "Sök med AI: 'Viktiga mail denna vecka'" : "Sök i emails..."}
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
            disabled={isSearching}
          />
        </div>

        <button
          type="button"
          onClick={() => setIsAiSearch(!isAiSearch)}
          className={`w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all ${
            isAiSearch
              ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <Sparkles className="w-3 h-3" />
          {isAiSearch ? 'AI Sökning Aktiv' : 'Aktivera AI Sökning'}
        </button>
      </form>
    </div>
  )
}