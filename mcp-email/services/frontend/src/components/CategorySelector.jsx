import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
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

export default function CategorySelector({ email, currentCategory, onCategoryChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const [customCategories, setCustomCategories] = useState([])
  const dropdownRef = useRef(null)

  useEffect(() => {
    // Load custom categories from localStorage
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
    // Track the category change for learning
    learningService.trackAction('categorize', email, {
      oldCategory: currentCategory,
      newCategory: categoryId,
      userCorrection: true
    })

    onCategoryChange(categoryId)
    setIsOpen(false)
  }

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-all
          ${current.color} hover:opacity-80 focus:outline-none focus:ring-1 focus:ring-offset-1`}
      >
        <span className="text-xs">{current.icon}</span>
        <span>{current.label}</span>
        <ChevronDown className={`w-2.5 h-2.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

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