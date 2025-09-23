import { useState, useEffect } from 'react'
import { Mail, Paperclip, Star, Trash2, Archive, FolderOpen, Check, Sparkles, MoreVertical } from 'lucide-react'
import useEmailStore from '../store/emailStore-refactored'
import { fetchEmails } from '../services/emailService'
import { classifyEmail } from '../services/aiService'
import ConfidenceIndicator from './ConfidenceIndicator'
import { PredictiveActionBadge } from './PredictiveActionsPanel'
import learningService from '../services/learningService'
import MinimalCategorySelector from './MinimalCategorySelector'
import FolderMoveDialog from './FolderMoveDialog'
import BulkActionBar from './BulkActionBar'

function EmailItem({ email, aiMode, onDelete, onMove }) {
  const { selectedEmails, toggleEmailSelection, setAiSuggestions, aiSuggestions, updateEmailCategory } = useEmailStore()
  const isSelected = selectedEmails.includes(email.uid)
  const suggestions = aiSuggestions[email.uid]
  const [aiConfidence, setAiConfidence] = useState(0)
  const [category, setCategory] = useState('other')
  const [showActions, setShowActions] = useState(false)

  useEffect(() => {
    if (aiMode && !suggestions) {
      // Get AI suggestions for this email
      classifyEmail(email).then(result => {
        setAiSuggestions(email.uid, result)
      })
    }

    // Get AI confidence from learning service
    const recommendation = learningService.getRecommendation(email)
    setAiConfidence(recommendation?.confidence || 0)

    // Determine initial category - use email.category if it exists, otherwise categorize
    const detectedCategory = email.category || categorizeEmail(email)
    setCategory(detectedCategory)
  }, [aiMode, email, suggestions])

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

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-700 border-red-200'
      case 'high': return 'bg-orange-100 text-orange-700 border-orange-200'
      case 'normal': return 'bg-gray-100 text-gray-700 border-gray-200'
      case 'low': return 'bg-green-100 text-green-700 border-green-200'
      default: return 'bg-gray-100 text-gray-700'
    }
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
      className={`group border-b border-gray-200 hover:bg-gray-50 transition-colors cursor-pointer ${
        isSelected ? 'bg-blue-50' : ''
      }`}
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
            {email.subject || '(No subject)'}
          </p>

          <p className="text-sm text-gray-600 mt-1 line-clamp-2 overflow-hidden" style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxHeight: '2.8em'
          }}>
            {email.bodyPreview || email.text?.substring(0, 150) || 'No preview available'}
          </p>

          <div className="flex items-center gap-2 mt-2">
            <MinimalCategorySelector
              email={email}
              currentCategory={category}
              onCategoryChange={async (newCategory) => {
                const originalCategory = email.category
                setCategory(newCategory)
                // Update email in store so SmartFilters can see the change
                updateEmailCategory(email.uid, newCategory)

                // Send feedback to ML system for learning
                try {
                  await fetch('http://localhost:3012/api/ml/feedback', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
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
                  })
                  console.log(`✅ ML feedback sent: ${originalCategory} → ${newCategory}`)
                } catch (error) {
                  console.warn('⚠️ Failed to send ML feedback:', error)
                }

                // Track category change
                learningService.trackAction('categorize', email, {
                  category: newCategory,
                  manual: true
                })
              }}
            />
          </div>

        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
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
    </div>
  )
}

