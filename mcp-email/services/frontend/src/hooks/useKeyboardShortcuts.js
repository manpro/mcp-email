import { useEffect, useCallback, useState } from 'react'
import useEmailStore from '../store/emailStore'
import learningService from '../services/learningService'

// Keyboard shortcuts configuration
const shortcuts = {
  // Navigation
  'j': { action: 'nextEmail', description: 'Nästa email' },
  'k': { action: 'prevEmail', description: 'Föregående email' },
  'g i': { action: 'goToInbox', description: 'Gå till inkorg' },
  'g s': { action: 'goToSent', description: 'Gå till skickat' },
  'g d': { action: 'goToDrafts', description: 'Gå till utkast' },
  'g a': { action: 'goToArchive', description: 'Gå till arkiv' },
  '/': { action: 'search', description: 'Sök' },

  // Actions
  'r': { action: 'reply', description: 'Svara' },
  'a': { action: 'replyAll', description: 'Svara alla' },
  'f': { action: 'forward', description: 'Vidarebefordra' },
  's': { action: 'star', description: 'Stjärnmärk/avmärk' },
  'e': { action: 'archive', description: 'Arkivera' },
  '#': { action: 'delete', description: 'Ta bort' },
  'z': { action: 'undo', description: 'Ångra' },
  'u': { action: 'markUnread', description: 'Markera som oläst' },
  'shift+u': { action: 'markRead', description: 'Markera som läst' },
  'b': { action: 'snooze', description: 'Snooze' },
  'l': { action: 'label', description: 'Lägg till etikett' },
  'm': { action: 'mute', description: 'Tysta konversation' },

  // Selection
  'x': { action: 'select', description: 'Välj/avvälj email' },
  '*+a': { action: 'selectAll', description: 'Välj alla' },
  '*+n': { action: 'selectNone', description: 'Avmarkera alla' },
  '*+r': { action: 'selectRead', description: 'Välj lästa' },
  '*+u': { action: 'selectUnread', description: 'Välj olästa' },
  '*+s': { action: 'selectStarred', description: 'Välj stjärnmärkta' },

  // AI shortcuts
  'shift+a': { action: 'aiSuggest', description: 'Visa AI-förslag' },
  'shift+p': { action: 'aiPredict', description: 'AI-prediktion' },
  'shift+c': { action: 'aiCategorize', description: 'AI-kategorisering' },
  'shift+s': { action: 'aiSummary', description: 'AI-sammanfattning' },

  // Interface
  'c': { action: 'compose', description: 'Skriv nytt' },
  '?': { action: 'help', description: 'Visa hjälp' },
  'esc': { action: 'escape', description: 'Avbryt/stäng' },
  '.': { action: 'moreActions', description: 'Fler åtgärder' },
  'v': { action: 'viewConversation', description: 'Visa konversation' },
  'n': { action: 'newer', description: 'Nyare konversation' },
  'p': { action: 'older', description: 'Äldre konversation' }
}

