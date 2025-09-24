import { useState, useRef, useEffect } from 'react'
import {
  Mail, Briefcase, User, FileText, Shield, Calendar, Bot, Users, Ban, Folder,
  CheckCircle, AlertTriangle, Clock, ArrowRight, ThumbsUp, ThumbsDown
} from 'lucide-react'
import customCategoriesCache from '../services/customCategoriesCache'

const defaultCategories = [
  { id: 'newsletter', label: 'Nyhetsbrev', icon: Mail, color: 'bg-blue-100 text-blue-700', shortcut: '1' },
  { id: 'work', label: 'Arbete', icon: Briefcase, color: 'bg-purple-100 text-purple-700', shortcut: '2' },
  { id: 'personal', label: 'Personligt', icon: User, color: 'bg-green-100 text-green-700', shortcut: '3' },
  { id: 'invoice', label: 'Faktura', icon: FileText, color: 'bg-yellow-100 text-yellow-700', shortcut: '4' },
  { id: 'security', label: 'Säkerhet', icon: Shield, color: 'bg-red-100 text-red-700', shortcut: '5' },
  { id: 'meetings', label: 'Möten', icon: Calendar, color: 'bg-indigo-100 text-indigo-700', shortcut: '6' },
  { id: 'automated', label: 'Automatiskt', icon: Bot, color: 'bg-gray-100 text-gray-700', shortcut: '7' },
  { id: 'social', label: 'Socialt', icon: Users, color: 'bg-pink-100 text-pink-700', shortcut: '8' },
  { id: 'spam', label: 'Spam', icon: Ban, color: 'bg-gray-100 text-gray-700', shortcut: '9' },
  { id: 'other', label: 'Övrigt', icon: Folder, color: 'bg-gray-100 text-gray-700', shortcut: '0' }
]

// Confidence indicator component
function ConfidenceBadge({ confidence, isAutoExecuted = false }) {
  if (isAutoExecuted) {
    return (
      <div className="flex items-center text-xs text-green-600 bg-green-50 px-1 rounded">
        <CheckCircle className="w-3 h-3 mr-1" />
        Auto
      </div>
    )
  }

  if (confidence >= 0.95) {
    return <div className="w-2 h-2 bg-green-500 rounded-full" title="Högt förtroende (95%+)" />
  } else if (confidence >= 0.80) {
    return <div className="w-2 h-2 bg-yellow-500 rounded-full" title="Medel förtroende (80-94%)" />
  } else {
    return <div className="w-2 h-2 bg-red-500 rounded-full" title="Lågt förtroende (<80%)" />
  }
}

