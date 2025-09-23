import { useState, useEffect } from 'react'
import { Plus, Mail, Settings, Trash2, Check, X, Eye, EyeOff } from 'lucide-react'
import useEmailStore from '../store/emailStore'

function AccountItem({ account, onToggle, onRemove, onSelect, isSelected }) {
  const unreadBadge = account.unreadCount > 0 && (
    <span className="ml-auto bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
      {account.unreadCount}
    </span>
  )

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
        isSelected ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
      } ${!account.active ? 'opacity-50' : ''}`}
      onClick={() => onSelect(account.id)}
    >
      <div
        className="w-3 h-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: account.color }}
      />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {account.displayName}
        </p>
        <p className="text-xs text-gray-500 truncate">
          {account.email}
        </p>
      </div>

      {unreadBadge}

      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => onToggle(account.id, !account.active)}
          className="p-1 hover:bg-gray-200 rounded transition-colors"
          title={account.active ? "Deactivate" : "Activate"}
        >
          {account.active ? (
            <Eye className="w-4 h-4 text-gray-600" />
          ) : (
            <EyeOff className="w-4 h-4 text-gray-400" />
          )}
        </button>
        <button
          onClick={() => onRemove(account.id)}
          className="p-1 hover:bg-red-100 rounded transition-colors"
          title="Remove account"
        >
          <Trash2 className="w-4 h-4 text-red-500" />
        </button>
      </div>
    </div>
  )
}

function AddAccountForm({ onAdd, onCancel }) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    displayName: '',
    provider: 'auto'
  })

  const providers = [
    { value: 'auto', label: 'Auto-detect' },
    { value: 'gmail', label: 'Gmail' },
    { value: 'outlook', label: 'Outlook' },
    { value: 'oneCom', label: 'One.com' },
    { value: 'custom', label: 'Custom IMAP' }
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    await onAdd(formData)
    setFormData({ email: '', password: '', displayName: '', provider: 'auto' })
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-white rounded-lg shadow-sm border">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Add Email Account</h3>

      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-700 mb-1">Email Address</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="user@example.com"
            required
          />
        </div>

        <div>
          <label className="block text-xs text-gray-700 mb-1">Password</label>
          <input
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••••"
            required
          />
        </div>

        <div>
          <label className="block text-xs text-gray-700 mb-1">Display Name (optional)</label>
          <input
            type="text"
            value={formData.displayName}
            onChange={(e) => setFormData({...formData, displayName: e.target.value})}
            className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Work Email"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-700 mb-1">Provider</label>
          <select
            value={formData.provider}
            onChange={(e) => setFormData({...formData, provider: e.target.value})}
            className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {providers.map(provider => (
              <option key={provider.value} value={provider.value}>
                {provider.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2 mt-4">
        <button
          type="submit"
          className="flex-1 px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Add Account
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

export default function AccountManager() {
  const [accounts, setAccounts] = useState([])
  const [showAddForm, setShowAddForm] = useState(false)
  const [loading, setLoading] = useState(false)
  const { selectedAccountId, setSelectedAccountId } = useEmailStore()

  useEffect(() => {
    loadAccounts()
  }, [])

  const loadAccounts = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://172.16.16.148:3015'
      const response = await fetch(`${apiUrl}/api/accounts`)
      const data = await response.json()
      setAccounts(data.accounts || [])

      // Select first account if none selected
      if (!selectedAccountId && data.accounts?.length > 0) {
        setSelectedAccountId(data.accounts[0].id)
      }
    } catch (error) {
      console.error('Failed to load accounts:', error)
    }
  }

  const handleAddAccount = async (accountData) => {
    setLoading(true)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://172.16.16.148:3015'

      // First add the account
      const addResponse = await fetch(`${apiUrl}/api/accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(accountData)
      })

      if (!addResponse.ok) {
        throw new Error('Failed to add account')
      }

      const { account } = await addResponse.json()

      // Then connect to it
      const connectResponse = await fetch(`${apiUrl}/api/accounts/${account.id}/connect`, {
        method: 'POST'
      })

      if (!connectResponse.ok) {
        console.error('Failed to connect to account')
      }

      await loadAccounts()
      setShowAddForm(false)
      setSelectedAccountId(account.id)
    } catch (error) {
      console.error('Failed to add account:', error)
      alert('Failed to add account: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleAccount = async (accountId, active) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://172.16.16.148:3015'
      await fetch(`${apiUrl}/api/accounts/${accountId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active })
      })
      await loadAccounts()
    } catch (error) {
      console.error('Failed to toggle account:', error)
    }
  }

  const handleRemoveAccount = async (accountId) => {
    if (!confirm('Are you sure you want to remove this account?')) {
      return
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://172.16.16.148:3015'
      await fetch(`${apiUrl}/api/accounts/${accountId}`, {
        method: 'DELETE'
      })

      // Select another account if removing the selected one
      if (selectedAccountId === accountId) {
        const remainingAccounts = accounts.filter(a => a.id !== accountId)
        if (remainingAccounts.length > 0) {
          setSelectedAccountId(remainingAccounts[0].id)
        } else {
          setSelectedAccountId(null)
        }
      }

      await loadAccounts()
    } catch (error) {
      console.error('Failed to remove account:', error)
    }
  }

  const handleSelectAccount = (accountId) => {
    setSelectedAccountId(accountId)
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Email Accounts</h2>
        {!showAddForm && (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Account
          </button>
        )}
      </div>

      {showAddForm && (
        <div className="mb-4">
          <AddAccountForm
            onAdd={handleAddAccount}
            onCancel={() => setShowAddForm(false)}
          />
        </div>
      )}

      <div className="space-y-2">
        {accounts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Mail className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p className="text-sm">No email accounts connected</p>
            <p className="text-xs mt-1">Click "Add Account" to get started</p>
          </div>
        ) : (
          accounts.map(account => (
            <AccountItem
              key={account.id}
              account={account}
              isSelected={selectedAccountId === account.id}
              onToggle={handleToggleAccount}
              onRemove={handleRemoveAccount}
              onSelect={handleSelectAccount}
            />
          ))
        )}
      </div>

      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm">Connecting to email account...</p>
          </div>
        </div>
      )}
    </div>
  )
}