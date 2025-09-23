import { useState, useEffect } from 'react'
import {
  Zap, Archive, Reply, Forward, Star, Trash2, Clock,
  FolderOpen, Tag, Bell, BellOff, CheckSquare, Calendar,
  Mail, Send, ChevronRight, Sparkles, Brain, TrendingUp
} from 'lucide-react'
import learningService from '../services/learningService'
import ConfidenceIndicator from './ConfidenceIndicator'
import useEmailStore from '../store/emailStore'

// Map action types to icons and labels
const actionConfig = {
  reply: { icon: Reply, label: 'Svara', color: 'blue' },
  forward: { icon: Forward, label: 'Vidarebefordra', color: 'green' },
  archive: { icon: Archive, label: 'Arkivera', color: 'gray' },
  delete: { icon: Trash2, label: 'Ta bort', color: 'red' },
  star: { icon: Star, label: 'Stjärnmärk', color: 'yellow' },
  snooze: { icon: Clock, label: 'Snooze', color: 'purple' },
  move: { icon: FolderOpen, label: 'Flytta', color: 'indigo' },
  label: { icon: Tag, label: 'Etikett', color: 'pink' },
  notify: { icon: Bell, label: 'Notifiera', color: 'orange' },
  mute: { icon: BellOff, label: 'Tysta', color: 'gray' },
  task: { icon: CheckSquare, label: 'Skapa uppgift', color: 'teal' },
  calendar: { icon: Calendar, label: 'Lägg i kalender', color: 'cyan' }
}

