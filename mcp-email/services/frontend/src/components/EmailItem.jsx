import { useState, useEffect, memo } from 'react'
import { Mail, Paperclip, Star, Trash2, Archive, FolderOpen, Check, Sparkles, Tag } from 'lucide-react'
import axiosInstance from '../lib/axiosInstance.js'
import useEmailStore from '../store/emailStore-optimized'
import { classifyEmail } from '../services/aiService'
import ConfidenceIndicator from './ConfidenceIndicator'
import { PredictiveActionBadge } from './PredictiveActionsPanel'
import learningService from '../services/learningService'
import EnhancedCategorySelector from './EnhancedCategorySelector'
import EmailCategoryChanger from './EmailCategoryChanger'
import { useUndoRedo } from './UndoRedoBar'
import { useDraggable } from '../hooks/useDragDrop'
import EmailModal from './EmailModal'

const EmailItem = memo(function EmailItem({
  email,
  aiMode,
  onDelete,
  onMove
}) {
  const { selectedEmails, toggleEmailSelection, setAiSuggestions, aiSuggestions, updateEmailCategory } = useEmailStore()
  const { executeWithUndo, createCategorizeAction } = useUndoRedo()
  const isSelected = selectedEmails.includes(email.uid)
  const suggestions = aiSuggestions[email.uid]
  const [aiConfidence, setAiConfidence] = useState(0)
  const [category, setCategory] = useState('other')
  const [showModal, setShowModal] = useState(false)
  const [showCategoryChanger, setShowCategoryChanger] = useState(false)
  const [mlAnalysis, setMlAnalysis] = useState(null)

  // Drag functionality - include selected emails if this email is selected
  const dragData = isSelected && selectedEmails.length > 1
    ? selectedEmails.map(uid => ({ uid }))
    : [email]

  const { dragRef, isDragging } = useDraggable(dragData, {
    type: 'emails',
    onDragStart: () => {
      // If this email isn't selected but others are, clear selection and select this one
      if (!isSelected && selectedEmails.length > 0) {
        // This would need to be passed down as a prop or handled differently
      }
    }
  })

  useEffect(() => {
    // Create AbortController for this effect
    const abortController = new AbortController()

    if (aiMode && !suggestions) {
      classifyEmail(email).then(result => {
        if (!abortController.signal.aborted) {
          setAiSuggestions(email.uid, result)
        }
      })
    }

    const recommendation = learningService.getRecommendation(email)
    setAiConfidence(recommendation?.confidence || 0)

    const detectedCategory = email.category || categorizeEmail(email)
    setCategory(detectedCategory)

    // FIXED: Removed auto-fetching of ML analysis to prevent API flood
    // ML analysis will only be fetched when explicitly requested (e.g., when user interacts with the email)
    // This fixes the hundreds of HTTP 499 cancelled requests issue

    // Set fallback analysis immediately to prevent unnecessary API calls
    if (aiMode && !mlAnalysis) {
      setMlAnalysis({
        confidence: recommendation?.confidence || 0.7,
        suggestedCategory: detectedCategory,
        shouldSuggest: false,
        shouldAutoExecute: false,
        needsManualReview: true
      })
    }

    // Cleanup function to abort requests if component unmounts
    return () => {
      abortController.abort()
    }
  }, [aiMode, email, suggestions, mlAnalysis])

  const fetchMLAnalysis = async (uid, signal = null) => {
    try {
      const response = await axiosInstance.get(`/api/emails/${uid}/analysis`, {
        signal // Pass AbortSignal to axios
      })
      return response.data
    } catch (error) {
      // Don't log cancelled requests as errors
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        console.log(`🚫 ML analysis request cancelled for email ${uid}`)
        throw error
      }

      console.warn(`Failed to fetch ML analysis for email ${uid}:`, error.message)

      // If analysis endpoint fails, return basic analysis
      return {
        confidence: 0.7,
        suggestedCategory: category,
        shouldSuggest: false,
        shouldAutoExecute: false,
        needsManualReview: true
      }
    }
  }

  const categorizeEmail = (email) => {
    const from = (email.from || '').toLowerCase()
    const subject = (email.subject || '').toLowerCase()
    const text = (email.text || email.bodyPreview || '').toLowerCase()

    if (from.includes('newsletter') || from.includes('noreply') ||
        from.includes('marketing') || subject.includes('nyhetsbrev') ||
        text.includes('unsubscribe') || text.includes('avprenumerera')) {
      return 'newsletter'
    }

    if (subject.includes('säkerhet') || subject.includes('verifiering') ||
        subject.includes('lösenord') || subject.includes('security')) {
      return 'security'
    }

    if (subject.includes('möte') || subject.includes('meeting') ||
        subject.includes('kallelse') || text.includes('zoom')) {
      return 'meetings'
    }

    if (from.includes('@company.') || subject.includes('projekt') ||
        subject.includes('deadline') || subject.includes('rapport')) {
      return 'work'
    }

    if (from.includes('automated') || subject.includes('bekräftelse')) {
      return 'automated'
    }

    if (subject.includes('faktura') || subject.includes('invoice') ||
        text.includes('betalning') || text.includes('payment')) {
      return 'invoice'
    }

    return 'personal'
  }

  const formatDate = (date) => {
    const d = new Date(date)
    const today = new Date()
    if (d.toDateString() === today.toDateString()) {
      return d.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString('sv-SE', { month: 'short', day: 'numeric' })
  }

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'newsletter': return '📰'
      case 'personal': return '👤'
      case 'invoice': return '📄'
      case 'calendar': return '📅'
      case 'spam': return '🚫'
      default: return '📧'
    }
  }

  return (
    <div
      ref={dragRef}
      className={`group border-b border-gray-200 hover:bg-gray-50 transition-colors ${
        isSelected ? 'bg-blue-50' : ''
      } ${isDragging ? 'opacity-50' : ''}`}
    >
      <div className="p-3 flex items-start gap-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => toggleEmailSelection(email.uid)}
          className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
          style={{ width: '16px', height: '16px' }}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-gray-900 truncate">
                {email.from?.replace(/["<>]/g, '').split(' ')[0] || 'Unknown'}
              </p>
              {!email.seen && (
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
              )}
            </div>
            <span className="text-xs text-gray-500 flex-shrink-0">
              {formatDate(email.date)}
            </span>
          </div>

          {aiMode && aiConfidence > 0.5 && (
            <div className="flex items-center gap-2 mt-1">
              <ConfidenceIndicator confidence={aiConfidence} type="badge" />
              <PredictiveActionBadge email={email} />
            </div>
          )}

          <p className="text-sm text-gray-800 truncate">
            {email.subject || '(Inget ämne)'}
          </p>

          {/* Email preview - clickable to open modal */}
          <div
            className="mt-2 cursor-pointer hover:bg-gray-50 rounded p-2 -m-2 transition-colors"
            onClick={() => setShowModal(true)}
            onMouseEnter={async () => {
              // Fetch ML analysis on hover if not already loaded and in AI mode
              if (aiMode && !mlAnalysis && email.uid) {
                try {
                  const analysis = await fetchMLAnalysis(email.uid)
                  setMlAnalysis(analysis)
                  if (analysis && analysis.confidence) {
                    setAiConfidence(analysis.confidence)
                  }
                } catch (error) {
                  // Silently fail for hover interactions
                  if (error.name !== 'AbortError' && error.code !== 'ERR_CANCELED') {
                    console.log(`Could not load ML analysis on hover: ${error.message}`)
                  }
                }
              }
            }}
          >
            <p className="text-sm text-gray-600 line-clamp-3 overflow-hidden" style={{
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              lineHeight: '1.4em',
              maxHeight: '4.2em'
            }}>
              {(() => {
                if (email.text) return email.text
                if (email.html) {
                  const stripped = email.html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
                  return stripped
                }
                return email.bodyPreview || email.summary || 'Ingen förhandsvisning tillgänglig'
              })()}
            </p>
            {email.hasAttachments && (
              <div className="flex items-center gap-1 mt-1">
                <Paperclip className="w-3 h-3 text-gray-400" />
                <span className="text-xs text-gray-500">Bilagor</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 mt-2">
            <EnhancedCategorySelector
              email={email}
              currentCategory={category}
              mlAnalysis={mlAnalysis || {
                confidence: aiConfidence,
                suggestedCategory: category,
                shouldSuggest: false,
                shouldAutoExecute: false
              }}
              onCategoryChange={async (newCategory) => {
                const originalCategory = email.category || category

                try {
                  await executeWithUndo(
                    () => createCategorizeAction(email.uid, newCategory, originalCategory),
                    async () => {
                      setCategory(newCategory)
                      updateEmailCategory(email.uid, newCategory)

                      // Send enhanced ML training signal
                      await axiosInstance.post('/api/ml/training-signal', {
                        emailUid: email.uid,
                        fromCategory: originalCategory,
                        toCategory: newCategory,
                        mlSuggestion: mlAnalysis?.suggestedCategory,
                        mlConfidence: mlAnalysis?.confidence || aiConfidence,
                        userAction: 'manual_categorize',
                        timestamp: Date.now()
                      })

                      // Send traditional ML feedback for backward compatibility
                      await axiosInstance.post('/api/ml/feedback', {
                        emailId: email.uid,
                        correction: {
                          category: newCategory,
                          priority: email.priority || 'medium',
                          sentiment: email.sentiment || 'neutral',
                          topics: email.topics || [],
                          action_required: email.actionRequired || false,
                          summary: email.summary || `Email categorized as ${newCategory}`
                        },
                        feedback: `User changed category from "${originalCategory}" to "${newCategory}"`
                      })

                      // Track action
                      learningService.trackAction('categorize', email, {
                        category: newCategory,
                        manual: true
                      })

                      console.log(`✅ Category changed: ${originalCategory} → ${newCategory}`)
                    }
                  )
                } catch (error) {
                  console.error('Failed to change category:', error)
                }
              }}
            />
          </div>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => setShowCategoryChanger(true)}
            className="p-1.5 hover:bg-blue-200 rounded transition-colors"
            title="Ändra kategori"
          >
            <Tag className="w-4 h-4 text-blue-600" />
          </button>
          <button
            onClick={() => onMove && onMove(email)}
            className="p-1.5 hover:bg-gray-200 rounded transition-colors"
            title="Flytta"
          >
            <Archive className="w-4 h-4 text-gray-600" />
          </button>
          <button
            onClick={() => onDelete && onDelete(email)}
            className="p-1.5 hover:bg-gray-200 rounded transition-colors"
            title="Ta bort"
          >
            <Trash2 className="w-4 h-4 text-gray-600" />
          </button>
          <button className="p-1.5 hover:bg-gray-200 rounded transition-colors">
            <Star className="w-4 h-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Email Modal */}
      <EmailModal
        email={email}
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />

      {/* Category Changer Modal */}
      {showCategoryChanger && (
        <EmailCategoryChanger
          email={email}
          onCategoryChange={async (emailId, newCategory) => {
            const originalCategory = email.category || category

            try {
              await executeWithUndo(
                () => createCategorizeAction(email.uid, newCategory, originalCategory),
                async () => {
                  setCategory(newCategory)
                  updateEmailCategory(email.uid, newCategory)

                  // Send ML feedback
                  await axiosInstance.post('/api/ml/feedback', {
                    emailId: email.uid,
                    oldCategory: originalCategory,
                    newCategory: newCategory,
                    userCorrection: true
                  }).catch(error => {
                    console.error('Failed to send ML feedback:', error)
                  })
                }
              )
            } catch (error) {
              console.error('Failed to update category:', error)
            }
          }}
          onClose={() => setShowCategoryChanger(false)}
        />
      )}
    </div>
  )
})

export default EmailItem