'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Skeleton } from './ui/skeleton'
import { Clock, Calendar, ExternalLink, RefreshCw, Coffee, Sun, Moon } from 'lucide-react'

interface BriefingItem {
  id: number
  title: string
  summary: string
  ai_summary?: string
  url: string
  source: string
  published_at: string
  reasons: string[]
  score: number
  has_image: boolean
  image_url?: string
  position: number
}

interface Briefing {
  briefing_date: string
  time_slot: string
  title: string
  subtitle: string
  generated_at: string
  published: boolean
  items: BriefingItem[]
  metrics: {
    total_articles_considered: number
    articles_selected: number
    ai_summaries_generated: number
  }
}

interface BriefingsData {
  date: string
  briefings: {
    morning?: Briefing
    lunch?: Briefing
    evening?: Briefing
  }
}

const TIME_SLOT_CONFIG = {
  morning: {
    icon: Coffee,
    label: 'Morning',
    description: 'Overnight and early morning news',
    color: 'bg-orange-100 text-orange-800'
  },
  lunch: {
    icon: Sun,
    label: 'Lunch',
    description: 'Morning developments and updates',
    color: 'bg-yellow-100 text-yellow-800'
  },
  evening: {
    icon: Moon,
    label: 'Evening',
    description: 'Daily summary and analysis',
    color: 'bg-blue-100 text-blue-800'
  }
}

