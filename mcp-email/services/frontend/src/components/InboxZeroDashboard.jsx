import { useState, useEffect } from 'react'
import {
  Trophy, Target, TrendingUp, Clock, CheckCircle, Mail,
  Star, Zap, Activity, BarChart3, Calendar, Award
} from 'lucide-react'

// Inbox Zero Dashboard - Advanced analytics and achievement tracking
export default function InboxZeroDashboard({
  isOpen = false,
  onClose,
  totalEmails = 0,
  processedEmails = 0,
  selectedEmails = []
}) {
  const [stats, setStats] = useState({
    inboxZeroAchievements: 0,
    dailyProcessed: 0,
    weeklyGoal: 100,
    averageResponseTime: '2.3h',
    productivityScore: 85,
    streak: 3
  })

  const [achievements, setAchievements] = useState([])
  const [weeklyProgress, setWeeklyProgress] = useState([])

  useEffect(() => {
    if (isOpen) {
      loadInboxZeroStats()
      loadAchievements()
      loadWeeklyProgress()
    }
  }, [isOpen, totalEmails, processedEmails])

  const loadInboxZeroStats = async () => {
    try {
      const response = await fetch('/api/inbox-zero/stats')
      const data = await response.json()
      setStats(prevStats => ({ ...prevStats, ...data.stats }))
    } catch (error) {
      console.error('Failed to load inbox zero stats:', error)
    }
  }

  const loadAchievements = async () => {
    try {
      const response = await fetch('/api/inbox-zero/achievements')
      const data = await response.json()
      setAchievements(data.achievements || [])
    } catch (error) {
      console.error('Failed to load achievements:', error)
      // Mock achievements for demo
      setAchievements([
        {
          id: 1,
          title: 'First Steps',
          description: 'Processed your first 10 emails with AI',
          unlocked: true,
          date: '2025-09-24',
          icon: '🎯'
        },
        {
          id: 2,
          title: 'Category Master',
          description: 'Categorized 50 emails correctly',
          unlocked: true,
          date: '2025-09-24',
          icon: '📁'
        },
        {
          id: 3,
          title: 'Inbox Zero Hero',
          description: 'Achieved inbox zero for 3 consecutive days',
          unlocked: false,
          icon: '🏆'
        },
        {
          id: 4,
          title: 'Speed Demon',
          description: 'Process 100 emails in under 1 hour',
          unlocked: false,
          icon: '⚡'
        }
      ])
    }
  }

  const loadWeeklyProgress = async () => {
    try {
      const response = await fetch('/api/inbox-zero/weekly-progress')
      const data = await response.json()
      setWeeklyProgress(data.progress || [])
    } catch (error) {
      console.error('Failed to load weekly progress:', error)
      // Mock data for demo
      setWeeklyProgress([
        { day: 'Mån', processed: 23, goal: 20 },
        { day: 'Tis', processed: 31, goal: 20 },
        { day: 'Ons', processed: 18, goal: 20 },
        { day: 'Tor', processed: 27, goal: 20 },
        { day: 'Fre', processed: 15, goal: 20 },
        { day: 'Lör', processed: 8, goal: 10 },
        { day: 'Sön', processed: 5, goal: 10 }
      ])
    }
  }

  const currentInboxCount = totalEmails - processedEmails
  const inboxZeroProgress = totalEmails > 0 ? (processedEmails / totalEmails) * 100 : 0
  const isInboxZero = currentInboxCount === 0

  const getProductivityColor = (score) => {
    if (score >= 90) return 'text-green-600 bg-green-50'
    if (score >= 70) return 'text-blue-600 bg-blue-50'
    if (score >= 50) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const getStreakIcon = (streak) => {
    if (streak >= 7) return '🔥'
    if (streak >= 3) return '⭐'
    if (streak >= 1) return '✨'
    return '💭'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Inbox Zero Dashboard</h2>
                <p className="text-gray-600">Håll koll på din email-produktivitet</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Main Stats */}
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            {/* Inbox Zero Status */}
            <div className={`p-4 rounded-lg border-2 transition-all ${
              isInboxZero
                ? 'bg-green-50 border-green-200 shadow-lg'
                : 'bg-gray-50 border-gray-200'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <Target className={`w-5 h-5 ${isInboxZero ? 'text-green-600' : 'text-gray-600'}`} />
                <span className="text-sm font-medium text-gray-700">Inbox Status</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {currentInboxCount}
              </div>
              <div className="text-sm text-gray-600">
                {isInboxZero ? '🎉 Inbox Zero!' : 'emails kvar'}
              </div>
              <div className="mt-2 bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    isInboxZero ? 'bg-green-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${Math.min(inboxZeroProgress, 100)}%` }}
                />
              </div>
            </div>

            {/* Daily Progress */}
            <div className="p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-700">Idag Processade</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.dailyProcessed}
              </div>
              <div className="text-sm text-gray-600">
                av {stats.weeklyGoal / 7 | 0} målet
              </div>
            </div>

            {/* Productivity Score */}
            <div className={`p-4 rounded-lg border-2 border-opacity-50 ${getProductivityColor(stats.productivityScore)}`}>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5" />
                <span className="text-sm font-medium text-gray-700">Produktivitet</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.productivityScore}%
              </div>
              <div className="text-sm text-gray-600">
                Genomsnitt: {stats.averageResponseTime}
              </div>
            </div>

            {/* Streak */}
            <div className="p-4 bg-gradient-to-br from-yellow-50 to-orange-50 rounded-lg border-2 border-yellow-200">
              <div className="flex items-center gap-2 mb-2">
                <div className="text-xl">{getStreakIcon(stats.streak)}</div>
                <span className="text-sm font-medium text-gray-700">Streak</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.streak} dagar
              </div>
              <div className="text-sm text-gray-600">
                Konsekutiva framgångar
              </div>
            </div>
          </div>

          {/* Weekly Progress Chart */}
          <div className="mb-8 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              Veckoöversikt
            </h3>
            <div className="grid grid-cols-7 gap-2">
              {weeklyProgress.map((day, index) => {
                const percentage = (day.processed / day.goal) * 100
                const isGoalMet = day.processed >= day.goal

                return (
                  <div key={index} className="text-center">
                    <div className="text-xs font-medium text-gray-600 mb-1">{day.day}</div>
                    <div className="bg-white rounded-lg p-2 border">
                      <div className={`text-sm font-bold ${
                        isGoalMet ? 'text-green-600' : 'text-gray-900'
                      }`}>
                        {day.processed}
                      </div>
                      <div className="text-xs text-gray-500">/{day.goal}</div>
                      <div className="mt-1 bg-gray-200 rounded-full h-1">
                        <div
                          className={`h-1 rounded-full ${
                            isGoalMet ? 'bg-green-500' : 'bg-blue-400'
                          }`}
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Achievements */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Award className="w-5 h-5 text-yellow-600" />
              Prestationer
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {achievements.map(achievement => (
                <div
                  key={achievement.id}
                  className={`p-4 rounded-lg border transition-all ${
                    achievement.unlocked
                      ? 'bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200 shadow-sm'
                      : 'bg-gray-50 border-gray-200 opacity-60'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">{achievement.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className={`font-semibold ${
                          achievement.unlocked ? 'text-gray-900' : 'text-gray-500'
                        }`}>
                          {achievement.title}
                        </h4>
                        {achievement.unlocked && (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                      </div>
                      <p className={`text-sm ${
                        achievement.unlocked ? 'text-gray-600' : 'text-gray-400'
                      }`}>
                        {achievement.description}
                      </p>
                      {achievement.unlocked && achievement.date && (
                        <div className="text-xs text-gray-500 mt-1">
                          Upplåst: {new Date(achievement.date).toLocaleDateString('sv-SE')}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <Zap className="w-5 h-5 text-blue-600" />
              Snabbåtgärder
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <button className="flex items-center gap-2 p-3 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow border">
                <Mail className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium">Bulkprocess</span>
              </button>
              <button className="flex items-center gap-2 p-3 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow border">
                <Star className="w-4 h-4 text-yellow-600" />
                <span className="text-sm font-medium">Prioritera</span>
              </button>
              <button className="flex items-center gap-2 p-3 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow border">
                <Activity className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium">Analytics</span>
              </button>
              <button className="flex items-center gap-2 p-3 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow border">
                <Clock className="w-4 h-4 text-purple-600" />
                <span className="text-sm font-medium">Schemalägg</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}