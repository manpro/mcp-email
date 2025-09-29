import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Plus, Tag } from 'lucide-react'

const AddCategoryModal = ({ isOpen, onClose, onAdd }) => {
  const [categoryName, setCategoryName] = useState('')
  const [categoryIcon, setCategoryIcon] = useState('📁')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const predefinedIcons = [
    '📧', '📋', '📊', '🔔', '⚡', '🔴', '🟡', '🟢', '🔵', '🟣',
    '📁', '📋', '💼', '🏠', '🛡️', '🚨', '💰', '🎯', '📈', '🔥'
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!categoryName.trim()) return

    setIsSubmitting(true)
    try {
      // Create category ID from name (lowercase, replace spaces with underscores)
      const categoryId = categoryName.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')

      await onAdd({
        id: categoryId,
        name: categoryName.trim(),
        icon: categoryIcon,
        displayName: categoryName.trim()
      })

      // Reset form
      setCategoryName('')
      setCategoryIcon('📁')
      onClose()
    } catch (error) {
      console.error('Failed to add category:', error)
      alert('Misslyckades med att lägga till kategori: ' + error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Tag className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Lägg till kategori</h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Kategorinamn
              </label>
              <input
                type="text"
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="t.ex. Projekt, Kunder, Privat..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
                maxLength={50}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Välj ikon
              </label>
              <div className="grid grid-cols-10 gap-2">
                {predefinedIcons.map((icon, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => setCategoryIcon(icon)}
                    className={`w-8 h-8 text-lg rounded-lg border-2 hover:bg-gray-50 transition-colors ${
                      categoryIcon === icon
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200'
                    }`}
                  >
                    {icon}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Avbryt
              </button>
              <button
                type="submit"
                disabled={!categoryName.trim() || isSubmitting}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>{isSubmitting ? 'Lägger till...' : 'Lägg till'}</span>
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default AddCategoryModal