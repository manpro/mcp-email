import { useState } from 'react'
import { X, Search, Sparkles, Clock, Mail, ChevronDown, ChevronUp } from 'lucide-react'
import useEmailStore from '../store/emailStore'

function SearchResultItem({ email, query }) {
  const [expanded, setExpanded] = useState(false)
  const { selectedEmails, toggleEmailSelection } = useEmailStore()
  const isSelected = selectedEmails.includes(email.uid)

  const formatDate = (date) => {
    const d = new Date(date)
    const today = new Date()
    if (d.toDateString() === today.toDateString()) {
      return d.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString('sv-SE', { month: 'short', day: 'numeric' })
  }

  const highlightText = (text, query) => {
    if (!query || !text) return text
    const regex = new RegExp(`(${query})`, 'gi')
    return text.replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>')
  }

  return (
    <div className={`border-b border-gray-200 hover:bg-gray-50 transition-colors ${isSelected ? 'bg-blue-50' : ''}`}>
      <div className="p-3 flex items-start gap-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => toggleEmailSelection(email.uid)}
          className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
          style={{ width: '16px', height: '16px' }}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-gray-900 truncate">
                <span dangerouslySetInnerHTML={{
                  __html: highlightText(email.from?.replace(/[\"<>]/g, '').split(' ')[0] || 'Unknown', query)
                }} />
              </p>
              {!email.seen && (
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
              )}
              <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                Sökresultat
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 flex-shrink-0">
                {formatDate(email.date)}
              </span>
              <button
                onClick={() => setExpanded(!expanded)}
                className="p-1 hover:bg-gray-200 rounded transition-colors"
              >
                {expanded ? (
                  <ChevronUp className="w-3 h-3 text-gray-500" />
                ) : (
                  <ChevronDown className="w-3 h-3 text-gray-500" />
                )}
              </button>
            </div>
          </div>

          <p className="text-sm text-gray-800 truncate mb-1">
            <span dangerouslySetInnerHTML={{
              __html: highlightText(email.subject || '(No subject)', query)
            }} />
          </p>

          <p className={`text-sm text-gray-600 ${expanded ? '' : 'line-clamp-2'}`} style={{
            display: expanded ? 'block' : '-webkit-box',
            WebkitLineClamp: expanded ? 'unset' : 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxHeight: expanded ? 'none' : '2.8em'
          }}>
            <span dangerouslySetInnerHTML={{
              __html: highlightText(
                email.bodyPreview || email.text?.substring(0, expanded ? 500 : 150) || 'No preview available',
                query
              )
            }} />
          </p>

          {expanded && email.matchReason && (
            <div className="mt-2 p-2 bg-blue-50 rounded-lg">
              <p className="text-xs text-blue-700 font-medium mb-1">
                <Sparkles className="w-3 h-3 inline mr-1" />
                AI Match Reason:
              </p>
              <p className="text-xs text-blue-600">{email.matchReason}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SearchResults() {
  const { searchResults, searchQuery, clearSearch, isSearchActive } = useEmailStore()

  if (!isSearchActive || searchResults.length === 0) {
    return null
  }

  return (
    <div className="bg-white border-b border-gray-200">
      {/* Search Results Header */}
      <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-blue-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-blue-900">
              Sökresultat för "{searchQuery}"
            </h3>
            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
              {searchResults.length} träffar
            </span>
          </div>
          <button
            onClick={clearSearch}
            className="p-1.5 hover:bg-blue-100 rounded-lg transition-colors"
            title="Stäng sökresultat"
          >
            <X className="w-4 h-4 text-blue-600" />
          </button>
        </div>
      </div>

      {/* Search Results List */}
      <div className="max-h-80 overflow-y-auto">
        {searchResults.map((email) => (
          <SearchResultItem
            key={`search-${email.uid}`}
            email={email}
            query={searchQuery}
          />
        ))}
      </div>

      {/* Separator */}
      <div className="p-2 bg-gray-50 border-b border-gray-300">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <div className="flex-1 h-px bg-gray-300"></div>
          <span className="px-2 bg-gray-50">Inbox</span>
          <div className="flex-1 h-px bg-gray-300"></div>
        </div>
      </div>
    </div>
  )
}