export default function EmailList({ aiMode }) {
  const { emails, setEmails, selectedFolder, selectedAccountId, selectedEmails, activeFilters, clearSelection } = useEmailStore()
  const [loading, setLoading] = useState(false)
  const [showMoveDialog, setShowMoveDialog] = useState(false)
  const [emailToMove, setEmailToMove] = useState(null)

  useEffect(() => {
    if (selectedAccountId) {
      loadEmails()
    }
  }, [selectedFolder, selectedAccountId])

  // Categorization logic (same as SmartFilters)
  const categorizeEmail = (email) => {
    // ALWAYS use backend category if available
    if (email.category) {
      return email.category
    }

    // Fallback to rule-based categorization
    const from = (email.from || '').toLowerCase()
    const subject = (email.subject || '').toLowerCase()
    const text = (email.text || email.bodyPreview || '').toLowerCase()

    if (subject.includes('säkerhet') || subject.includes('verifiering') ||
        subject.includes('lösenord') || subject.includes('inloggning') ||
        subject.includes('security') || subject.includes('verification')) {
      return 'security'
    }

    if (subject.includes('möte') || subject.includes('meeting') ||
        subject.includes('kallelse') || subject.includes('invitation') ||
        text.includes('calendar') || text.includes('zoom')) {
      return 'meetings'
    }

    if (from.includes('newsletter') || from.includes('noreply') ||
        from.includes('marketing') || subject.includes('nyhetsbrev') ||
        text.includes('unsubscribe') || text.includes('avprenumerera')) {
      return 'newsletter'
    }

    if (from.includes('@company.') || from.includes('@work.') ||
        subject.includes('projekt') || subject.includes('rapport') ||
        subject.includes('deadline') || subject.includes('budget')) {
      return 'work'
    }

    if (from.includes('noreply') || from.includes('donotreply') ||
        from.includes('automated') || from.includes('system') ||
        subject.includes('bekräftelse') || subject.includes('confirmation')) {
      return 'automated'
    }

    if (subject.includes('brådskande') || subject.includes('urgent') ||
        subject.includes('akut') || subject.includes('emergency')) {
      return 'urgent'
    }

    return 'personal'
  }

  const determinePriority = (email) => {
    // ALWAYS use backend priority if available
    if (email.priority) {
      return email.priority
    }

    // Fallback to rule-based priority determination
    const subject = (email.subject || '').toLowerCase()
    const text = (email.text || email.bodyPreview || '').toLowerCase()
    const from = (email.from || '').toLowerCase()

    if (subject.includes('kritisk') || subject.includes('critical') ||
        subject.includes('emergency') || subject.includes('urgent')) {
      return 'critical'
    }

    if (subject.includes('viktigt') || subject.includes('important') ||
        subject.includes('brådskande') || subject.includes('deadline') ||
        from.includes('boss') || from.includes('chef')) {
      return 'high'
    }

    if (subject.includes('newsletter') || subject.includes('nyhetsbrev') ||
        from.includes('noreply') || text.includes('unsubscribe')) {
      return 'low'
    }

    return 'medium'
  }

  // Filter emails based on active filters
  const filteredEmails = emails.filter(email => {
    if (activeFilters.size === 0) return true

    // Use backend category if available, otherwise fall back to client-side categorization
    const category = email.category || categorizeEmail(email)
    // Use backend priority if available, otherwise fall back to client-side determination
    const priority = email.priority || determinePriority(email)

    return Array.from(activeFilters).some(filterKey => {
      const [type, value] = filterKey.split(':')
      if (type === 'category' && value === category) return true
      if (type === 'priority' && value === priority) return true
      if (type === 'source') {
        // Handle source filtering based on email metadata
        if (value === 'user_override' && email.manualCategory) return true
        if (value === 'ml_analysis' && email.category && !email.manualCategory) return true
        if (value === 'rule_based' && !email.category && !email.manualCategory) return true
      }
      return false
    })
  })

  const handleDelete = async (email) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
      const response = await fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${email.uid}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Remove email from list
        setEmails(emails.filter(e => e.uid !== email.uid))
        // Track deletion
        learningService.trackAction('delete', email)
      }
    } catch (error) {
      console.error('Failed to delete email:', error)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedEmails.length === 0) return

    const confirmDelete = window.confirm(`Vill du ta bort ${selectedEmails.length} valda emails?`)
    if (!confirmDelete) return

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      // Delete all selected emails
      await Promise.all(
        selectedEmails.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}`, {
            method: 'DELETE'
          })
        )
      )

      // Remove deleted emails from list
      setEmails(emails.filter(e => !selectedEmails.includes(e.uid)))
      clearSelection()
    } catch (error) {
      console.error('Failed to delete emails:', error)
    }
  }

  const handleMove = (email) => {
    setEmailToMove(email)
    setShowMoveDialog(true)
  }

  const handleBulkMove = () => {
    if (selectedEmails.length === 0) return
    setEmailToMove(null) // null indicates bulk move
    setShowMoveDialog(true)
  }

  const moveEmailsToFolder = async (targetFolder) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
      const emailsToMove = emailToMove ? [emailToMove.uid] : selectedEmails

      // Move emails to target folder
      await Promise.all(
        emailsToMove.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}/move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ targetFolder })
          })
        )
      )

      // Remove moved emails from current folder view if not viewing "All Mail"
      if (selectedFolder !== 'All Mail') {
        setEmails(emails.filter(e => !emailsToMove.includes(e.uid)))
      }

      clearSelection()
      setShowMoveDialog(false)
      setEmailToMove(null)
    } catch (error) {
      console.error('Failed to move emails:', error)
    }
  }

  const loadEmails = async () => {
    const { setSelectedAccountId, loadEmails: storeLoadEmails } = useEmailStore.getState()

    // Ensure account ID is set - use a default if none exists
    const accountId = selectedAccountId || 'primary'
    if (!selectedAccountId) {
      setSelectedAccountId(accountId)
    }

    setLoading(true)
    try {
      // Use the refactored store's loadEmails method instead of direct API calls
      await storeLoadEmails()
    } catch (error) {
      console.error('Failed to load emails:', error)
      setEmails([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-gray-500">Laddar emails...</div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <BulkActionBar emails={filteredEmails} onRefresh={loadEmails} />

      {filteredEmails.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <Mail className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-500">
              {emails.length === 0 ? 'Inga emails i denna mapp' : 'Inga emails matchar de valda filtren'}
            </p>
          </div>
        </div>
      ) : (
        <div>
          {filteredEmails.map((email, index) => (
            <EmailItem
              key={email.uid || email.id || `email-${index}`}
              email={email}
              aiMode={aiMode}
              onDelete={handleDelete}
              onMove={handleMove}
            />
          ))}
        </div>
      )}

      <FolderMoveDialog
        isOpen={showMoveDialog}
        onClose={() => {
          setShowMoveDialog(false)
          setEmailToMove(null)
        }}
        onMove={moveEmailsToFolder}
        emailCount={emailToMove ? 1 : selectedEmails.length}
      />
    </div>
  )
}