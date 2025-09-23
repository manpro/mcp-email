import { useState, useEffect } from 'react'
import { ChevronRight, ChevronDown, Folder, FolderOpen, Inbox, Send, Trash2, Archive, Mail, User } from 'lucide-react'
import useEmailStore from '../store/emailStore'

const iconMap = {
  'INBOX': Inbox,
  'Sent': Send,
  'Trash': Trash2,
  'Archive': Archive,
  'Skickat': Send,
  'Papperskorg': Trash2,
}

function FolderNode({ folder, accountId, level = 0 }) {
  const [isExpanded, setIsExpanded] = useState(
    // Auto-expand INBOX and its immediate children
    folder.path === 'INBOX' || folder.path.startsWith('INBOX/') && !folder.path.includes('/', 6)
  )
  const { selectedFolder, setSelectedFolder, selectedAccountId, setSelectedAccountId } = useEmailStore()
  const isSelected = selectedFolder === folder.path && selectedAccountId === accountId

  const hasChildren = folder.children && Object.keys(folder.children).length > 0
  const Icon = iconMap[folder.name] || iconMap[folder.path] || (isExpanded ? FolderOpen : Folder)

  const handleClick = () => {
    if (hasChildren) {
      setIsExpanded(!isExpanded)
    }
    // Set both the account and folder when clicking a folder
    setSelectedAccountId(accountId)
    setSelectedFolder(folder.path)
  }

  return (
    <div>
      <div
        onClick={handleClick}
        className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-100 transition-colors ${
          isSelected ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
        }`}
        style={{ paddingLeft: `${level * 1.5 + 0.75}rem` }}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded(!isExpanded)
            }}
            className="p-0.5 hover:bg-gray-200 rounded"
          >
            {isExpanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
          </button>
        )}
        {!hasChildren && <div className="w-4" />}

        <Icon className="w-4 h-4" />
        <span className="text-sm font-medium flex-1">{folder.displayName || folder.name}</span>
        {folder.unread > 0 && (
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-600 rounded-full">
            {folder.unread}
          </span>
        )}
      </div>

      {isExpanded && hasChildren && (
        <div>
          {Object.entries(folder.children).map(([key, child]) => (
            <FolderNode key={key} folder={child} accountId={accountId} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

function AccountSection({ account, isExpanded, onToggle }) {
  const { selectedAccountId, selectedFolder, setSelectedFolder } = useEmailStore()
  const [folders, setFolders] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isExpanded && account.id === selectedAccountId) {
      loadFolders()
    }
  }, [isExpanded, account.id, selectedAccountId])

  const buildFolderTree = (mailboxes) => {
    const tree = {}
    const allPaths = new Set()

    // First, collect all paths and ensure parent paths exist
    mailboxes.forEach(mailbox => {
      const parts = mailbox.path.split('/')
      let currentPath = ''
      parts.forEach((part, index) => {
        currentPath = index === 0 ? part : `${currentPath}/${part}`
        allPaths.add(currentPath)
      })
    })

    // Build folder objects for all paths
    const folderMap = {}
    Array.from(allPaths).forEach(path => {
      const mailbox = mailboxes.find(m => m.path === path)
      const parts = path.split('/')
      const name = parts[parts.length - 1]

      folderMap[path] = {
        name: name,
        path: path,
        displayName: mailbox?.name || name,
        unread: mailbox?.unread || 0,
        children: {}
      }
    })

    // Build tree structure
    Object.keys(folderMap).forEach(path => {
      const folder = folderMap[path]
      if (path.includes('/')) {
        // This is a subfolder
        const parentPath = path.substring(0, path.lastIndexOf('/'))
        if (folderMap[parentPath]) {
          folderMap[parentPath].children[folder.name] = folder
        } else {
          // No parent found, add to root
          tree[folder.name] = folder
        }
      } else {
        // Root folder
        tree[folder.name] = folder
      }
    })

    return tree
  }

  const loadFolders = async () => {
    setLoading(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
      // Use mailboxes endpoint which exists
      const response = await fetch(`${apiUrl}/api/accounts/${account.id}/mailboxes`)
      const data = await response.json()

      if (data.mailboxes) {
        // Build hierarchical folder structure
        const folderStructure = buildFolderTree(data.mailboxes)
        setFolders(folderStructure)
      }
    } catch (error) {
      console.error('Failed to load folders for account:', account.id, error)
      // Set default folders if API fails
      setFolders({
        'INBOX': {
          name: 'INBOX',
          path: 'INBOX',
          displayName: 'Inbox',
          unread: 0,
          children: {}
        },
        'Sent': {
          name: 'Sent',
          path: 'Sent',
          displayName: 'Sent',
          children: {}
        },
        'Drafts': {
          name: 'Drafts',
          path: 'Drafts',
          displayName: 'Drafts',
          children: {}
        },
        'Trash': {
          name: 'Trash',
          path: 'Trash',
          displayName: 'Trash',
          children: {}
        },
        'Spam': {
          name: 'Spam',
          path: 'Spam',
          displayName: 'Spam',
          children: {}
        },
        'Archive': {
          name: 'Archive',
          path: 'Archive',
          displayName: 'Archive',
          children: {}
        }
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mb-2">
      {/* Account header */}
      <div
        onClick={onToggle}
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-100 transition-colors"
      >
        <button className="p-0.5 hover:bg-gray-200 rounded">
          {isExpanded ? (
            <ChevronDown className="w-3 h-3" />
          ) : (
            <ChevronRight className="w-3 h-3" />
          )}
        </button>

        <div
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: account.color }}
        />

        <User className="w-4 h-4 text-gray-600" />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {account.displayName}
          </p>
          <p className="text-xs text-gray-500 truncate">
            {account.email}
          </p>
        </div>

        {account.unreadCount > 0 && (
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-600 rounded-full">
            {account.unreadCount}
          </span>
        )}
      </div>

      {/* Account folders */}
      {isExpanded && (
        <div className="ml-4">
          {loading ? (
            <div className="px-3 py-2 text-xs text-gray-500">Loading folders...</div>
          ) : (
            Object.entries(folders).map(([key, folder]) => (
              <FolderNode key={key} folder={folder} accountId={account.id} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default function FolderTree() {
  const { selectedAccountId, accounts, setAccounts } = useEmailStore()
  const [expandedAccounts, setExpandedAccounts] = useState(new Set())

  useEffect(() => {
    loadAccounts()
  }, [])

  // Auto-expand the selected account
  useEffect(() => {
    if (selectedAccountId && !expandedAccounts.has(selectedAccountId)) {
      setExpandedAccounts(prev => new Set([...prev, selectedAccountId]))
    }
  }, [selectedAccountId, expandedAccounts])

  const loadAccounts = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
      const response = await fetch(`${apiUrl}/api/accounts`)
      const data = await response.json()
      setAccounts(data.accounts || [])
    } catch (error) {
      console.error('Failed to load accounts:', error)
      setAccounts([])
    }
  }

  const toggleAccount = (accountId) => {
    setExpandedAccounts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(accountId)) {
        newSet.delete(accountId)
      } else {
        newSet.add(accountId)
      }
      return newSet
    })
  }

  const activeAccounts = accounts.filter(acc => acc.active)

  if (activeAccounts.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 text-center text-gray-500">
          <Mail className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          <p className="text-sm">No active accounts</p>
          <p className="text-xs mt-1">Add an email account to see folders</p>
        </div>
      </div>
    )
  }

  // If only one account, show folders directly without account grouping
  if (activeAccounts.length === 1) {
    const account = activeAccounts[0]
    return (
      <div className="flex-1 overflow-y-auto">
        <AccountSection
          account={account}
          isExpanded={true}
          onToggle={() => {}}
        />
      </div>
    )
  }

  // Multiple accounts - show with account grouping
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="py-2">
        {activeAccounts.map((account) => (
          <AccountSection
            key={account.id}
            account={account}
            isExpanded={expandedAccounts.has(account.id)}
            onToggle={() => toggleAccount(account.id)}
          />
        ))}
      </div>
    </div>
  )
}