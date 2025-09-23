import { useState, useRef, useEffect } from 'react'
import { ChevronDown, MoreHorizontal } from 'lucide-react'
import learningService from '../services/learningService'

const defaultCategories = [
  { id: 'newsletter', label: 'Nyhetsbrev', icon: '📰', color: 'bg-blue-100 text-blue-700', priority: 1 },
  { id: 'work', label: 'Arbete', icon: '💼', color: 'bg-purple-100 text-purple-700', priority: 2 },
  { id: 'personal', label: 'Personligt', icon: '👤', color: 'bg-green-100 text-green-700', priority: 3 },
  { id: 'invoice', label: 'Faktura', icon: '📄', color: 'bg-yellow-100 text-yellow-700', priority: 4 },
  { id: 'security', label: 'Säkerhet', icon: '🔒', color: 'bg-red-100 text-red-700', priority: 5 },
  { id: 'meetings', label: 'Möten', icon: '📅', color: 'bg-indigo-100 text-indigo-700', priority: 6 },
  { id: 'automated', label: 'Automatiskt', icon: '🤖', color: 'bg-gray-100 text-gray-700', priority: 7 },
  { id: 'social', label: 'Socialt', icon: '💬', color: 'bg-pink-100 text-pink-700', priority: 8 },
  { id: 'spam', label: 'Spam', icon: '🚫', color: 'bg-gray-100 text-gray-700', priority: 9 },
  { id: 'other', label: 'Övrigt', icon: '📁', color: 'bg-gray-100 text-gray-700', priority: 10 }
]

export default function CompactCategorySelector({ email, currentCategory, onCategoryChange, compact = false }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [recentCategories, setRecentCategories] = useState([])
  const [customCategories, setCustomCategories] = useState([])
  const containerRef = useRef(null)

  useEffect(() => {
    // Load custom categories and recent usage
    const saved = localStorage.getItem('customEmailCategories')
    if (saved) {
      setCustomCategories(JSON.parse(saved))
    }

    const recent = JSON.parse(localStorage.getItem('recentCategories') || '[]')
    setRecentCategories(recent.slice(0, 3))
  }, [])

  const allCategories = [...defaultCategories, ...customCategories.map((cat, idx) => ({
    ...cat,
    priority: 100 + idx
  }))]

  // Get priority categories (most used + high priority)
  const getPriorityCategories = () => {
    const recentIds = new Set(recentCategories)
    const topCategories = allCategories
      .filter(cat => recentIds.has(cat.id) || cat.priority <= 3)
      .slice(0, 4)

    return topCategories
  }

  const priorityCategories = getPriorityCategories()
  const remainingCategories = allCategories.filter(cat =>
    !priorityCategories.some(pCat => pCat.id === cat.id)
  )

  const current = allCategories.find(c => c.id === currentCategory) || defaultCategories[9]

  const handleCategorySelect = (categoryId) => {
    // Track usage for learning
    learningService.trackAction('categorize', email, {
      oldCategory: currentCategory,
      newCategory: categoryId,
      userCorrection: true
    })

    // Update recent categories
    const recent = JSON.parse(localStorage.getItem('recentCategories') || '[]')
    const updated = [categoryId, ...recent.filter(id => id !== categoryId)].slice(0, 5)
    localStorage.setItem('recentCategories', JSON.stringify(updated))
    setRecentCategories(updated.slice(0, 3))

    onCategoryChange(categoryId)
    setIsExpanded(false)
  }

  // Tooltip component
  const Tooltip = ({ children, content }) => (
    <div className="group relative inline-block">
      {children}
      <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 text-xs text-white bg-gray-900 rounded whitespace-nowrap z-50">
        {content}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-2 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  )

  // Compact icon-only button
  const CategoryButton = ({ category, isActive = false, showTooltip = true }) => {
    const button = (
      <button
        onClick={() => handleCategorySelect(category.id)}
        className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs transition-all hover:scale-110 focus:outline-none focus:ring-1 focus:ring-offset-1 ${
          isActive
            ? `${category.color} ring-1 ring-gray-400`
            : 'bg-gray-50 hover:bg-gray-100 text-gray-600'
        }`}
        title={showTooltip ? undefined : category.label}
      >
        <span className="text-sm">{category.icon}</span>
      </button>
    )

    return showTooltip ? (
      <Tooltip content={category.label}>
        {button}
      </Tooltip>
    ) : button
  }

  if (compact) {
    // Ultra-compact mode: only show current category as icon with tooltip
    return (
      <Tooltip content={`${current.label} (klicka för att ändra)`}>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs transition-all hover:scale-110 focus:outline-none focus:ring-1 focus:ring-offset-1 ${current.color}`}
        >
          <span className="text-sm">{current.icon}</span>
        </button>
      </Tooltip>
    )
  }

  return (
    <div className="flex items-center gap-1" ref={containerRef}>
      {/* Priority categories - always visible */}
      <div className="flex items-center gap-1">
        {priorityCategories.map(category => (
          <CategoryButton
            key={category.id}
            category={category}
            isActive={category.id === currentCategory}
          />
        ))}
      </div>

      {/* Expand/collapse button for remaining categories */}
      {remainingCategories.length > 0 && (
        <div className="relative">
          <Tooltip content={isExpanded ? 'Visa färre kategorier' : `Visa ${remainingCategories.length} fler kategorier`}>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 transition-all focus:outline-none focus:ring-1 focus:ring-offset-1"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3 transform rotate-180" />
              ) : (
                <MoreHorizontal className="w-3 h-3" />
              )}
            </button>
          </Tooltip>

          {/* Expanded categories */}
          {isExpanded && (
            <div className="absolute top-full left-0 mt-1 flex flex-wrap gap-1 p-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-w-64">
              {remainingCategories.map(category => (
                <CategoryButton
                  key={category.id}
                  category={category}
                  isActive={category.id === currentCategory}
                  showTooltip={false}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Current category label (for context) - hidden on mobile */}
      <span className="hidden sm:inline-block text-xs text-gray-500 ml-1">
        {current.label}
      </span>
    </div>
  )
}