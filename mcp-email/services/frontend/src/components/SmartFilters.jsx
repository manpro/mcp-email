import { useState, useEffect } from 'react'
import { Filter, Star, Clock, AlertTriangle, User, Building, FileText, Calendar, Shield, X, Mail, Lock, Users, Bot, Ban, Folder, Tag } from 'lucide-react'
import useEmailStore from '../store/emailStore'

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

// Additional urgent/important categories (not part of the default 10)
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
          ? category.color + ' ring-1 ring-offset-1 ring-blue-400'
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
          ? 'bg-gray-100 border-gray-300 ring-1 ring-offset-1 ring-blue-400'
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

export default function SmartFilters() {
  const { emails, selectedAccountId, activeFilters, toggleFilter, clearAllFilters } = useEmailStore()
  const [emailStats, setEmailStats] = useState({})
  const [isVisible, setIsVisible] = useState(true)
  const [customCategories, setCustomCategories] = useState([])
  const [showAllCategories, setShowAllCategories] = useState(false)

  useEffect(() => {
    // Load custom categories from localStorage
    const saved = localStorage.getItem('customEmailCategories')
    if (saved) {
      const custom = JSON.parse(saved).map((cat, idx) => ({
        ...cat,
        lucideIcon: Tag,
        color: 'bg-teal-100 text-teal-700 border-teal-200',
        priority: 100 + idx
      }))
      setCustomCategories(custom)
    }
  }, [])

  useEffect(() => {
    // Analyze emails and categorize them
    analyzeEmails()
  }, [emails, customCategories])

  const analyzeEmails = () => {
    const stats = {
      categories: {},
      priorities: {},
      total: emails.length,
      unread: 0
    }

    // Get all categories
    const allCategories = [
      ...defaultCategories,
      additionalCategories.urgent,
      additionalCategories.important,
      ...customCategories
    ]

    // Initialize all categories with 0 count
    allCategories.forEach(cat => {
      stats.categories[cat.id] = 0
    })

    // Collect all unique categories from emails (including custom ones not in our predefined list)
    const emailCategories = new Set()
    emails.forEach(email => {
      const category = categorizeEmail(email)
      emailCategories.add(category)
    })

    // Add any new categories found in emails to stats
    emailCategories.forEach(category => {
      if (!stats.categories.hasOwnProperty(category)) {
        stats.categories[category] = 0
      }
    })

    emails.forEach(email => {
      // Count unread
      if (!email.seen) {
        stats.unread++
      }

      // Categorize emails based on content and metadata
      const category = categorizeEmail(email)
      if (stats.categories[category] !== undefined) {
        stats.categories[category]++
      }

      // Debug logging for categorization
      console.log(`📧 Email ${email.uid} categorized as:`, {
        category,
        originalCategory: email.category,
        manualCategory: email.manualCategory,
        from: email.from?.substring(0, 30) + '...',
        subject: email.subject?.substring(0, 30) + '...'
      })

      // Determine priority
      const priority = determinePriority(email)
      stats.priorities[priority] = (stats.priorities[priority] || 0) + 1
    })

    console.log(`📊 Email categorization complete:`, {
      totalEmails: stats.total,
      categories: Object.entries(stats.categories).map(([cat, count]) => `${cat}: ${count}`).join(', '),
      unread: stats.unread
    })

    setEmailStats(stats)
  }

  const categorizeEmail = (email) => {
    // First check if email has a manually assigned category
    if (email.category && email.manualCategory) {
      return email.category
    }

    // If email comes from API with a category (ML analysis), use that
    if (email.category) {
      return email.category
    }

    // Fall back to rule-based categorization
    const from = (email.from || '').toLowerCase()
    const subject = (email.subject || '').toLowerCase()
    const text = (email.text || email.bodyPreview || '').toLowerCase()

    // Check for urgent first
    if (subject.includes('brådskande') || subject.includes('urgent') ||
        subject.includes('akut') || subject.includes('emergency')) {
      return 'urgent'
    }

    // Check for important
    if (subject.includes('viktigt') || subject.includes('important') ||
        from.includes('chef') || from.includes('boss')) {
      return 'important'
    }

    // Security emails
    if (subject.includes('säkerhet') || subject.includes('verifiering') ||
        subject.includes('lösenord') || subject.includes('inloggning') ||
        subject.includes('security') || subject.includes('verification')) {
      return 'security'
    }

    // Meeting invitations
    if (subject.includes('möte') || subject.includes('meeting') ||
        subject.includes('kallelse') || subject.includes('invitation') ||
        text.includes('calendar') || text.includes('zoom')) {
      return 'meetings'
    }

    // Newsletters and marketing
    if (from.includes('newsletter') || from.includes('noreply') ||
        from.includes('marketing') || subject.includes('nyhetsbrev') ||
        text.includes('unsubscribe') || text.includes('avprenumerera')) {
      return 'newsletter'
    }

    // Invoice
    if (subject.includes('faktura') || subject.includes('invoice') ||
        text.includes('betalning') || text.includes('payment')) {
      return 'invoice'
    }

    // Work-related (common work domains and keywords)
    if (from.includes('@company.') || from.includes('@work.') ||
        subject.includes('projekt') || subject.includes('rapport') ||
        subject.includes('deadline') || subject.includes('budget')) {
      return 'work'
    }

    // Social
    if (from.includes('facebook') || from.includes('twitter') ||
        from.includes('instagram') || from.includes('linkedin') ||
        subject.includes('vän') || subject.includes('friend')) {
      return 'social'
    }

    // Spam
    if (subject.includes('spam') || subject.includes('winner') ||
        subject.includes('congratulations') || text.includes('click here now')) {
      return 'spam'
    }

    // Automated emails
    if (from.includes('noreply') || from.includes('donotreply') ||
        from.includes('automated') || from.includes('system') ||
        subject.includes('bekräftelse') || subject.includes('confirmation')) {
      return 'automated'
    }

    // Check custom categories
    for (const cat of customCategories) {
      if (cat.aiCriteria) {
        const criteria = cat.aiCriteria.toLowerCase()
        if (from.includes(criteria) || subject.includes(criteria) || text.includes(criteria)) {
          return cat.id
        }
      }
    }

    // Default to personal (ensure all emails have a category)
    return 'personal'
  }

  const determinePriority = (email) => {
    const subject = (email.subject || '').toLowerCase()
    const text = (email.text || email.bodyPreview || '').toLowerCase()
    const from = (email.from || '').toLowerCase()

    // Critical priority
    if (subject.includes('kritisk') || subject.includes('critical') ||
        subject.includes('emergency') || subject.includes('urgent')) {
      return 'critical'
    }

    // High priority
    if (subject.includes('viktigt') || subject.includes('important') ||
        subject.includes('brådskande') || subject.includes('deadline') ||
        from.includes('boss') || from.includes('chef')) {
      return 'high'
    }

    // Low priority
    if (subject.includes('newsletter') || subject.includes('nyhetsbrev') ||
        from.includes('noreply') || text.includes('unsubscribe')) {
      return 'low'
    }

    // Default to medium
    return 'medium'
  }

  const handleToggleFilter = (type, value) => {
    const filterKey = `${type}:${value}`
    toggleFilter(filterKey)
  }

  // Get all categories
  const allCategories = [
    ...defaultCategories,
    additionalCategories.urgent,
    additionalCategories.important,
    ...customCategories
  ]

  // Create dynamic categories for any categories found in emails but not in predefined list
  const dynamicCategories = []
  if (emailStats.categories) {
    Object.keys(emailStats.categories).forEach(categoryId => {
      const exists = allCategories.some(cat => cat.id === categoryId)
      if (!exists && emailStats.categories[categoryId] > 0) {
        dynamicCategories.push({
          id: categoryId,
          label: categoryId.charAt(0).toUpperCase() + categoryId.slice(1), // Capitalize
          icon: '🏷️',
          lucideIcon: Tag,
          color: 'bg-teal-100 text-teal-700 border-teal-200',
          priority: 200 + Object.keys(emailStats.categories).indexOf(categoryId) // Stable priority based on order
        })
      }
    })
  }

  const allCategoriesWithDynamic = [...allCategories, ...dynamicCategories]

  // Filter categories that have emails or are active
  const visibleCategories = showAllCategories
    ? allCategoriesWithDynamic
    : allCategoriesWithDynamic.filter(cat =>
        (emailStats.categories && emailStats.categories[cat.id] > 0) ||
        activeFilters.has(`category:${cat.id}`)
      )

  // Sort by email count (most to least), then by priority
  visibleCategories.sort((a, b) => {
    const countA = emailStats.categories?.[a.id] || 0
    const countB = emailStats.categories?.[b.id] || 0

    // Primary sort: by count (descending - most emails first)
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
        Visa smarta filter ({emailStats.total} emails)
      </button>
    )
  }

  return (
    <div className="bg-white border-b border-gray-200 p-2">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Filter className="w-3 h-3 text-gray-600" />
          <h3 className="text-xs font-semibold text-gray-900">Smarta Filter</h3>
          <span className="text-xs text-gray-500">
            {emailStats.total} emails, {emailStats.unread} olästa
          </span>
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
        <div className="flex items-center justify-between mb-1">
          <h4 className="text-xs font-medium text-gray-600">Kategorier</h4>
          <button
            onClick={() => setShowAllCategories(!showAllCategories)}
            className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
          >
            {showAllCategories ? 'Visa endast aktiva' : 'Visa alla kategorier'}
          </button>
        </div>
        <div className="flex flex-wrap gap-1">
          {visibleCategories.map((category) => (
            <CategoryFilter
              key={category.id}
              category={category}
              count={emailStats.categories?.[category.id] || 0}
              isActive={activeFilters.has(`category:${category.id}`)}
              onClick={(cat) => handleToggleFilter('category', cat)}
            />
          ))}
        </div>
      </div>

      {/* Priority Filters */}
      <div>
        <h4 className="text-xs font-medium text-gray-600 mb-1">Prioritet</h4>
        <div className="flex flex-wrap gap-1">
          {Object.entries(emailStats.priorities || {}).map(([priority, count]) => (
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

      {/* Active Filters Summary */}
      {activeFilters.size > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-600">
            Aktiva filter: {Array.from(activeFilters).map(filter => {
              const [type, value] = filter.split(':')
              if (type === 'category') {
                const category = allCategoriesWithDynamic.find(cat => cat.id === value)
                return category?.label || value
              } else if (type === 'priority') {
                const priorityNames = { critical: 'Kritisk', high: 'Hög', medium: 'Medium', low: 'Låg' }
                return priorityNames[value] || value
              }
              return value
            }).join(', ')}
          </div>
        </div>
      )}
    </div>
  )
}