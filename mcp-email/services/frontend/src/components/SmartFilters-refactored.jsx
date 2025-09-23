import { useState, useEffect } from 'react'
import { Filter, Star, Clock, AlertTriangle, User, Building, FileText, Calendar, Shield, X, Mail, Lock, Users, Bot, Ban, Folder, Tag } from 'lucide-react'
import useEmailStore from '../store/emailStore-refactored'

// Complete list of all default categories with icons
const defaultCategories = [
  { id: 'newsletter', label: 'Nyhetsbrev', icon: '📰', lucideIcon: FileText, color: 'bg-blue-100 text-blue-700 border-blue-200', priority: 1 },
  { id: 'work', label: 'Arbete', icon: '💼', lucideIcon: Building, color: 'bg-purple-100 text-purple-700 border-purple-200', priority: 2 },
  { id: 'personal', label: 'Personligt', icon: '👤', lucideIcon: User, color: 'bg-green-100 text-green-700 border-green-200', priority: 3 },
  { id: 'invoice', label: 'Faktura', icon: '📄', lucideIcon: FileText, color: 'bg-yellow-100 text-yellow-700 border-yellow-200', priority: 4 },
  { id: 'security', label: 'Säkerhet', icon: '🔒', lucideIcon: Lock, color: 'bg-red-100 text-red-700 border-red-200', priority: 5 },
  { id: 'meetings', label: 'Möten', icon: '📅', lucideIcon: Calendar, color: 'bg-indigo-100 text-indigo-700 border-indigo-200', priority: 6 },
  { id: 'automated', label: 'Automatiskt', icon: '🤖', lucideIcon: Bot, color: 'bg-gray-100 text-gray-700 border-gray-200', priority: 7 },
  { id: 'social', label: 'Socialt', icon: '💬', lucideIcon: Users, color: 'bg-pink-100 text-pink-700 border-pink-200', priority: 8 },
  { id: 'spam', label: 'Spam', icon: '🚫', lucideIcon: Ban, color: 'bg-gray-100 text-gray-700 border-gray-200', priority: 9 },
  { id: 'other', label: 'Övrigt', icon: '📁', lucideIcon: Folder, color: 'bg-gray-100 text-gray-700 border-gray-200', priority: 10 }
]

// Additional urgent/important categories
const additionalCategories = {
  urgent: {
    id: 'urgent',
    label: 'Brådskande',
    icon: '🔥',
    lucideIcon: AlertTriangle,
    color: 'bg-red-100 text-red-700 border-red-200',
    description: 'Email som kräver snabb åtgärd'
  },
  important: {
    id: 'important',
    label: 'Viktigt',
    icon: '⭐',
    lucideIcon: Star,
    color: 'bg-orange-100 text-orange-700 border-orange-200',
    description: 'Viktig korrespondens'
  }
}

function CategoryFilter({ category, count, isActive, onClick }) {
  const Icon = category.lucideIcon || Tag

  return (
    <button
      onClick={() => onClick(category.id)}
      className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs transition-all ${
        isActive
          ? category.color + ' ring-2 ring-blue-500 shadow-md font-semibold'
          : 'bg-white hover:bg-gray-50 border-gray-200 text-gray-700'
      }`}
      title={category.description || category.label}
    >
      {category.icon ? (
        <span className="text-sm">{category.icon}</span>
      ) : (
        <Icon className="w-3 h-3" />
      )}
      <span className="font-medium">{category.label}</span>
      {count > 0 && (
        <span className={`ml-1 px-1.5 py-0 text-xs rounded-full ${
          isActive ? 'bg-white bg-opacity-70' : 'bg-gray-100'
        }`}>
          {count}
        </span>
      )}
    </button>
  )
}

function PriorityFilter({ priority, count, isActive, onClick }) {
  const priorityConfig = {
    critical: { name: 'Kritisk', color: 'bg-red-500', textColor: 'text-red-700' },
    high: { name: 'Hög', color: 'bg-orange-500', textColor: 'text-orange-700' },
    medium: { name: 'Medium', color: 'bg-blue-500', textColor: 'text-blue-700' },
    low: { name: 'Låg', color: 'bg-green-500', textColor: 'text-green-700' }
  }

  const config = priorityConfig[priority]
  if (!config) return null

  return (
    <button
      onClick={() => onClick(priority)}
      className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs transition-all ${
        isActive
          ? 'bg-gray-100 border-gray-300 ring-2 ring-blue-500 shadow-md font-semibold'
          : 'bg-white hover:bg-gray-50 border-gray-200'
      }`}
    >
      <div className={`w-2 h-2 rounded-full ${config.color}`}></div>
      <span className={`font-medium ${isActive ? config.textColor : 'text-gray-700'}`}>
        {config.name}
      </span>
      {count > 0 && (
        <span className="ml-1 px-1.5 py-0 text-xs bg-gray-100 rounded-full">
          {count}
        </span>
      )}
    </button>
  )
}