// Smart suggestion bar for medium confidence predictions
function SuggestionBar({ suggestion, onAccept, onReject, onAlwaysApply }) {
  return (
    <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs">
      <ArrowRight className="w-3 h-3 text-blue-600" />
      <span className="text-blue-700">
        Förslag: <strong>{suggestion.label}</strong>
      </span>
      <div className="flex gap-1 ml-auto">
        <button
          onClick={onAccept}
          className="px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
          title="Acceptera (Enter)"
        >
          <ThumbsUp className="w-3 h-3" />
        </button>
        <button
          onClick={onAlwaysApply}
          className="px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
          title="Använd alltid för liknande email"
        >
          Alltid
        </button>
        <button
          onClick={onReject}
          className="px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
          title="Avvisa (Esc)"
        >
          <ThumbsDown className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}

export default function EnhancedCategorySelector({
  email,
  currentCategory,
  mlAnalysis = {},  // { category, confidence, isAutoExecuted }
  onCategoryChange,
  showSuggestions = true
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [customCategories, setCustomCategories] = useState([])
  const [showingSuggestion, setShowingSuggestion] = useState(false)
  const dropdownRef = useRef(null)

  const confidence = mlAnalysis.confidence || 0
  const isAutoExecuted = mlAnalysis.isAutoExecuted || false
  const suggestedCategory = mlAnalysis.suggestedCategory

  useEffect(() => {
    const cachedCategories = customCategoriesCache.getCategories()
    setCustomCategories(cachedCategories)

    const unsubscribe = customCategoriesCache.subscribe((categories) => {
      setCustomCategories(categories || [])
    })

    customCategoriesCache.loadCustomCategories()

    return unsubscribe
  }, [])

  // Show suggestion for medium confidence predictions
  useEffect(() => {
    if (
      showSuggestions &&
      suggestedCategory &&
      suggestedCategory !== currentCategory &&
      confidence >= 0.80 &&
      confidence < 0.95 &&
      !isAutoExecuted
    ) {
      setShowingSuggestion(true)
    } else {
      setShowingSuggestion(false)
    }
  }, [suggestedCategory, currentCategory, confidence, isAutoExecuted, showSuggestions])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

      // Handle number keys 0-9 for category shortcuts
      if (e.key >= '0' && e.key <= '9') {
        const category = defaultCategories.find(cat => cat.shortcut === e.key)
        if (category) {
          handleCategorySelect(category.id, 'keyboard')
        }
      }

      // Handle suggestion shortcuts
      if (showingSuggestion) {
        if (e.key === 'Enter') {
          e.preventDefault()
          handleAcceptSuggestion()
        } else if (e.key === 'Escape') {
          e.preventDefault()
          handleRejectSuggestion()
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [showingSuggestion])

  const allCategories = [...defaultCategories, ...customCategories.map((cat, idx) => ({
    ...cat,
    priority: 100 + idx
  }))]

  const current = allCategories.find(c => c.id === currentCategory) || defaultCategories[9]
  const suggested = allCategories.find(c => c.id === suggestedCategory)

  const handleCategorySelect = (categoryId, source = 'manual') => {
    // Send training signal to ML based on user action
    const trainingSignal = {
      emailUid: email.uid,
      fromCategory: currentCategory,
      toCategory: categoryId,
      mlSuggestion: suggestedCategory,
      mlConfidence: confidence,
      userAction: source, // 'manual', 'keyboard', 'suggestion_accept', 'suggestion_reject'
      timestamp: Date.now()
    }

    // Send to ML training service
    sendTrainingSignal(trainingSignal)

    onCategoryChange(categoryId)
    setIsOpen(false)
    setShowingSuggestion(false)
  }

  const handleAcceptSuggestion = () => {
    if (suggestedCategory) {
      handleCategorySelect(suggestedCategory, 'suggestion_accept')
    }
  }

  const handleRejectSuggestion = () => {
    setShowingSuggestion(false)
    // Send rejection signal to ML
    sendTrainingSignal({
      emailUid: email.uid,
      mlSuggestion: suggestedCategory,
      mlConfidence: confidence,
      userAction: 'suggestion_reject',
      timestamp: Date.now()
    })
  }

  const handleAlwaysApply = () => {
    // Create automatic rule for similar emails
    createAutoRule(email, suggestedCategory)
    handleAcceptSuggestion()
  }

  const sendTrainingSignal = async (signal) => {
    try {
      await fetch('/api/ml/training-signal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signal)
      })
    } catch (error) {
      console.warn('Failed to send training signal:', error)
    }
  }

  const createAutoRule = async (email, categoryId) => {
    try {
      await fetch('/api/rules/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trigger: {
            type: 'sender',
            value: email.from
          },
          action: {
            type: 'categorize',
            category: categoryId
          },
          confidence_required: 0.90
        })
      })
    } catch (error) {
      console.warn('Failed to create auto rule:', error)
    }
  }

  return (
    <div className="space-y-1">
      {/* Suggestion Bar for medium confidence */}
      {showingSuggestion && suggested && (
        <SuggestionBar
          suggestion={suggested}
          onAccept={handleAcceptSuggestion}
          onReject={handleRejectSuggestion}
          onAlwaysApply={handleAlwaysApply}
        />
      )}

      {/* Category Selector */}
      <div className="relative" ref={dropdownRef}>
        <div className="group relative flex items-center gap-1">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className={`w-8 h-6 rounded flex items-center justify-center text-xs transition-all hover:scale-105 focus:outline-none focus:ring-1 focus:ring-offset-1 ${current.color}`}
            title={`${current.label} (Shortcut: ${current.shortcut || ''})`}
          >
            {current.icon && typeof current.icon === 'function' ? (
              <current.icon className="w-3 h-3" />
            ) : (
              <Mail className="w-3 h-3" />
            )}
          </button>

          {/* Confidence Indicator */}
          <ConfidenceBadge confidence={confidence} isAutoExecuted={isAutoExecuted} />

          {/* Tooltip */}
          <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 text-xs text-white bg-gray-900 rounded whitespace-nowrap z-50">
            {current.label}
            {confidence > 0 && ` (${Math.round(confidence * 100)}% säker)`}
            {current.shortcut && ` • ${current.shortcut}`}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-2 border-transparent border-t-gray-900"></div>
          </div>
        </div>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-48">
            <div className="py-1">
              {allCategories.map((category) => (
                <button
                  key={category.id}
                  onClick={() => handleCategorySelect(category.id)}
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2 ${
                    category.id === currentCategory ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className={`w-6 h-6 rounded flex items-center justify-center ${category.color}`}>
                    {category.icon && typeof category.icon === 'function' ? (
                      <category.icon className="w-3 h-3" />
                    ) : (
                      <Mail className="w-3 h-3" />
                    )}
                  </div>
                  <span className="flex-1">{category.label}</span>
                  {category.shortcut && (
                    <kbd className="px-1 py-0.5 text-xs bg-gray-100 border border-gray-300 rounded">
                      {category.shortcut}
                    </kbd>
                  )}
                  {category.id === suggestedCategory && (
                    <div className="text-xs text-blue-600 font-medium">ML förslag</div>
                  )}
                </button>
              ))}
            </div>
            <div className="border-t border-gray-200 px-3 py-2 text-xs text-gray-500">
              Använd siffertangenter 0-9 som genvägar
            </div>
          </div>
        )}
      </div>
    </div>
  )
}