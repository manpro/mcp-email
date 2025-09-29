import React, { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Plus, X, Info } from 'lucide-react'
import useEmailStore from '../store/emailStore-optimized'
import { categorizeEmail, getCategoryIcon } from '../utils/emailCategories'
import AddCategoryModal from './AddCategoryModal'

const CategoryChip = ({
  category,
  count,
  isActive,
  source,
  onClick,
  onRemove
}) => {
  // Determine border color based on categorization source
  const getBorderColor = (source) => {
    switch (source) {
      case 'ml': return 'border-blue-400 bg-blue-50'
      case 'llm': return 'border-green-400 bg-green-50'
      case 'manual': return 'border-orange-400 bg-orange-50'
      case 'rule': return 'border-gray-300 bg-gray-50'
      default: return 'border-gray-300 bg-gray-50'
    }
  }

  const getSourceLabel = (source) => {
    switch (source) {
      case 'ml': return 'ML-kategoriserad'
      case 'llm': return 'AI-kategoriserad'
      case 'manual': return 'Manuellt vald'
      case 'rule': return 'Regel-baserad'
      default: return 'Automatisk'
    }
  }

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`
        relative inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium
        border transition-all duration-200 hover:shadow-sm
        ${isActive
          ? `${getBorderColor(source)} ring-2 ring-blue-200`
          : `${getBorderColor(source)} hover:shadow-md`
        }
      `}
      title={`${category.label}: ${count} emails (${getSourceLabel(source)})`}
    >
      <span className="text-sm">{getCategoryIcon(category.id)}</span>
      <span className="text-xs font-semibold">{count}</span>

      {/* Source indicator dot */}
      <div
        className={`w-1.5 h-1.5 rounded-full ${
          source === 'ml' ? 'bg-blue-500' :
          source === 'llm' ? 'bg-green-500' :
          source === 'manual' ? 'bg-orange-500' :
          'bg-gray-400'
        }`}
      />

      {/* Remove button on hover */}
      {isActive && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onRemove()
          }}
          className="ml-1 p-0.5 hover:bg-white rounded-full"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </motion.button>
  )
}

const CategoryFilterStrip = ({ emails = [] }) => {
  const { activeFilters, toggleFilter, clearAllFilters } = useEmailStore()
  const [showAddCategory, setShowAddCategory] = useState(false)

  // Handle adding new category
  const handleAddCategory = async (categoryData) => {
    try {
      // Send to backend to create new category
      const response = await fetch('/api/categories', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(categoryData),
      })

      if (!response.ok) {
        throw new Error('Failed to create category')
      }

      console.log('✅ New category added:', categoryData)
      // Category will appear in next email refresh
    } catch (error) {
      console.error('❌ Failed to add category:', error)
      throw error
    }
  }

  // Helper function to get category display names
  const getCategoryDisplayName = (categoryId) => {
    const names = {
      work: 'Arbete',
      personal: 'Personligt',
      newsletter: 'Nyhetsbrev',
      invoice: 'Faktura',
      security: 'Säkerhet',
      meetings: 'Möten',
      social: 'Socialt',
      automated: 'Automatiskt',
      offers: 'Erbjudanden',
      urgent: 'Brådskande',
      spam: 'Spam'
    }
    return names[categoryId] || categoryId.charAt(0).toUpperCase() + categoryId.slice(1)
  }

  // Calculate category statistics with source tracking
  const categoryStats = useMemo(() => {
    if (!emails.length) return []

    const stats = {}

    emails.forEach(email => {
      const category = email.category || categorizeEmail(email)

      // Determine source of categorization
      let source = 'rule' // default
      if (email.category) {
        if (email.manualCategory) source = 'manual'
        else if (email.mlSource === 'llm') source = 'llm'
        else if (email.mlSource === 'ml') source = 'ml'
        else source = 'ml' // assume ML if category exists but no manual flag
      }

      if (!stats[category]) {
        stats[category] = {
          id: category,
          label: getCategoryDisplayName(category),
          count: 0,
          sources: { rule: 0, ml: 0, llm: 0, manual: 0 }
        }
      }

      stats[category].count++
      stats[category].sources[source]++
    })

    // Convert to array and sort by count
    return Object.values(stats)
      .sort((a, b) => b.count - a.count)
      .map(stat => ({
        ...stat,
        // Determine primary source for display
        primarySource: Object.entries(stat.sources)
          .sort(([,a], [,b]) => b - a)[0][0]
      }))
  }, [emails])

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    let mlCount = 0, llmCount = 0, manualCount = 0, ruleCount = 0

    emails.forEach(email => {
      if (email.category) {
        if (email.manualCategory) manualCount++
        else if (email.mlSource === 'llm') llmCount++
        else if (email.mlSource === 'ml') mlCount++
        else mlCount++ // assume ML
      } else {
        ruleCount++
      }
    })

    return { mlCount, llmCount, manualCount, ruleCount }
  }, [emails])

  const totalEmails = emails.length
  const activeFilterCount = activeFilters.size

  return (
    <div className="bg-white border-b border-gray-100 px-4 py-2 space-y-2">
      {/* Category filter chips */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300">
        {/* Total email count */}
        <div className="flex-shrink-0 bg-gray-100 px-3 py-1 rounded-full text-xs font-medium text-gray-700">
          📧 {totalEmails}
        </div>

        {/* Category chips */}
        <div className="flex gap-1.5 min-w-0">
          {categoryStats.map(category => (
            <CategoryChip
              key={category.id}
              category={category}
              count={category.count}
              isActive={activeFilters.has(`category:${category.id}`)}
              source={category.primarySource}
              onClick={() => toggleFilter(`category:${category.id}`)}
              onRemove={() => toggleFilter(`category:${category.id}`)}
            />
          ))}
        </div>

        {/* Add category button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowAddCategory(true)}
          className="flex-shrink-0 w-6 h-6 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center transition-colors"
          title="Lägg till ny kategori"
        >
          <Plus className="w-3 h-3" />
        </motion.button>

        {/* Clear filters button */}
        {activeFilterCount > 0 && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={clearAllFilters}
            className="flex-shrink-0 px-2 py-1 bg-red-100 hover:bg-red-200 text-red-700 rounded-full text-xs font-medium transition-colors"
          >
            Rensa ({activeFilterCount})
          </motion.button>
        )}
      </div>

      {/* Status summary - ultra compact */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>Inbox ({totalEmails})</span>
          {summaryStats.mlCount > 0 && (
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              {summaryStats.mlCount} ML
            </span>
          )}
          {summaryStats.llmCount > 0 && (
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              {summaryStats.llmCount} AI
            </span>
          )}
          {summaryStats.manualCount > 0 && (
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
              {summaryStats.manualCount} manuella
            </span>
          )}
        </div>

        {activeFilterCount > 0 && (
          <span className="text-blue-600 font-medium">
            Visar filtrerade emails ({activeFilterCount} filter aktiva)
          </span>
        )}
      </div>

      {/* Add Category Modal */}
      <AddCategoryModal
        isOpen={showAddCategory}
        onClose={() => setShowAddCategory(false)}
        onAdd={handleAddCategory}
      />
    </div>
  )
}

export default CategoryFilterStrip