import { useState, useEffect } from 'react'
import { Brain, Database, TrendingUp } from 'lucide-react'

export default function LearningDataViewer() {
  const [learningData, setLearningData] = useState({
    userActions: [],
    categoryActions: [],
    customCategories: [],
    totalActions: 0
  })

  useEffect(() => {
    // Load all learning data from localStorage
    const userActions = JSON.parse(localStorage.getItem('userActions') || '[]')
    const categoryActions = userActions.filter(a => a.action === 'categorize')
    const customCategories = JSON.parse(localStorage.getItem('customEmailCategories') || '[]')

    setLearningData({
      userActions,
      categoryActions,
      customCategories,
      totalActions: userActions.length
    })

    console.log('Learning Data Summary:', {
      totalActions: userActions.length,
      categoryChanges: categoryActions.length,
      customCategories: customCategories.length,
      recentActions: categoryActions.slice(-10)
    })
  }, [])

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-xl p-4 max-w-sm z-50 border border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-5 h-5 text-purple-600" />
        <h3 className="font-semibold text-gray-800">AI Learning Status</h3>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-gray-600">Total Actions Tracked:</span>
          <span className="font-medium text-gray-900">{learningData.totalActions}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600">Category Changes:</span>
          <span className="font-medium text-green-600">{learningData.categoryActions.length}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-gray-600">Custom Categories:</span>
          <span className="font-medium text-blue-600">{learningData.customCategories.length}</span>
        </div>

        {learningData.categoryActions.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500 mb-2">Recent Learning (last 5):</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {learningData.categoryActions.slice(-5).reverse().map((action, idx) => (
                <div key={idx} className="text-xs bg-gray-50 p-2 rounded">
                  <div className="flex items-center gap-1">
                    <TrendingUp className="w-3 h-3 text-green-500" />
                    <span className="text-gray-700">
                      {action.context.oldCategory} → {action.context.newCategory}
                    </span>
                  </div>
                  <span className="text-gray-400">
                    {new Date(action.timestamp).toLocaleTimeString('sv-SE')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-3 pt-2 border-t border-gray-200">
          <div className="flex items-center gap-2 text-xs">
            <Database className="w-3 h-3 text-gray-400" />
            <span className="text-gray-500">
              Data sparas lokalt för inlärning
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}