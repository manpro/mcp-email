import { useState, useEffect } from 'react'
import { X, Folder, FolderOpen, ChevronRight, ChevronDown, Search } from 'lucide-react'
import useEmailStore from '../store/emailStore'

export default function FolderMoveDialog({ isOpen, onClose, onMove, emailCount }) {
  const { folders, selectedAccountId } = useEmailStore()
  const [selectedFolder, setSelectedFolder] = useState(null)
  const [expandedFolders, setExpandedFolders] = useState(new Set(['INBOX']))
  const [searchQuery, setSearchQuery] = useState('')
  const [folderStructure, setFolderStructure] = useState([])

  useEffect(() => {
    if (isOpen && selectedAccountId) {
      loadFolders()
    }
  }, [isOpen, selectedAccountId])

  const loadFolders = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
      const response = await fetch(`${apiUrl}/api/accounts/${selectedAccountId}/mailboxes`)
      const data = await response.json()

      // Build hierarchical structure
      const structure = buildFolderTree(data.mailboxes || [])
      setFolderStructure(structure)
    } catch (error) {
      console.error('Failed to load folders:', error)
      // Use default folders as fallback
      setFolderStructure([
        { name: 'INBOX', path: 'INBOX', children: [] },
        { name: 'Sent', path: 'Sent', children: [] },
        { name: 'Drafts', path: 'Drafts', children: [] },
        { name: 'Archive', path: 'Archive', children: [] },
        { name: 'Trash', path: 'Trash', children: [] }
      ])
    }
  }

  const buildFolderTree = (folders) => {
    const tree = []
    const folderMap = {}

    // First pass: create all folder objects
    folders.forEach(folder => {
      folderMap[folder.path] = {
        ...folder,
        children: []
      }
    })

    // Second pass: build tree structure
    folders.forEach(folder => {
      if (folder.path.includes('/')) {
        const parentPath = folder.path.substring(0, folder.path.lastIndexOf('/'))
        if (folderMap[parentPath]) {
          folderMap[parentPath].children.push(folderMap[folder.path])
        } else {
          tree.push(folderMap[folder.path])
        }
      } else {
        tree.push(folderMap[folder.path])
      }
    })

    return tree
  }

  const toggleFolder = (folderPath) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(folderPath)) {
        next.delete(folderPath)
      } else {
        next.add(folderPath)
      }
      return next
    })
  }

  const handleMove = async () => {
    if (!selectedFolder) return

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'

      // Move emails to selected folder
      await onMove(selectedFolder)

      onClose()
    } catch (error) {
      console.error('Failed to move emails:', error)
    }
  }

  const filterFolders = (folders, query) => {
    if (!query) return folders

    return folders.reduce((acc, folder) => {
      const matchesQuery = folder.name.toLowerCase().includes(query.toLowerCase())
      const filteredChildren = filterFolders(folder.children || [], query)

      if (matchesQuery || filteredChildren.length > 0) {
        acc.push({
          ...folder,
          children: filteredChildren
        })
      }

      return acc
    }, [])
  }

  const FolderItem = ({ folder, level = 0 }) => {
    const hasChildren = folder.children && folder.children.length > 0
    const isExpanded = expandedFolders.has(folder.path)
    const isSelected = selectedFolder === folder.path

    return (
      <div>
        <div
          className={`flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer rounded-lg mx-1 ${
            isSelected ? 'bg-blue-50 text-blue-600' : ''
          }`}
          style={{ paddingLeft: `${level * 20 + 12}px` }}
          onClick={() => setSelectedFolder(folder.path)}
        >
          {hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                toggleFolder(folder.path)
              }}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          )}

          {!hasChildren && <div className="w-5" />}

          {isExpanded && hasChildren ? (
            <FolderOpen className="w-4 h-4 text-gray-500" />
          ) : (
            <Folder className="w-4 h-4 text-gray-500" />
          )}

          <span className="text-sm flex-1">{folder.name}</span>

          {folder.specialUse && (
            <span className="text-xs text-gray-400">{folder.specialUse}</span>
          )}
        </div>

        {isExpanded && hasChildren && (
          <div>
            {folder.children.map((child) => (
              <FolderItem key={child.path} folder={child} level={level + 1} />
            ))}
          </div>
        )}
      </div>
    )
  }

  const filteredFolders = filterFolders(folderStructure, searchQuery)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] flex flex-col">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Flytta email</h2>
            <p className="text-sm text-gray-500 mt-1">
              {emailCount} email{emailCount > 1 ? 's' : ''} kommer att flyttas
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Sök mappar..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {filteredFolders.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Folder className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>Inga mappar hittades</p>
            </div>
          ) : (
            filteredFolders.map((folder) => (
              <FolderItem key={folder.path} folder={folder} />
            ))
          )}
        </div>

        <div className="p-4 border-t border-gray-200 flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Avbryt
          </button>
          <button
            onClick={handleMove}
            disabled={!selectedFolder}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Flytta
          </button>
        </div>
      </div>
    </div>
  )
}