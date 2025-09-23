import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp, Plus, Star, Clock, Search } from 'lucide-react'

function CategoryMenu({ categories, onSelect, onClose }) {
  const [showAll, setShowAll] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [recentlyUsed, setRecentlyUsed] = useState([])
  const menuRef = useRef(null)

  useEffect(() => {
    // Load recently used categories from localStorage
    const recent = JSON.parse(localStorage.getItem('recentCategories') || '[]')
    setRecentlyUsed(recent.slice(0, 3))

    // Handle click outside
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  const handleCategorySelect = (categoryId) => {
    // Track recent usage
    const recent = JSON.parse(localStorage.getItem('recentCategories') || '[]')
    const updated = [categoryId, ...recent.filter(id => id !== categoryId)].slice(0, 5)
    localStorage.setItem('recentCategories', JSON.stringify(updated))

    onSelect(categoryId)
    onClose()
  }

  // Filter categories based on search
  const filteredCategories = searchQuery
    ? categories.filter(cat =>
        cat.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        cat.icon.includes(searchQuery)
      )
    : categories

  // Separate into groups for better UX
  const popularCategories = filteredCategories.slice(0, 5)
  const additionalCategories = filteredCategories.slice(5)
  const recentCategories = recentlyUsed
    .map(id => categories.find(cat => cat.id === id))
    .filter(Boolean)

  return (
    <div
      ref={menuRef}
      className="absolute top-full mt-1 left-0 w-64 max-w-[90vw] bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden z-50"
      style={{ maxHeight: '70vh' }}
    >
      {/* Search bar */}
      <div className="p-2 border-b border-gray-100">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input
            type="text"
            placeholder="Sök kategorier..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:border-blue-500"
            autoFocus
          />
        </div>
      </div>

      <div className="overflow-y-auto" style={{ maxHeight: 'calc(70vh - 40px)' }}>
        {/* Recently used section */}
        {recentCategories.length > 0 && !searchQuery && (
          <div className="p-1 border-b border-gray-100">
            <div className="flex items-center gap-1 px-2 py-0.5 text-xs text-gray-500 font-medium">
              <Clock className="w-3 h-3" />
              <span>Senast använda</span>
            </div>
            {recentCategories.map(cat => (
              <button
                key={cat.id}
                onClick={() => handleCategorySelect(cat.id)}
                className="w-full flex items-center gap-1 px-2 py-1 rounded hover:bg-blue-50 text-left transition-colors group"
              >
                <span className="text-sm">{cat.icon}</span>
                <span className="text-xs flex-1 group-hover:text-blue-700">{cat.label}</span>
                <Star className="w-3 h-3 text-yellow-500" />
              </button>
            ))}
          </div>
        )}

        {/* Popular categories */}
        <div className="p-1">
          {!searchQuery && (
            <div className="px-2 py-0.5 text-xs text-gray-500 font-medium">
              Populära kategorier
            </div>
          )}

          {popularCategories.map(cat => (
            <button
              key={cat.id}
              onClick={() => handleCategorySelect(cat.id)}
              className="w-full flex items-center gap-1 px-2 py-1 rounded hover:bg-blue-50 text-left transition-colors group"
            >
              <span className="text-sm">{cat.icon}</span>
              <span className="text-xs flex-1 group-hover:text-blue-700">{cat.label}</span>
              {cat.priority <= 3 && (
                <span className="text-xs px-1 py-0 bg-blue-100 text-blue-600 rounded">
                  Popular
                </span>
              )}
            </button>
          ))}

          {/* Show more/less toggle */}
          {additionalCategories.length > 0 && !searchQuery && (
            <>
              <button
                onClick={() => setShowAll(!showAll)}
                className="w-full flex items-center justify-center gap-1 px-2 py-1 mt-1 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors"
              >
                {showAll ? (
                  <>
                    <ChevronUp className="w-3 h-3" />
                    <span>Visa färre</span>
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3 h-3" />
                    <span>Visa {additionalCategories.length} fler kategorier</span>
                  </>
                )}
              </button>

              {/* Additional categories */}
              {showAll && (
                <div className="mt-1 pt-1 border-t border-gray-100">
                  <div className="px-2 py-0.5 text-xs text-gray-500 font-medium">
                    Alla kategorier
                  </div>
                  {additionalCategories.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => handleCategorySelect(cat.id)}
                      className="w-full flex items-center gap-1 px-2 py-1 rounded hover:bg-blue-50 text-left transition-colors group"
                    >
                      <span className="text-sm">{cat.icon}</span>
                      <span className="text-xs flex-1 group-hover:text-blue-700">{cat.label}</span>
                      {cat.priority > 100 && (
                        <span className="text-xs px-1 py-0 bg-green-100 text-green-600 rounded">
                          Egen
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          {/* No results */}
          {filteredCategories.length === 0 && (
            <div className="py-8 text-center">
              <p className="text-sm text-gray-500">Ingen kategori hittades</p>
            </div>
          )}
        </div>

        {/* Create new category */}
        {!searchQuery && (
          <div className="p-1 border-t border-gray-100">
            <button
              onClick={() => {
                // Create a new category via prompt
                const categoryName = prompt('Namn på ny kategori:')
                if (categoryName) {
                  const description = prompt(`Beskriv kategorin "${categoryName}" för AI-inlärning:`)
                  if (description) {
                    const newCategory = {
                      id: categoryName.toLowerCase().replace(/\s+/g, '_'),
                      label: categoryName,
                      icon: '📌',
                      priority: 100 + categories.length
                    }

                    // Save to localStorage
                    const customCategories = JSON.parse(localStorage.getItem('customEmailCategories') || '[]')
                    customCategories.push({ ...newCategory, aiCriteria: description })
                    localStorage.setItem('customEmailCategories', JSON.stringify(customCategories))

                    // Track for learning
                    const learningService = require('../services/learningService').default
                    learningService.trackAction('create_category', null, {
                      categoryId: newCategory.id,
                      categoryName: newCategory.label,
                      aiCriteria: description
                    })

                    onSelect(newCategory.id)
                  }
                }
              }}
              className="w-full flex items-center gap-1 px-2 py-1 rounded hover:bg-green-50 text-left transition-colors group"
            >
              <Plus className="w-3 h-3 text-green-600 group-hover:text-green-700" />
              <span className="text-xs text-green-600 group-hover:text-green-700 font-medium">
                Skapa ny kategori
              </span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default CategoryMenu