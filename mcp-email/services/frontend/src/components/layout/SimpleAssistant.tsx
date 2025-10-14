import React, { useState, useRef, useEffect, Suspense } from 'react'
import { MessageSquare, Zap, Mail, AlertTriangle, Send } from 'lucide-react'
import { useEmailsQuery, queryKeys } from '@/hooks/useEmailQueries'
import { useQueryClient } from '@tanstack/react-query'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

// Lazy load SmartActions component
const SmartActions = React.lazy(() => import('@/components/SmartActions'))

/**
 * Del 9: AssistantPanel with Chat functionality and MCP stub
 * Implements working chat with streaming responses
 */

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  streaming?: boolean
}

// Call backend AI Assistant API
async function callAssistantAPI(message: string, context?: any): Promise<string> {
  try {
    const response = await fetch('/api/assistant/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message,
        context
      })
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'AI Assistant error')
    }

    return data.message
  } catch (error) {
    console.error('Assistant API error:', error)
    throw error
  }
}

// Simulate streaming by splitting response into chunks
async function* simulateStreaming(fullMessage: string): AsyncGenerator<string> {
  // Split by words for natural streaming effect
  const words = fullMessage.split(' ')
  for (let i = 0; i < words.length; i++) {
    const chunk = i === 0 ? words[i] : ' ' + words[i]
    await new Promise(resolve => setTimeout(resolve, 40 + Math.random() * 60))
    yield chunk
  }
}

