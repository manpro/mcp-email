import { useState, useEffect } from 'react'
import { Sparkles, Zap, TrendingUp, AlertTriangle, CheckCircle, XCircle, FolderOpen, Trash2, Filter } from 'lucide-react'
import useEmailStore from '../store/emailStore'
import { getBulkSuggestions, trainUserPattern } from '../services/aiService'
import NewsFilter from './NewsFilter'
import PredictiveActionsPanel from './PredictiveActionsPanel'
import learningService from '../services/learningService'

export default function AIPanel() {
  const { selectedEmails, emails, aiSuggestions } = useEmailStore()
  const [bulkSuggestions, setBulkSuggestions] = useState(null)
  const [showNewsFilter, setShowNewsFilter] = useState(false)
  const [stats, setStats] = useState({
    spam: 0,
    newsletters: 0,
    important: 0,
    personal: 0
  })

  useEffect(() => {
    calculateStats()
  }, [emails, aiSuggestions])

  useEffect(() => {
    if (selectedEmails.length > 1) {
      loadBulkSuggestions()
    }
  }, [selectedEmails])

  const calculateStats = () => {
    const newStats = { spam: 0, newsletters: 0, important: 0, personal: 0 }

    emails.forEach(email => {
      const suggestion = aiSuggestions[email.uid]
      if (suggestion) {
        if (suggestion.category === 'spam') newStats.spam++
        if (suggestion.category === 'newsletter') newStats.newsletters++
        if (suggestion.priority === 'high' || suggestion.priority === 'critical') newStats.important++
        if (suggestion.category === 'personal') newStats.personal++
      }
    })

    setStats(newStats)
  }

  const loadBulkSuggestions = async () => {
    const selectedEmailData = emails.filter(e => selectedEmails.includes(e.uid))
    const suggestions = await getBulkSuggestions(selectedEmailData)
    setBulkSuggestions(suggestions)
  }

  const handleAction = async (action, value) => {
    console.log('Executing action:', action, value)

    // Train the AI on user's choice
    selectedEmails.forEach(emailId => {
      const email = emails.find(e => e.uid === emailId)
      if (email) {
        trainUserPattern(email, action, value)
      }
    })
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-yellow-500" />
          AI Assistent
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Email Stats */}
        <div className="p-4 space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Översikt</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-red-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs text-red-700">Spam</span>
                <AlertTriangle className="w-4 h-4 text-red-500" />
              </div>
              <p className="text-2xl font-bold text-red-600 mt-1">{stats.spam}</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs text-blue-700">Nyhetsbrev</span>
                <TrendingUp className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-bold text-blue-600 mt-1">{stats.newsletters}</p>
            </div>
            <div className="p-3 bg-yellow-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs text-yellow-700">Viktiga</span>
                <Zap className="w-4 h-4 text-yellow-500" />
              </div>
              <p className="text-2xl font-bold text-yellow-600 mt-1">{stats.important}</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs text-green-700">Personliga</span>
                <CheckCircle className="w-4 h-4 text-green-500" />
              </div>
              <p className="text-2xl font-bold text-green-600 mt-1">{stats.personal}</p>
            </div>
          </div>
        </div>

        {/* AI Suggestions */}
        {selectedEmails.length > 0 && (
          <div className="p-4 border-t border-gray-200 space-y-3">
            <h4 className="text-sm font-medium text-gray-700">
              AI Förslag ({selectedEmails.length} email vald{selectedEmails.length > 1 ? 'a' : ''})
            </h4>

            {bulkSuggestions && (
              <div className="space-y-2">
                {bulkSuggestions.actions.map((action, index) => (
                  <button
                    key={index}
                    onClick={() => handleAction(action.type, action.value)}
                    className="w-full p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg hover:from-blue-100 hover:to-purple-100 transition-all text-left"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {action.icon === 'folder' && <FolderOpen className="w-4 h-4 text-blue-600" />}
                        {action.icon === 'delete' && <Trash2 className="w-4 h-4 text-red-600" />}
                        <div>
                          <p className="text-sm font-medium text-gray-900">{action.label}</p>
                          <p className="text-xs text-gray-600">{action.reason}</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">
                        {action.confidence}% säkerhet
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* News Filter Toggle */}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={() => setShowNewsFilter(!showNewsFilter)}
            className="w-full p-3 bg-gradient-to-r from-purple-50 to-blue-50 text-purple-700 rounded-lg hover:from-purple-100 hover:to-blue-100 transition-colors text-left"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Nyhetsfiltrering</p>
                  <p className="text-xs opacity-75">Baserat på dina preferenser</p>
                </div>
              </div>
              <span className="text-xs text-gray-500">
                {showNewsFilter ? 'Dölj' : 'Visa'}
              </span>
            </div>
          </button>
        </div>

        {showNewsFilter && <NewsFilter emails={emails} />}

        {/* Quick Actions */}
        <div className="p-4 border-t border-gray-200 space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Snabbåtgärder</h4>
          <div className="space-y-2">
            <button className="w-full p-3 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors text-left">
              <div className="flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Rensa alla spam</p>
                  <p className="text-xs opacity-75">Ta bort {stats.spam} spam-meddelanden</p>
                </div>
              </div>
            </button>

            <button className="w-full p-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-left">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Hantera nyhetsbrev</p>
                  <p className="text-xs opacity-75">Visa {stats.newsletters} nyhetsbrev med avprenumeration</p>
                </div>
              </div>
            </button>

            <button className="w-full p-3 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors text-left">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Smart sortering</p>
                  <p className="text-xs opacity-75">Organisera inbox automatiskt</p>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Custom Actions */}
        <div className="p-4 border-t border-gray-200 space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Custom Actions</h4>
          <div className="space-y-2">
            <button className="w-full p-3 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors text-left">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Fotbollsträning</p>
                  <p className="text-xs opacity-75">Acceptera och lägg till i kalender</p>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}