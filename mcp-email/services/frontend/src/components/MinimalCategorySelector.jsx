import { useState, useRef, useEffect } from 'react'
import learningService from '../services/learningService'
import CategoryMenu from './CategoryMenu'

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

export default function MinimalCategorySelector({ email, currentCategory, onCategoryChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const [customCategories, setCustomCategories] = useState([])
  const dropdownRef = useRef(null)

  useEffect(() => {
    const saved = localStorage.getItem('customEmailCategories')
    if (saved) {
      setCustomCategories(JSON.parse(saved))
    }
  }, [])

  const allCategories = [...defaultCategories, ...customCategories.map((cat, idx) => ({
    ...cat,
    priority: 100 + idx
  }))]

  const current = allCategories.find(c => c.id === currentCategory) || defaultCategories[9]

  const handleCategorySelect = (categoryId) => {
    learningService.trackAction('categorize', email, {
      oldCategory: currentCategory,
      newCategory: categoryId,
      userCorrection: true
    })

    onCategoryChange(categoryId)
    setIsOpen(false)
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="group relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`w-8 h-6 rounded flex items-center justify-center text-xs transition-all hover:scale-105 focus:outline-none focus:ring-1 focus:ring-offset-1 ${current.color}`}
          title={current.label}
        >
          <span className="text-sm">{current.icon}</span>
        </button>

        {/* Tooltip */}
        <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 text-xs text-white bg-gray-900 rounded whitespace-nowrap z-50">
          {current.label}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-2 border-transparent border-t-gray-900"></div>
        </div>
      </div>

      {isOpen && (
        <CategoryMenu
          categories={allCategories}
          onSelect={handleCategorySelect}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}