export default function SimpleAssistant() {
  const { data: emails = [] } = useEmailsQuery('default')
  const queryClient = useQueryClient()

  const tabs = [
    { id: 'chat', name: 'Chat', icon: MessageSquare },
    { id: 'actions', name: 'Smart åtgärder', icon: Zap },
    { id: 'newsletters', name: 'Nyhetsbrev', icon: Mail },
    { id: 'spam', name: 'Spam', icon: AlertTriangle }
  ]

  const [activeTab, setActiveTab] = useState('chat')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hej! Jag är din AI-assistent driven av Qwen3 14B. Jag kan hjälpa dig kategorisera emails, skapa automatiska regler, sammanfatta innehåll och svara på frågor om dina emails. Vad kan jag hjälpa dig med?',
      timestamp: new Date()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle send message with real GPT-OSS backend
  const handleSend = async () => {
    if (!inputValue.trim() || isStreaming) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsStreaming(true)

    // Create assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true
    }

    setMessages(prev => [...prev, assistantMessage])

    try {
      // Build context with real email data including body content
      // GPT-OSS 20B has 128K context window, optimal is 20-25 emails for <60s response
      const recentEmails = emails.slice(0, 25).map(e => ({
        subject: e.subject,
        from: e.from,
        category: e.category,
        date: e.date,
        bodyPreview: e.bodyText?.substring(0, 1000) || e.bodyHtml?.substring(0, 1000) || 'Inget innehåll'
      }))

      // Detect if user wants to create a category
      const categoryKeywords = ['skapa kategori', 'ny kategori', 'lägg till kategori', 'kategori för']
      const wantsToCreateCategory = categoryKeywords.some(kw =>
        userMessage.content.toLowerCase().includes(kw)
      )

      let aiResponse

      if (wantsToCreateCategory) {
        // Use category creation endpoint
        const response = await fetch('/api/categories/create-with-ai', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userRequest: userMessage.content,
            emailContext: { recentEmails }
          })
        })

        const data = await response.json()

        if (data.success) {
          // Invalidate labels query to refresh the sidebar immediately
          queryClient.invalidateQueries({ queryKey: queryKeys.labels.all })
          console.log('🔄 Invalidated labels query - sidebar should refresh')

          if (data.action === 'created') {
            aiResponse = `✅ Jag har skapat kategorin "${data.category.displayName}" ${data.category.icon}\n\n` +
              `**Detaljer:**\n` +
              `- Färg: ${data.category.color}\n` +
              `- Automatiskt kategoriserade: ${data.categorizedCount} emails\n\n` +
              `**Regler:**\n` +
              `- Nyckelord: ${data.rules?.keywords?.join(', ') || 'inga'}\n` +
              `- Domäner: ${data.rules?.from_domains?.join(', ') || 'inga'}\n\n` +
              `${data.reason}`
          } else if (data.action === 'use_existing') {
            aiResponse = `ℹ️ En liknande kategori finns redan: "${data.existingCategory}"\n\n${data.reason}\n\nVill du fortfarande skapa en ny kategori? Beskriv hur den ska skilja sig från den befintliga.`
          } else if (data.action === 'already_exists') {
            aiResponse = `ℹ️ ${data.reason}\n\nKategorin "${data.categoryName}" finns redan i systemet.`
          }
        } else {
          aiResponse = `❌ Kunde inte skapa kategorin: ${data.error}\n\nFörsök igen eller formulera din begäran annorlunda.`
        }
      } else {
        // Normal chat endpoint
        aiResponse = await callAssistantAPI(userMessage.content, {
          emailCount: emails.length,
          recentEmails
        })
      }

      // Stream the response word by word for better UX
      let fullContent = ''
      for await (const chunk of simulateStreaming(aiResponse)) {
        fullContent += chunk
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: fullContent }
              : msg
          )
        )
      }

      // Mark streaming as done
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessageId
            ? { ...msg, streaming: false }
            : msg
        )
      )
    } catch (error) {
      console.error('Error streaming response:', error)

      // Show error message
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: 'Tyvärr kunde jag inte ansluta till AI-tjänsten. Försök igen senare.',
                streaming: false
              }
            : msg
        )
      )
    } finally {
      setIsStreaming(false)
      inputRef.current?.focus()
    }
  }

  // Format timestamp
  const formatTime = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    if (diff < 60000) return 'Just nu'
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min sedan`
    if (diff < 86400000) return date.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' })
    return date.toLocaleDateString('sv-SE', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Tab Bar */}
      <div className="flex border-b border-gray-200">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <tab.icon style={{ width: 'var(--icon-size)', height: 'var(--icon-size)' }} />
            <span className="hidden lg:inline">{tab.name}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'chat' && (
          <div className="space-y-4">
            {messages.map(message => (
              <div key={message.id} className="flex items-start gap-3">
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <MessageSquare className="w-4 h-4 text-blue-600" />
                  </div>
                )}
                <div className={`flex-1 ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                  <div>
                    <div
                      className={`rounded-lg p-3 text-sm ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white ml-auto max-w-[80%]'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {message.content}
                      {message.streaming && (
                        <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
                      )}
                    </div>
                    <div className={`mt-1 text-xs text-gray-400 ${message.role === 'user' ? 'text-right' : ''}`}>
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        {activeTab === 'actions' && (
          <Suspense fallback={
            <div className="flex items-center justify-center p-8">
              <LoadingSpinner />
            </div>
          }>
            <SmartActions />
          </Suspense>
        )}

        {activeTab === 'newsletters' && (
          <div className="text-sm text-gray-600">
            <p className="font-medium mb-2">Nyhetsbrev</p>
            <p className="text-gray-400">Översikt över prenumerationer...</p>
          </div>
        )}

        {activeTab === 'spam' && (
          <div className="text-sm text-gray-600">
            <p className="font-medium mb-2">Spam-hantering</p>
            <p className="text-gray-400">Spam-filter statistik...</p>
          </div>
        )}
      </div>

      {/* Input */}
      {activeTab === 'chat' && (
        <div className="p-3 border-t border-gray-200">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={isStreaming ? 'Väntar på svar...' : 'Skriv ett meddelande...'}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isStreaming}
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isStreaming}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send style={{ width: '16px', height: '16px' }} />
              <span className="hidden sm:inline">Skicka</span>
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-400 text-center">
            Tryck Enter för att skicka • Drivs av Qwen3 14B
          </div>
        </div>
      )}
    </div>
  )
}