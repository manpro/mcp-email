import { useState } from 'react'
import {
  Trash2,
  Archive,
  FolderOpen,
  Tag,
  Star,
  Mail,
  MailOpen,
  CheckCircle,
  XCircle,
  MoreVertical
} from 'lucide-react'
import useEmailStore from '../store/emailStore'
import FolderMoveDialog from './FolderMoveDialog'
import CategoryMenu from './CategoryMenu'
import learningService from '../services/learningService'

export default function BulkActionBar({ emails, onRefresh }) {
  const {
    selectedEmails,
    clearSelection,
    selectedAccountId
  } = useEmailStore()

  const [showMoveDialog, setShowMoveDialog] = useState(false)
  const [showCategoryMenu, setShowCategoryMenu] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)

  if (selectedEmails.length === 0) return null

  const selectedEmailObjects = emails.filter(e => selectedEmails.includes(e.uid))

  const handleBulkDelete = async () => {
    if (!confirm(`Ta bort ${selectedEmails.length} valda emails?`)) return

    setIsProcessing(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      await Promise.all(
        selectedEmails.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}`, {
            method: 'DELETE'
          })
        )
      )

      // Track bulk delete
      learningService.trackAction('bulk_delete', null, {
        count: selectedEmails.length
      })

      clearSelection()
      onRefresh()
    } catch (error) {
      console.error('Failed to delete emails:', error)
      alert('Kunde inte ta bort alla emails')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleBulkArchive = async () => {
    setIsProcessing(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      await Promise.all(
        selectedEmails.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}/move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ targetFolder: 'Archive' })
          })
        )
      )

      learningService.trackAction('bulk_archive', null, {
        count: selectedEmails.length
      })

      clearSelection()
      onRefresh()
    } catch (error) {
      console.error('Failed to archive emails:', error)
      alert('Kunde inte arkivera alla emails')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleMarkAsRead = async () => {
    setIsProcessing(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      await Promise.all(
        selectedEmails.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}/read`, {
            method: 'POST'
          })
        )
      )

      clearSelection()
      onRefresh()
    } catch (error) {
      console.error('Failed to mark as read:', error)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleMarkAsUnread = async () => {
    setIsProcessing(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      await Promise.all(
        selectedEmails.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}/unread`, {
            method: 'POST'
          })
        )
      )

      clearSelection()
      onRefresh()
    } catch (error) {
      console.error('Failed to mark as unread:', error)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleBulkCategory = async (category) => {
    setIsProcessing(true)
    try {
      // Track category changes for learning
      selectedEmailObjects.forEach(email => {
        learningService.trackAction('categorize', email, {
          newCategory: category,
          bulkAction: true
        })
      })

      // Here you would normally send to backend
      // For now just track locally

      setShowCategoryMenu(false)
      clearSelection()
      onRefresh()
    } catch (error) {
      console.error('Failed to categorize:', error)
    } finally {
      setIsProcessing(false)
    }
  }

  const moveEmailsToFolder = async (targetFolder) => {
    setIsProcessing(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      await Promise.all(
        selectedEmails.map(uid =>
          fetch(`${apiUrl}/api/accounts/${selectedAccountId}/emails/${uid}/move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ targetFolder })
          })
        )
      )

      learningService.trackAction('bulk_move', null, {
        count: selectedEmails.length,
        targetFolder
      })

      clearSelection()
      setShowMoveDialog(false)
      onRefresh()
    } catch (error) {
      console.error('Failed to move emails:', error)
      alert('Kunde inte flytta alla emails')
    } finally {
      setIsProcessing(false)
    }
  }

  // Get all categories including custom ones
  const defaultCategories = [
    { id: 'newsletter', label: 'Nyhetsbrev', icon: '📰', priority: 1 },
    { id: 'work', label: 'Arbete', icon: '💼', priority: 2 },
    { id: 'personal', label: 'Personligt', icon: '👤', priority: 3 },
    { id: 'invoice', label: 'Faktura', icon: '📄', priority: 4 },
    { id: 'security', label: 'Säkerhet', icon: '🔒', priority: 5 },
    { id: 'meetings', label: 'Möten', icon: '📅', priority: 6 },
    { id: 'automated', label: 'Automatiskt', icon: '🤖', priority: 7 },
    { id: 'social', label: 'Socialt', icon: '💬', priority: 8 },
    { id: 'spam', label: 'Spam', icon: '🚫', priority: 9 },
    { id: 'other', label: 'Övrigt', icon: '📁', priority: 10 }
  ]

  // Load custom categories from localStorage
  const customCategories = JSON.parse(localStorage.getItem('customEmailCategories') || '[]')
    .map((cat, idx) => ({ ...cat, priority: 100 + idx }))

  const allCategories = [...defaultCategories, ...customCategories]

  return (
    <>
      <div className="sticky top-0 z-40 bg-blue-50 border-b border-blue-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-blue-900">
                {selectedEmails.length} email{selectedEmails.length > 1 ? 's' : ''} vald{selectedEmails.length > 1 ? 'a' : ''}
              </span>
            </div>

            <button
              onClick={clearSelection}
              className="text-sm text-blue-600 hover:text-blue-700 underline"
            >
              Avmarkera alla
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Mark as read/unread */}
            <div className="flex items-center border-r border-blue-300 pr-2 gap-1">
              <button
                onClick={handleMarkAsRead}
                disabled={isProcessing}
                className="p-2 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
                title="Markera som läst"
              >
                <MailOpen className="w-4 h-4 text-gray-700" />
              </button>
              <button
                onClick={handleMarkAsUnread}
                disabled={isProcessing}
                className="p-2 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
                title="Markera som oläst"
              >
                <Mail className="w-4 h-4 text-gray-700" />
              </button>
            </div>

            {/* Category */}
            <div className="relative">
              <button
                onClick={() => setShowCategoryMenu(!showCategoryMenu)}
                disabled={isProcessing}
                className="flex items-center gap-2 px-3 py-2 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
                title="Sätt kategori"
              >
                <Tag className="w-4 h-4 text-gray-700" />
                <span className="text-sm text-gray-700">Kategori</span>
              </button>

              {showCategoryMenu && (
                <CategoryMenu
                  categories={allCategories}
                  onSelect={handleBulkCategory}
                  onClose={() => setShowCategoryMenu(false)}
                />
              )}
            </div>

            {/* Move to folder */}
            <button
              onClick={() => setShowMoveDialog(true)}
              disabled={isProcessing}
              className="flex items-center gap-2 px-3 py-2 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
              title="Flytta till mapp"
            >
              <FolderOpen className="w-4 h-4 text-gray-700" />
              <span className="text-sm text-gray-700">Flytta</span>
            </button>

            {/* Archive */}
            <button
              onClick={handleBulkArchive}
              disabled={isProcessing}
              className="flex items-center gap-2 px-3 py-2 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
              title="Arkivera"
            >
              <Archive className="w-4 h-4 text-gray-700" />
              <span className="text-sm text-gray-700">Arkivera</span>
            </button>

            {/* Delete */}
            <button
              onClick={handleBulkDelete}
              disabled={isProcessing}
              className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              title="Ta bort"
            >
              <Trash2 className="w-4 h-4" />
              <span className="text-sm">Ta bort</span>
            </button>
          </div>
        </div>

        {isProcessing && (
          <div className="absolute inset-0 bg-blue-50/80 flex items-center justify-center">
            <div className="bg-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
              <span className="text-sm text-gray-700">Bearbetar...</span>
            </div>
          </div>
        )}
      </div>

      <FolderMoveDialog
        isOpen={showMoveDialog}
        onClose={() => setShowMoveDialog(false)}
        onMove={moveEmailsToFolder}
        emailCount={selectedEmails.length}
      />
    </>
  )
}