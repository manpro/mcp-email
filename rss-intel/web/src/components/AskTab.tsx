'use client'

import { useState } from 'react'
import { Send, Sparkles, ExternalLink, Calendar, FileText, Loader2 } from 'lucide-react'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Alert, AlertDescription } from './ui/alert'
import { Skeleton } from './ui/skeleton'

interface Citation {
  id: string
  title: string
  url: string
  source: string
  published_at: string
  relevance_score: number
  excerpt: string
}

interface AskResponse {
  answer: string
  citations: Citation[]
  confidence: number
  processing_time: number
}

export function AskTab() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<AskResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<Array<{question: string, answer: string}>>([])

  const handleAsk = async () => {
    if (!question.trim()) return

    setLoading(true)
    setError(null)
    
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      })

      if (!res.ok) {
        throw new Error(`Failed to get answer: ${res.statusText}`)
      }

      const data: AskResponse = await res.json()
      setResponse(data)
      
      // Add to history
      setHistory(prev => [...prev, { question, answer: data.answer }])
      
      // Clear question
      setQuestion('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get answer')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return date.toLocaleDateString()
  }

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) return <Badge className="bg-green-500">High confidence</Badge>
    if (confidence >= 0.6) return <Badge className="bg-yellow-500">Medium confidence</Badge>
    return <Badge className="bg-red-500">Low confidence</Badge>
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Ask Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Ask a Question
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Textarea
              placeholder="What would you like to know? I'll search across all our content to find the best answer with citations..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="min-h-[100px]"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleAsk()
                }
              }}
            />
            
            <div className="flex justify-between items-center">
              <div className="text-xs text-gray-500">
                Press Ctrl+Enter to send
              </div>
              <Button 
                onClick={handleAsk} 
                disabled={!question.trim() || loading}
                className="flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Ask
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
              <div className="grid grid-cols-2 gap-4 mt-6">
                <Skeleton className="h-32" />
                <Skeleton className="h-32" />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Response */}
      {response && !loading && (
        <div className="space-y-6">
          {/* Answer Card */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-start">
                <CardTitle>Answer</CardTitle>
                <div className="flex gap-2">
                  {getConfidenceBadge(response.confidence)}
                  <Badge variant="outline">
                    {response.processing_time.toFixed(2)}s
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="prose dark:prose-invert max-w-none">
                {response.answer.split('\n').map((paragraph, i) => (
                  <p key={i} className="mb-4 text-gray-700 dark:text-gray-300">
                    {paragraph}
                  </p>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Citations */}
          {response.citations.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Sources ({response.citations.length})
              </h3>
              
              <div className="grid gap-4 md:grid-cols-2">
                {response.citations.map((citation, index) => (
                  <Card key={citation.id} className="hover:shadow-lg transition-shadow">
                    <CardContent className="p-4">
                      <div className="space-y-3">
                        <div className="flex justify-between items-start">
                          <Badge variant="outline" className="text-xs">
                            [{index + 1}]
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {Math.round(citation.relevance_score * 100)}% relevant
                          </Badge>
                        </div>
                        
                        <h4 className="font-medium text-sm line-clamp-2">
                          {citation.title}
                        </h4>
                        
                        {citation.excerpt && (
                          <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
                            {citation.excerpt}
                          </p>
                        )}
                        
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <div className="flex items-center gap-2">
                            <span>{citation.source}</span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatDate(citation.published_at)}
                            </span>
                          </div>
                          
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2"
                            onClick={() => window.open(citation.url, '_blank')}
                          >
                            <ExternalLink className="h-3 w-3 mr-1" />
                            Open
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* History */}
      {history.length > 0 && !loading && !response && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Recent Questions</h3>
          <div className="space-y-2">
            {history.slice(-5).reverse().map((item, i) => (
              <Card key={i} className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                    onClick={() => setQuestion(item.question)}>
                <CardContent className="p-3">
                  <p className="text-sm font-medium">{item.question}</p>
                  <p className="text-xs text-gray-500 line-clamp-2 mt-1">{item.answer}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Example Questions */}
      {!response && !loading && history.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Try asking:</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              {[
                "What are the latest developments in AI?",
                "How is blockchain being used in supply chain?",
                "What are the trends in renewable energy?",
                "What security vulnerabilities were discovered recently?",
                "What's new in quantum computing?"
              ].map((example) => (
                <Button
                  key={example}
                  variant="outline"
                  className="justify-start text-left"
                  onClick={() => setQuestion(example)}
                >
                  {example}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}