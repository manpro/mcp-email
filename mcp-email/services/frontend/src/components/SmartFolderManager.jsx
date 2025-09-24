import { useState, useEffect, useRef } from 'react'
import {
  Folder, FolderOpen, Plus, ArrowRight, Move, Archive,
  ChevronRight, ChevronDown, Target, Zap, Clock, CheckCircle
} from 'lucide-react'

// Smart Folder Manager with ML-driven suggestions and auto-creation
export default function SmartFolderManager({
  currentFolder = 'INBOX',
  onFolderChange,
  selectedEmails = [],
  onBulkMove
}) {
  const [folders, setFolders] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [expandedFolders, setExpandedFolders] = useState(new Set(['INBOX']))
  const [dragOverFolder, setDragOverFolder] = useState(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  useEffect(() => {
    loadFolders()
    loadSuggestions()
  }, [])

  const loadFolders = async () => {
    try {
      const response = await fetch('/api/folders')
      const data = await response.json()
      setFolders(data.folders || [])
    } catch (error) {
      console.error('Failed to load folders:', error)
    }
  }

  const loadSuggestions = async () => {
    try {
      const response = await fetch('/api/folders/suggestions')
      const data = await response.json()
      setSuggestions(data.suggestions || [])
    } catch (error) {
      console.error('Failed to load suggestions:', error)
    }
  }

  const handleDragOver = (e, folderPath) => {
    e.preventDefault()
    setDragOverFolder(folderPath)
  }

  const handleDragLeave = () => {
    setDragOverFolder(null)
  }

  const handleDrop = async (e, folderPath) => {
    e.preventDefault()
    setDragOverFolder(null)

    const emailIds = JSON.parse(e.dataTransfer.getData('application/json'))

    try {
      await onBulkMove(emailIds, folderPath)

      // Send learning signal to ML
      await fetch('/api/ml/folder-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          emailIds,
          targetFolder: folderPath,
          action: 'user_drag_drop',
          timestamp: Date.now()
        })
      })

      loadSuggestions() // Refresh suggestions
    } catch (error) {
      console.error('Failed to move emails:', error)
    }
  }

  const createFolder = async (folderName, parentFolder = '') => {
    try {
      const folderPath = parentFolder ? `${parentFolder}/${folderName}` : folderName

      await fetch('/api/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: folderPath,
          autoCreated: false
        })
      })

      loadFolders()
      setShowCreateDialog(false)
    } catch (error) {
      console.error('Failed to create folder:', error)
    }
  }

  const acceptSuggestion = async (suggestion) => {
    try {
      // Auto-create the suggested folder
      await fetch('/api/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: suggestion.folderPath,
          autoCreated: true,
          reason: suggestion.reason
        })
      })

      // Move matching emails if specified
      if (suggestion.emailIds && suggestion.emailIds.length > 0) {
        await onBulkMove(suggestion.emailIds, suggestion.folderPath)
      }

      loadFolders()
      loadSuggestions()
    } catch (error) {
      console.error('Failed to accept suggestion:', error)
    }
  }

  const renderFolder = (folder, level = 0) => {
    const isExpanded = expandedFolders.has(folder.path)
    const hasChildren = folder.children && folder.children.length > 0
    const isActive = currentFolder === folder.path
    const isDragOver = dragOverFolder === folder.path

    return (
      <div key={folder.path} className="folder-item">
        <div
          className={`
            flex items-center px-2 py-1 text-sm cursor-pointer rounded transition-colors
            ${isActive ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100'}
            ${isDragOver ? 'bg-blue-50 border-2 border-blue-300 border-dashed' : ''}
          `}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={() => onFolderChange(folder.path)}
          onDragOver={(e) => handleDragOver(e, folder.path)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, folder.path)}
        >
          {hasChildren && (
            <button
              className="p-0.5 hover:bg-gray-200 rounded mr-1"
              onClick={(e) => {
                e.stopPropagation()
                const newExpanded = new Set(expandedFolders)
                if (isExpanded) {
                  newExpanded.delete(folder.path)
                } else {
                  newExpanded.add(folder.path)
                }
                setExpandedFolders(newExpanded)
              }}
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
          )}

          {!hasChildren && <div className="w-4" />}

          {isExpanded ? (
            <FolderOpen className="w-4 h-4 mr-2 text-blue-600" />
          ) : (
            <Folder className="w-4 h-4 mr-2 text-gray-600" />
          )}

          <span className="flex-1">{folder.name}</span>

          {folder.unreadCount > 0 && (
            <span className="px-1.5 py-0.5 bg-blue-600 text-white text-xs rounded-full">
              {folder.unreadCount}
            </span>
          )}

          {folder.autoCreated && (
            <Zap className="w-3 h-3 text-yellow-500 ml-1" title="Auto-skapad" />
          )}
        </div>

        {hasChildren && isExpanded && (
          <div>
            {folder.children.map(child => renderFolder(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-medium text-gray-900">Mappar</h3>
          <button
            onClick={() => setShowCreateDialog(true)}
            className="p-1 hover:bg-gray-200 rounded"
            title="Skapa ny mapp"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Smart Suggestions */}
      {suggestions.length > 0 && (
        <div className="p-3 bg-blue-50 border-b border-blue-200">
          <h4 className="text-sm font-medium text-blue-800 mb-2 flex items-center">
            <Target className="w-4 h-4 mr-1" />
            Smarta förslag
          </h4>
          {suggestions.slice(0, 3).map((suggestion, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-2 bg-white rounded border mb-1"
            >
              <div className="flex-1">
                <div className="text-sm font-medium">{suggestion.folderName}</div>
                <div className="text-xs text-gray-500">{suggestion.reason}</div>
              </div>
              <button
                onClick={() => acceptSuggestion(suggestion)}
                className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
              >
                Skapa
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Folder Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {folders.map(folder => renderFolder(folder))}
      </div>

      {/* Quick Actions for Selected Emails */}
      {selectedEmails.length > 0 && (
        <div className="p-3 border-t border-gray-200 bg-white">
          <div className="text-sm font-medium mb-2">
            {selectedEmails.length} email(s) valda
          </div>
          <div className="grid grid-cols-2 gap-1">
            <button
              onClick={() => onBulkMove(selectedEmails, 'Archive')}
              className="px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs flex items-center justify-center"
            >
              <Archive className="w-3 h-3 mr-1" />
              Arkivera
            </button>
            <button
              onClick={() => {/* Open folder selector */}}
              className="px-2 py-1 bg-blue-100 hover:bg-blue-200 rounded text-xs flex items-center justify-center"
            >
              <Move className="w-3 h-3 mr-1" />
              Flytta
            </button>
          </div>
        </div>
      )}

      {/* Create Folder Dialog */}
      {showCreateDialog && (
        <CreateFolderDialog
          onClose={() => setShowCreateDialog(false)}
          onCreate={createFolder}
          folders={folders}
        />
      )}
    </div>
  )
}

// Dialog for creating new folders
function CreateFolderDialog({ onClose, onCreate, folders }) {
  const [folderName, setFolderName] = useState('')
  const [parentFolder, setParentFolder] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (folderName.trim()) {
      onCreate(folderName.trim(), parentFolder)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-4 w-80">
        <h3 className="font-medium mb-3">Skapa ny mapp</h3>
        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Mappnamn</label>
            <input
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="t.ex. Projekt, Kunder"
              autoFocus
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Föräldermapp (valfritt)</label>
            <select
              value={parentFolder}
              onChange={(e) => setParentFolder(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Ingen (rotnivå)</option>
              {folders.map(folder => (
                <option key={folder.path} value={folder.path}>
                  {folder.path}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              Avbryt
            </button>
            <button
              type="submit"
              className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Skapa
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}