function SourceFilter({ source, count, isActive, onClick }) {
  const sourceConfig = {
    user_override: { name: 'Manuell', icon: '👤', color: 'bg-green-100 text-green-700 border-green-200' },
    ml_analysis: { name: 'AI Analys', icon: '🤖', color: 'bg-purple-100 text-purple-700 border-purple-200' },
    rule_based: { name: 'Regelbaserad', icon: '📋', color: 'bg-gray-100 text-gray-700 border-gray-200' }
  }

  const config = sourceConfig[source]
  if (!config) return null

  return (
    <button
      onClick={() => onClick(source)}
      className={`flex items-center gap-1 px-2 py-1 rounded-md border text-xs transition-all ${
        isActive
          ? config.color + ' ring-2 ring-blue-500 shadow-md font-semibold'
          : 'bg-white hover:bg-gray-50 border-gray-200 text-gray-700'
      }`}
    >
      <span className="text-sm">{config.icon}</span>
      <span className="font-medium">{config.name}</span>
      {count > 0 && (
        <span className={`ml-1 px-1.5 py-0 text-xs rounded-full ${
          isActive ? 'bg-white bg-opacity-70' : 'bg-gray-100'
        }`}>
          {count}
        </span>
      )}
    </button>
  )
}

export default function SmartFilters() {
  const { emails, selectedAccountId, activeFilters, toggleFilter, clearAllFilters, getCategoryStats } = useEmailStore()
  const [stats, setStats] = useState({ categories: {}, priorities: {}, sources: {}, total: 0, unread: 0 })
  const [isVisible, setIsVisible] = useState(true)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (selectedAccountId) {
      loadStats()
    }
  }, [selectedAccountId, emails])

  const loadStats = async () => {
    setIsLoading(true)
    try {
      const categoryStats = await getCategoryStats()
      setStats(categoryStats)
      console.log('📊 Category stats loaded:', categoryStats)
    } catch (error) {
      console.error('Failed to load category stats:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleFilter = (type, value) => {
    const filterKey = `${type}:${value}`
    toggleFilter(filterKey)
  }

  // Get all categories including dynamic ones
  const allCategories = [
    ...defaultCategories,
    additionalCategories.urgent,
    additionalCategories.important
  ]

  // Create dynamic categories for any categories found in stats but not in predefined list
  const dynamicCategories = []
  if (stats.categories) {
    Object.keys(stats.categories).forEach(categoryId => {
      const exists = allCategories.some(cat => cat.id === categoryId)
      if (!exists && stats.categories[categoryId] > 0) {
        dynamicCategories.push({
          id: categoryId,
          label: categoryId.charAt(0).toUpperCase() + categoryId.slice(1),
          icon: '🏷️',
          lucideIcon: Tag,
          color: 'bg-teal-100 text-teal-700 border-teal-200',
          priority: 200 + Object.keys(stats.categories).indexOf(categoryId)
        })
      }
    })
  }

  const allCategoriesWithDynamic = [...allCategories, ...dynamicCategories]

  // Filter categories that have emails or are active
  const visibleCategories = allCategoriesWithDynamic.filter(cat =>
    (stats.categories && stats.categories[cat.id] > 0) ||
    activeFilters.has(`category:${cat.id}`)
  )

  // Sort by email count (most to least), then by priority
  visibleCategories.sort((a, b) => {
    const countA = stats.categories?.[a.id] || 0
    const countB = stats.categories?.[b.id] || 0

    // Primary sort: by count (descending)
    if (countB !== countA) {
      return countB - countA
    }

    // Secondary sort: by priority (ascending)
    return (a.priority || 999) - (b.priority || 999)
  })

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="w-full p-2 text-sm text-gray-500 hover:text-gray-700 transition-colors border-b border-gray-200"
      >
        <Filter className="w-4 h-4 inline mr-2" />
        Visa smarta filter ({stats.total} emails)
      </button>
    )
  }

  return (
    <div className="bg-white border-b border-gray-200 p-2">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Filter className="w-3 h-3 text-gray-600" />
          <h3 className="text-xs font-semibold text-gray-900">Smarta Filter v2</h3>
          <span className="text-xs text-gray-500">
            {stats.total} emails, {stats.unread} olästa
          </span>
          {isLoading && (
            <span className="text-xs text-blue-600">Laddar...</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeFilters.size > 0 && (
            <button
              onClick={clearAllFilters}
              className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              Rensa alla ({activeFilters.size})
            </button>
          )}
          <button
            onClick={() => setIsVisible(false)}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Category Filters */}
      <div className="mb-2">
        <h4 className="text-xs font-medium text-gray-600 mb-1">Kategorier (sorterat efter antal)</h4>
        <div className="flex flex-wrap gap-1">
          {visibleCategories.map((category) => (
            <CategoryFilter
              key={category.id}
              category={category}
              count={stats.categories?.[category.id] || 0}
              isActive={activeFilters.has(`category:${category.id}`)}
              onClick={(cat) => handleToggleFilter('category', cat)}
            />
          ))}
        </div>
      </div>

      {/* Priority Filters */}
      {stats.priorities && Object.keys(stats.priorities).length > 0 && (
        <div className="mb-2">
          <h4 className="text-xs font-medium text-gray-600 mb-1">Prioritet</h4>
          <div className="flex flex-wrap gap-1">
            {Object.entries(stats.priorities).map(([priority, count]) => (
              <PriorityFilter
                key={priority}
                priority={priority}
                count={count}
                isActive={activeFilters.has(`priority:${priority}`)}
                onClick={(pri) => handleToggleFilter('priority', pri)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Source Filters */}
      {stats.sources && Object.keys(stats.sources).length > 0 && (
        <div className="mb-2">
          <h4 className="text-xs font-medium text-gray-600 mb-1">Kategoriseringskälla</h4>
          <div className="flex flex-wrap gap-1">
            {Object.entries(stats.sources).map(([source, count]) => (
              <SourceFilter
                key={source}
                source={source}
                count={count}
                isActive={activeFilters.has(`source:${source}`)}
                onClick={(src) => handleToggleFilter('source', src)}
              />
            ))}
          </div>
        </div>
      )}


    </div>
  )
}