export default function PredictiveActionsPanel({ email }) {
  const [predictions, setPredictions] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [actionHistory, setActionHistory] = useState([])
  const { applyAiAction } = useEmailStore()

  useEffect(() => {
    if (email) {
      loadPredictions()
    }
  }, [email])

  const loadPredictions = async () => {
    setIsProcessing(true)

    // Get AI recommendations
    const rec = learningService.getRecommendation(email)
    setRecommendation(rec)

    // Get predictive actions
    const pred = learningService.predictNextAction(email)
    setPredictions(pred)

    setIsProcessing(false)
  }

  const handleAction = async (action, confidence) => {
    // Track the action for learning
    learningService.trackAction(action, email, {
      source: 'predictive_panel',
      confidence
    })

    // Apply the action
    await applyAiAction(email.uid, action)

    // Add to history
    setActionHistory(prev => [...prev, { action, timestamp: Date.now() }])

    // Reload predictions
    loadPredictions()
  }

  const getActionStyle = (color) => {
    const styles = {
      blue: 'bg-blue-100 hover:bg-blue-200 text-blue-700 border-blue-300',
      green: 'bg-green-100 hover:bg-green-200 text-green-700 border-green-300',
      red: 'bg-red-100 hover:bg-red-200 text-red-700 border-red-300',
      yellow: 'bg-yellow-100 hover:bg-yellow-200 text-yellow-700 border-yellow-300',
      purple: 'bg-purple-100 hover:bg-purple-200 text-purple-700 border-purple-300',
      gray: 'bg-gray-100 hover:bg-gray-200 text-gray-700 border-gray-300',
      indigo: 'bg-indigo-100 hover:bg-indigo-200 text-indigo-700 border-indigo-300',
      pink: 'bg-pink-100 hover:bg-pink-200 text-pink-700 border-pink-300',
      orange: 'bg-orange-100 hover:bg-orange-200 text-orange-700 border-orange-300',
      teal: 'bg-teal-100 hover:bg-teal-200 text-teal-700 border-teal-300',
      cyan: 'bg-cyan-100 hover:bg-cyan-200 text-cyan-700 border-cyan-300'
    }
    return styles[color] || styles.gray
  }

  if (!email) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-500 text-center">
          Välj ett email för att se AI-förslag
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-white" />
            <h3 className="text-white font-semibold">AI Predictive Actions</h3>
          </div>
          <Sparkles className="w-4 h-4 text-yellow-300 animate-pulse" />
        </div>
      </div>

      {/* Primary Recommendation */}
      {recommendation?.primaryAction && (
        <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
              Rekommenderad åtgärd
            </span>
            <ConfidenceIndicator
              confidence={recommendation.primaryAction.confidence}
              reason={recommendation.primaryAction.reason}
            />
          </div>

          <button
            onClick={() => handleAction(
              recommendation.primaryAction.action,
              recommendation.primaryAction.confidence
            )}
            className={`w-full flex items-center justify-between p-3 rounded-lg border-2 transition-all ${
              getActionStyle(actionConfig[recommendation.primaryAction.action]?.color)
            } group`}
          >
            <div className="flex items-center gap-3">
              {actionConfig[recommendation.primaryAction.action]?.icon && (
                <div className="p-2 bg-white rounded-lg group-hover:scale-110 transition-transform">
                  {React.createElement(
                    actionConfig[recommendation.primaryAction.action].icon,
                    { className: 'w-5 h-5' }
                  )}
                </div>
              )}
              <div className="text-left">
                <p className="font-medium">
                  {actionConfig[recommendation.primaryAction.action]?.label}
                </p>
                <p className="text-xs opacity-75">
                  {recommendation.primaryAction.reason}
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      )}

      {/* Alternative Actions */}
      {recommendation?.alternatives && recommendation.alternatives.length > 0 && (
        <div className="p-4">
          <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-3">
            Alternativa åtgärder
          </h4>
          <div className="space-y-2">
            {recommendation.alternatives.map((alt, index) => (
              <button
                key={index}
                onClick={() => handleAction(alt.action, alt.confidence)}
                className={`w-full flex items-center justify-between p-2 rounded-lg border transition-all ${
                  getActionStyle(actionConfig[alt.action]?.color)
                } hover:shadow-md`}
              >
                <div className="flex items-center gap-2">
                  {actionConfig[alt.action]?.icon && (
                    React.createElement(
                      actionConfig[alt.action].icon,
                      { className: 'w-4 h-4' }
                    )
                  )}
                  <span className="text-sm font-medium">
                    {actionConfig[alt.action]?.label}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs opacity-75">{alt.reason}</span>
                  <ConfidenceIndicator
                    confidence={alt.confidence}
                    type="badge"
                  />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions Grid */}
      <div className="p-4 border-t border-gray-200">
        <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-3">
          Snabbåtgärder
        </h4>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(actionConfig).slice(0, 8).map(([action, config]) => (
            <button
              key={action}
              onClick={() => handleAction(action, 0.5)}
              className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-all hover:shadow-md group"
              title={config.label}
            >
              {React.createElement(config.icon, {
                className: 'w-4 h-4 mx-auto text-gray-600 group-hover:scale-110 transition-transform'
              })}
            </button>
          ))}
        </div>
      </div>

      {/* Learning Stats */}
      <div className="p-4 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600">
            AI har lärt sig från {learningService.getStatistics().totalActions} åtgärder
          </span>
          <TrendingUp className="w-4 h-4 text-green-600" />
        </div>
      </div>
    </div>
  )
}

// Compact version for email list items
export function PredictiveActionBadge({ email }) {
  const [recommendation, setRecommendation] = useState(null)

  useEffect(() => {
    const rec = learningService.getRecommendation(email)
    setRecommendation(rec)
  }, [email])

  if (!recommendation?.primaryAction || recommendation.primaryAction.confidence < 0.7) {
    return null
  }

  const action = recommendation.primaryAction
  const config = actionConfig[action.action]

  if (!config) return null

  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-gradient-to-r from-blue-50 to-purple-50 rounded-full border border-blue-200">
      {React.createElement(config.icon, { className: 'w-3 h-3 text-blue-600' })}
      <span className="text-xs font-medium text-blue-700">{config.label}</span>
      <span className="text-xs text-blue-500">{Math.round(action.confidence * 100)}%</span>
    </div>
  )
}