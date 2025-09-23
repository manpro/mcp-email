import { useEffect, useState } from 'react'
import { Brain, TrendingUp, AlertCircle, CheckCircle, Info } from 'lucide-react'

// Visual component for showing AI confidence
export default function ConfidenceIndicator({ confidence, reason, type = 'badge' }) {
  const [isAnimating, setIsAnimating] = useState(false)

  useEffect(() => {
    setIsAnimating(true)
    const timer = setTimeout(() => setIsAnimating(false), 500)
    return () => clearTimeout(timer)
  }, [confidence])

  const getConfidenceColor = () => {
    if (confidence >= 0.8) return { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' }
    if (confidence >= 0.6) return { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' }
    if (confidence >= 0.4) return { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' }
    return { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300' }
  }

  const getConfidenceIcon = () => {
    if (confidence >= 0.8) return CheckCircle
    if (confidence >= 0.6) return TrendingUp
    if (confidence >= 0.4) return Info
    return AlertCircle
  }

  const colors = getConfidenceColor()
  const Icon = getConfidenceIcon()

  if (type === 'bar') {
    return (
      <div className="w-full">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-700">AI Confidence</span>
          <span className={`text-xs font-bold ${colors.text}`}>
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full ${colors.bg} transition-all duration-500 ease-out ${
              isAnimating ? 'animate-pulse' : ''
            }`}
            style={{ width: `${confidence * 100}%` }}
          >
            <div className="h-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
          </div>
        </div>
        {reason && (
          <p className="text-xs text-gray-500 mt-1 italic">{reason}</p>
        )}
      </div>
    )
  }

  if (type === 'circular') {
    const circumference = 2 * Math.PI * 40
    const strokeDashoffset = circumference - (confidence * circumference)

    return (
      <div className="relative inline-flex items-center justify-center">
        <svg className="w-24 h-24 transform -rotate-90">
          <circle
            cx="48"
            cy="48"
            r="40"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-200"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`${colors.text} transition-all duration-500 ease-out`}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <Icon className={`w-6 h-6 ${colors.text}`} />
          <span className={`text-lg font-bold ${colors.text}`}>
            {Math.round(confidence * 100)}%
          </span>
        </div>
      </div>
    )
  }

  // Default badge type
  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full border ${colors.bg} ${colors.border} ${
      isAnimating ? 'scale-105' : ''
    } transition-transform duration-200`}>
      <Brain className={`w-3.5 h-3.5 ${colors.text}`} />
      <span className={`text-xs font-medium ${colors.text}`}>
        {Math.round(confidence * 100)}%
      </span>
      {reason && (
        <span className="text-xs text-gray-600 ml-1" title={reason}>
          ℹ️
        </span>
      )}
    </div>
  )
}

// Animated loading indicator for AI processing
export function AIProcessingIndicator({ text = 'AI analyserar...' }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
      <div className="relative">
        <Brain className="w-5 h-5 text-blue-600 animate-pulse" />
        <div className="absolute inset-0 animate-ping">
          <Brain className="w-5 h-5 text-blue-400 opacity-75" />
        </div>
      </div>
      <span className="text-sm font-medium text-blue-700">{text}</span>
      <div className="flex gap-0.5">
        <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}

// Confidence trend indicator
export function ConfidenceTrend({ history = [] }) {
  if (!history.length) return null

  const trend = history[history.length - 1] - history[0]
  const isImproving = trend > 0

  return (
    <div className="flex items-center gap-1">
      <TrendingUp
        className={`w-4 h-4 ${isImproving ? 'text-green-600' : 'text-red-600 rotate-180'}`}
      />
      <span className={`text-xs font-medium ${isImproving ? 'text-green-600' : 'text-red-600'}`}>
        {isImproving ? '+' : ''}{Math.round(trend * 100)}%
      </span>
    </div>
  )
}