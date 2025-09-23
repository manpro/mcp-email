import { useState } from 'react'
import { ChevronDown, Plus, X } from 'lucide-react'
import useEmailStore from '../store/emailStore-refactored'

// Predefinerade filter med ikoner
const availableFilters = [
  { id: 'newsletter', label: 'Nyheter', icon: '📰' },
  { id: 'work', label: 'Arbete', icon: '💼' },
  { id: 'important', label: 'Viktigt', icon: '⭐' },
  { id: 'unread', label: 'Oläst', icon: '🔵' },
  { id: 'invoice', label: 'Fakturor', icon: '📊' },
  { id: 'personal', label: 'Personligt', icon: '👤' },
  { id: 'meetings', label: 'Möten', icon: '🗓️' },
  { id: 'security', label: 'Säkerhet', icon: '🔒' },
  { id: 'social', label: 'Socialt', icon: '💬' },
  { id: 'automated', label: 'Automatiskt', icon: '🤖' },
  { id: 'spam', label: 'Spam', icon: '🗑️' },
  { id: 'other', label: 'Övrigt', icon: '📁' }
]

export default function SmartFiltersCompact() {
  const {
    activeFilters,
    setActiveFilters,
    categoryCounts,
    unreadCount = 0
  } = useEmailStore()

  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  // Ensure activeFilters is always an array
  const initialFilters = Array.isArray(activeFilters) ? activeFilters : []
  const [selectedFilters, setSelectedFilters] = useState(initialFilters)

  const handleFilterToggle = (filterId) => {
    const newFilters = selectedFilters.includes(filterId)
      ? selectedFilters.filter(id => id !== filterId)
      : [...selectedFilters, filterId]

    setSelectedFilters(newFilters)
    setActiveFilters(newFilters)
  }

  const handleQuickAdd = (filterId) => {
    if (!selectedFilters.includes(filterId)) {
      handleFilterToggle(filterId)
    }
  }

  const clearAllFilters = () => {
    setSelectedFilters([])
    setActiveFilters([])
  }

  const mainFilter = availableFilters.find(f => f.id === selectedFilters?.[0])
  const quickFilters = ['work', 'important', 'unread']

  return (
    <div className="compact-smart-filters bg-white border-b-2 border-gray-200 px-4 py-2">
      {/* Rad 1: Huvudfunktioner */}
      <div className="flex items-center gap-2 h-8">
        {/* Huvuddropdown */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-1.5 px-3 h-8 bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded-md text-sm font-medium text-gray-700 transition-colors"
          >
            <ChevronDown className="w-3 h-3" />
            <span>Smarta filter:</span>
            {mainFilter && (
              <>
                <span>{mainFilter.icon}</span>
                <span className="font-semibold">{mainFilter.label}</span>
              </>
            )}
          </button>

          {/* Dropdown menu */}
          {isDropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsDropdownOpen(false)}
              />
              <div className="absolute top-9 left-0 min-w-[220px] bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
                {availableFilters.map(filter => {
                  const count = categoryCounts?.[filter.id] || 0
                  const isActive = selectedFilters.includes(filter.id)

                  return (
                    <button
                      key={filter.id}
                      onClick={() => {
                        handleFilterToggle(filter.id)
                        setIsDropdownOpen(false)
                      }}
                      className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
                        isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                      }`}
                    >
                      <span className="text-lg">{filter.icon}</span>
                      <span className="flex-1 text-left">{filter.label}</span>
                      {count > 0 && (
                        <span className="text-xs text-gray-500">({count})</span>
                      )}
                      {isActive && (
                        <span className="text-green-600 font-bold">✓</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>

        {/* Snabbknappar */}
        {quickFilters.map(filterId => {
          const filter = availableFilters.find(f => f.id === filterId)
          const isActive = selectedFilters.includes(filterId)
          const count = categoryCounts?.[filterId] || 0

          return (
            <button
              key={filterId}
              onClick={() => handleQuickAdd(filterId)}
              className={`flex items-center gap-1 px-2 h-7 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? 'bg-blue-600 text-white border border-blue-600'
                  : 'bg-white hover:bg-gray-50 border border-gray-300 text-gray-600'
              }`}
            >
              {!isActive && <Plus className="w-3 h-3" />}
              <span>{filter?.label}</span>
              {count > 0 && (
                <span className={`ml-1 ${isActive ? 'opacity-80' : 'text-gray-500'}`}>
                  ({count})
                </span>
              )}
            </button>
          )
        })}

        {/* Oläst räknare */}
        {unreadCount > 0 && (
          <div className="ml-auto">
            <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 bg-red-500 text-white rounded-full text-xs font-bold">
              {unreadCount}
            </span>
          </div>
        )}
      </div>

      {/* Rad 2: Sekundära funktioner och chips (visas endast om filter är aktiva) */}
      {selectedFilters.length > 0 && (
        <div className="flex items-center gap-2 h-7 mt-1">
          {/* Aktiva filter chips */}
          <div className="flex gap-1.5 flex-1">
            {selectedFilters.map(filterId => {
              const filter = availableFilters.find(f => f.id === filterId)
              return (
                <div
                  key={filterId}
                  className="inline-flex items-center gap-1 px-2 h-6 bg-blue-50 border border-blue-200 rounded-full text-xs text-blue-700"
                >
                  <span>{filter?.icon}</span>
                  <span>{filter?.label}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFilterToggle(filterId)
                    }}
                    className="hover:bg-blue-200 rounded-full p-0.5 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )
            })}
          </div>

          {/* Rensa alla */}
          <button
            onClick={clearAllFilters}
            className="px-3 h-6 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-gray-300 rounded-md transition-colors"
          >
            Rensa alla
          </button>
        </div>
      )}
    </div>
  )
}