export default function BriefingsTab() {
  const [briefingsData, setBriefingsData] = useState<Record<string, BriefingsData>>({})
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState<string | null>(null)

  // Generate last 3 days
  const dates = Array.from({ length: 3 }, (_, i) => {
    const date = new Date()
    date.setDate(date.getDate() - i)
    return date.toISOString().split('T')[0]
  })

  useEffect(() => {
    loadBriefings()
  }, [])

  const loadBriefings = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Load briefings for the last 3 days
      const briefingsPromises = dates.map(async (date) => {
        const response = await fetch(`/api/proxy/briefings/${date}`)
        if (response.ok) {
          const data = await response.json()
          return { date, data }
        }
        return { date, data: null }
      })

      const results = await Promise.all(briefingsPromises)
      const briefingsMap: Record<string, BriefingsData> = {}
      
      results.forEach(({ date, data }) => {
        if (data) {
          briefingsMap[date] = data
        }
      })

      setBriefingsData(briefingsMap)
    } catch (err) {
      console.error('Error loading briefings:', err)
      setError('Could not load briefings')
    } finally {
      setLoading(false)
    }
  }

  const generateBriefing = async (date: string, timeSlot: string) => {
    setGenerating(`${date}-${timeSlot}`)
    setError(null)

    try {
      const response = await fetch(`/api/proxy/briefings/${date}/${timeSlot}/generate`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error(`Failed to generate briefing: ${response.status}`)
      }

      const result = await response.json()
      console.log('Generated briefing:', result)

      // Reload briefings for this date
      const updatedResponse = await fetch(`/api/proxy/briefings/${date}`)
      if (updatedResponse.ok) {
        const updatedData = await updatedResponse.json()
        setBriefingsData(prev => ({
          ...prev,
          [date]: updatedData
        }))
      }
    } catch (err) {
      console.error('Error generating briefing:', err)
      setError('Could not generate briefing')
    } finally {
      setGenerating(null)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const today = new Date()
    const yesterday = new Date()
    yesterday.setDate(today.getDate() - 1)
    
    if (date.toDateString() === today.toDateString()) return 'Today'
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
    
    return date.toLocaleDateString('en-US', { 
      weekday: 'long',
      month: 'long', 
      day: 'numeric' 
    })
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('sv-SE', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getBriefingForDate = (date: string): BriefingsData | null => {
    return briefingsData[date] || null
  }

  const renderBriefingCard = (briefing: Briefing | undefined, timeSlot: string, date: string) => {
    const config = TIME_SLOT_CONFIG[timeSlot as keyof typeof TIME_SLOT_CONFIG]
    const Icon = config.icon
    const isGenerating = generating === `${date}-${timeSlot}`

    if (!briefing) {
      return (
        <Card key={timeSlot} className="h-64">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-2">
              <Icon className="h-5 w-5" />
              <CardTitle className="text-lg">{config.label}</CardTitle>
              <Badge variant="outline" className={config.color}>
                Ej genererad
              </Badge>
            </div>
            <CardDescription>{config.description}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center flex-1">
            <p className="text-sm text-muted-foreground mb-4 text-center">
              No briefing available yet
            </p>
            <Button 
              onClick={() => generateBriefing(date, timeSlot)}
              disabled={isGenerating}
              variant="outline"
              size="sm"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Generater...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Generate
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )
    }

    return (
      <Card key={timeSlot} className="cursor-pointer hover:shadow-md transition-shadow">
        <CardHeader 
          className="pb-4"
          onClick={() => setSelectedTimeSlot(`${date}-${timeSlot}`)}
        >
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5" />
            <CardTitle className="text-lg">{config.label}</CardTitle>
            <Badge variant="secondary" className={config.color}>
              {briefing.items.length} articles
            </Badge>
          </div>
          <CardDescription>
            {briefing.subtitle}
          </CardDescription>
          <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatTime(briefing.generated_at)}
            </div>
            {briefing.metrics.ai_summaries_generated > 0 && (
              <Badge variant="outline" className="text-xs">
                {briefing.metrics.ai_summaries_generated} AI summaries
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {briefing.items.slice(0, 3).map((item, index) => (
              <div key={item.id} className="text-sm">
                <div className="font-medium line-clamp-1">{item.title}</div>
                <div className="text-muted-foreground text-xs">{item.source}</div>
              </div>
            ))}
            {briefing.items.length > 3 && (
              <div className="text-xs text-muted-foreground">
                +{briefing.items.length - 3} more articles
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  const renderDetailedView = () => {
    if (!selectedTimeSlot) return null

    const [date, timeSlot] = selectedTimeSlot.split('-')
    const briefingData = getBriefingForDate(date)
    const briefing = briefingData?.briefings[timeSlot as keyof typeof briefingData.briefings]

    if (!briefing) return null

    const config = TIME_SLOT_CONFIG[timeSlot as keyof typeof TIME_SLOT_CONFIG]
    const Icon = config.icon

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
          <div className="flex items-center justify-between p-6 border-b">
            <div className="flex items-center gap-3">
              <Icon className="h-6 w-6" />
              <div>
                <h2 className="text-xl font-semibold">{briefing.title}</h2>
                <p className="text-muted-foreground">{briefing.subtitle}</p>
              </div>
            </div>
            <Button 
              variant="ghost" 
              onClick={() => setSelectedTimeSlot(null)}
            >
              ×
            </Button>
          </div>

          <div className="overflow-y-auto max-h-[calc(90vh-120px)] p-6">
            <div className="space-y-6">
              {briefing.items.map((item, index) => (
                <Card key={item.id} className="border-l-4 border-l-blue-500">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-base mb-2">{item.title}</CardTitle>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{item.source}</span>
                          <span>{formatTime(item.published_at)}</span>
                          {item.reasons && item.reasons.length > 0 && (
                            <div className="flex gap-1">
                              {item.reasons.slice(0, 2).map(reason => (
                                <Badge key={reason} variant="outline" className="text-xs">
                                  {reason}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <Badge variant="secondary" className="ml-2">
                        #{index + 1}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {item.ai_summary && (
                        <div className="bg-blue-50 p-3 rounded-md">
                          <div className="text-xs font-medium text-blue-800 mb-1">AI Summary</div>
                          <p className="text-sm text-blue-900">{item.ai_summary}</p>
                        </div>
                      )}
                      <p className="text-sm text-gray-600">{item.summary}</p>
                      <div className="flex items-center justify-between">
                        <div className="flex gap-2">
                          <Badge variant="outline" className="text-xs">
                            Relevans: {Math.round(item.score * 100)}%
                          </Badge>
                          {item.has_image && (
                            <Badge variant="outline" className="text-xs">
                              Har bild
                            </Badge>
                          )}
                        </div>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => window.open(item.url, '_blank')}
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Läs mer
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Daily Briefings</h2>
          <Skeleton className="h-10 w-32" />
        </div>
        
        {dates.map(date => (
          <div key={date} className="space-y-4">
            <h3 className="text-lg font-medium">{formatDate(date)}</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-64" />
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Daily Briefings</h2>
          <Button onClick={loadBriefings} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Försök igen
          </Button>
        </div>
        
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <p className="text-red-600 mb-4">{error}</p>
              <Button onClick={loadBriefings} variant="outline">
                Ladda om
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Daily Briefings</h2>
          <p className="text-muted-foreground">
            Important news summarized for morning, lunch and evening
          </p>
        </div>
        <Button onClick={loadBriefings} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Uppdatera
        </Button>
      </div>

      {dates.map(date => {
        const briefingData = getBriefingForDate(date)
        
        return (
          <div key={date} className="space-y-4">
            <div className="flex items-center gap-3">
              <Calendar className="h-5 w-5" />
              <h3 className="text-lg font-medium">{formatDate(date)}</h3>
              <Badge variant="outline">
                {date === dates[0] ? 'Senaste' : ''}
              </Badge>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(TIME_SLOT_CONFIG).map(([timeSlot, config]) => {
                const briefing = briefingData?.briefings[timeSlot as keyof typeof briefingData.briefings]
                return renderBriefingCard(briefing, timeSlot, date)
              })}
            </div>
          </div>
        )
      })}

      {selectedTimeSlot && renderDetailedView()}
    </div>
  )
}