export default function useKeyboardShortcuts() {
  const {
    selectedEmails,
    toggleEmailSelection,
    selectAllEmails,
    clearSelection,
    setSelectedFolder,
    applyAiAction,
    emails,
    selectedAccountId
  } = useEmailStore()

  const [currentEmailIndex, setCurrentEmailIndex] = useState(0)
  const [commandBuffer, setCommandBuffer] = useState('')
  const [showHelp, setShowHelp] = useState(false)

  const executeShortcut = useCallback((action) => {
    const currentEmail = emails[currentEmailIndex]

    // Track keyboard shortcut usage for learning
    if (currentEmail) {
      learningService.trackAction(action, currentEmail, {
        source: 'keyboard_shortcut',
        shortcut: action
      })
    }

    switch (action) {
      // Navigation
      case 'nextEmail':
        setCurrentEmailIndex(prev => Math.min(prev + 1, emails.length - 1))
        break
      case 'prevEmail':
        setCurrentEmailIndex(prev => Math.max(prev - 1, 0))
        break
      case 'goToInbox':
        setSelectedFolder('INBOX')
        break
      case 'goToSent':
        setSelectedFolder('Sent')
        break
      case 'goToDrafts':
        setSelectedFolder('Drafts')
        break
      case 'goToArchive':
        setSelectedFolder('Archive')
        break
      case 'search':
        document.querySelector('input[type="search"]')?.focus()
        break

      // Actions on current email
      case 'reply':
        if (currentEmail) applyAiAction(currentEmail.uid, 'reply')
        break
      case 'replyAll':
        if (currentEmail) applyAiAction(currentEmail.uid, 'replyAll')
        break
      case 'forward':
        if (currentEmail) applyAiAction(currentEmail.uid, 'forward')
        break
      case 'star':
        if (currentEmail) applyAiAction(currentEmail.uid, 'star')
        break
      case 'archive':
        if (currentEmail) applyAiAction(currentEmail.uid, 'archive')
        break
      case 'delete':
        if (currentEmail) applyAiAction(currentEmail.uid, 'delete')
        break
      case 'markUnread':
        if (currentEmail) applyAiAction(currentEmail.uid, 'markUnread')
        break
      case 'markRead':
        if (currentEmail) applyAiAction(currentEmail.uid, 'markRead')
        break
      case 'snooze':
        if (currentEmail) applyAiAction(currentEmail.uid, 'snooze')
        break
      case 'mute':
        if (currentEmail) applyAiAction(currentEmail.uid, 'mute')
        break

      // Selection
      case 'select':
        if (currentEmail) toggleEmailSelection(currentEmail.uid)
        break
      case 'selectAll':
        selectAllEmails()
        break
      case 'selectNone':
        clearSelection()
        break

      // AI actions
      case 'aiSuggest':
        if (currentEmail) {
          const recommendation = learningService.getRecommendation(currentEmail)
          if (recommendation?.primaryAction) {
            applyAiAction(currentEmail.uid, recommendation.primaryAction.action)
          }
        }
        break
      case 'aiPredict':
        if (currentEmail) {
          const predictions = learningService.predictNextAction(currentEmail)
          if (predictions[0]) {
            applyAiAction(currentEmail.uid, predictions[0].action)
          }
        }
        break

      // Interface
      case 'help':
        setShowHelp(!showHelp)
        break
      case 'escape':
        clearSelection()
        setShowHelp(false)
        break

      default:
        console.log('Unhandled shortcut action:', action)
    }
  }, [emails, currentEmailIndex, selectedEmails])

  useEffect(() => {
    const handleKeyPress = (e) => {
      // Don't trigger shortcuts when typing in input fields
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return
      }

      // Build key combination string
      let key = ''
      if (e.ctrlKey) key += 'ctrl+'
      if (e.altKey) key += 'alt+'
      if (e.shiftKey) key += 'shift+'
      if (e.metaKey) key += 'cmd+'

      // Handle special keys
      if (e.key === 'Enter') key += 'enter'
      else if (e.key === 'Escape') key += 'esc'
      else if (e.key === ' ') key += 'space'
      else if (e.key === 'ArrowUp') key += 'up'
      else if (e.key === 'ArrowDown') key += 'down'
      else if (e.key === 'ArrowLeft') key += 'left'
      else if (e.key === 'ArrowRight') key += 'right'
      else key += e.key.toLowerCase()

      // Check for two-key combinations (like 'g i')
      if (commandBuffer) {
        const combo = `${commandBuffer} ${key}`
        if (shortcuts[combo]) {
          e.preventDefault()
          executeShortcut(shortcuts[combo].action)
          setCommandBuffer('')
          return
        }
        // Clear buffer if no match
        setCommandBuffer('')
      }

      // Check for single key shortcuts
      if (shortcuts[key]) {
        e.preventDefault()
        executeShortcut(shortcuts[key].action)
      } else if (key === 'g' || key === '*') {
        // Start command buffer for two-key combos
        e.preventDefault()
        setCommandBuffer(key)
        // Clear buffer after 1 second
        setTimeout(() => setCommandBuffer(''), 1000)
      }
    }

    document.addEventListener('keydown', handleKeyPress)
    return () => document.removeEventListener('keydown', handleKeyPress)
  }, [commandBuffer, executeShortcut])

  return {
    shortcuts,
    showHelp,
    setShowHelp,
    currentEmailIndex,
    commandBuffer
  }
}

// Help modal component
export function KeyboardShortcutsHelp({ isOpen, onClose }) {
  if (!isOpen) return null

  const groupedShortcuts = {
    'Navigation': ['j', 'k', 'g i', 'g s', 'g d', 'g a', '/'],
    'Åtgärder': ['r', 'a', 'f', 's', 'e', '#', 'z', 'u', 'shift+u', 'b', 'l', 'm'],
    'Markering': ['x', '*+a', '*+n', '*+r', '*+u', '*+s'],
    'AI': ['shift+a', 'shift+p', 'shift+c', 'shift+s'],
    'Gränssnitt': ['c', '?', 'esc', '.', 'v', 'n', 'p']
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-3xl max-h-[80vh] overflow-auto p-6"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Tangentbordsgenvägar</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <span className="text-2xl">×</span>
          </button>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {Object.entries(groupedShortcuts).map(([group, keys]) => (
            <div key={group}>
              <h3 className="font-semibold text-gray-700 mb-2">{group}</h3>
              <div className="space-y-1">
                {keys.map(key => (
                  <div key={key} className="flex items-center justify-between">
                    <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-sm font-mono">
                      {key}
                    </kbd>
                    <span className="text-sm text-gray-600 ml-2">
                      {shortcuts[key]?.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-700">
            <strong>Tips:</strong> Tryck <kbd className="px-1 bg-white rounded">?</kbd> när som helst för att visa denna hjälp
          </p>
        </div>
      </div>
    </div>
  )
}