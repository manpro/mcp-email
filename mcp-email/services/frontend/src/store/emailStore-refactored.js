import { create } from 'zustand'

const useEmailStore = create((set, get) => ({
  // State
  selectedFolder: 'INBOX',
  searchQuery: '',
  emails: [],
  searchResults: [],
  isSearchActive: false,
  activeFilters: new Set(),
  folders: [],
  selectedEmails: [],
  aiSuggestions: {},
  connectionId: 'user-1',
  isConnected: false,
  selectedAccountId: 'primary', // Default account ID
  accounts: [],

  // API Configuration
  apiBaseUrl: import.meta.env.VITE_EMAIL_API_URL || 'http://172.16.16.148:3012',
  userId: 'default', // This would come from authentication

  // Actions
  setSelectedFolder: (folder) => set({ selectedFolder: folder }),
  setSelectedAccountId: (accountId) => set({ selectedAccountId: accountId }),
  setAccounts: (accounts) => set({ accounts }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setEmails: (emails) => set({ emails }),
  setSearchResults: (results) => set({ searchResults: results, isSearchActive: results.length > 0 }),
  clearSearch: () => set({ searchResults: [], isSearchActive: false, searchQuery: '' }),
  setActiveFilters: (filters) => set({ activeFilters: new Set(filters) }),
  toggleFilter: (filterKey) => set((state) => {
    const newFilters = new Set(state.activeFilters)
    if (newFilters.has(filterKey)) {
      newFilters.delete(filterKey)
    } else {
      newFilters.add(filterKey)
    }
    return { activeFilters: newFilters }
  }),
  clearAllFilters: () => set({ activeFilters: new Set() }),
  setFolders: (folders) => set({ folders }),
  toggleEmailSelection: (emailId) => set((state) => ({
    selectedEmails: state.selectedEmails.includes(emailId)
      ? state.selectedEmails.filter(id => id !== emailId)
      : [...state.selectedEmails, emailId]
  })),
  selectAllEmails: () => set((state) => ({
    selectedEmails: state.emails.map(e => e.uid)
  })),
  clearSelection: () => set({ selectedEmails: [] }),
  setAiSuggestions: (emailId, suggestions) => set((state) => ({
    aiSuggestions: { ...state.aiSuggestions, [emailId]: suggestions }
  })),
  setConnection: (isConnected) => set({ isConnected }),

  // Refactored API Methods using centralized service

  /**
   * Load emails using the new centralized categorization service
   */
  loadEmails: async () => {
    const { selectedAccountId, apiBaseUrl, userId } = get()

    console.log('loadEmails called with:', {
      selectedAccountId,
      apiBaseUrl,
      userId
    })

    if (!selectedAccountId) {
      console.log('No selectedAccountId, setting empty emails')
      set({ emails: [] })
      return
    }

    try {
      const url = `${apiBaseUrl}/recent-emails/${selectedAccountId}?limit=100`
      console.log('Fetching emails from:', url)

      const response = await fetch(url, {
        headers: {
          'x-user-id': userId
        }
      })

      console.log('Response status:', response.status)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const emails = await response.json()

      console.log(`📧 Loaded ${emails.length} emails with centralized categorization`)
      console.log('First email:', emails[0])
      set({ emails })

      return emails
    } catch (error) {
      console.error('Failed to load emails:', error)
      set({ emails: [] })
      throw error
    }
  },

  /**
   * Update email category using the new backend API
   */
  updateEmailCategory: async (emailId, newCategory) => {
    const { apiBaseUrl, userId } = get()

    try {
      // Call backend API to set user override
      const response = await fetch(`${apiBaseUrl}/api/categories/override`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': userId
        },
        body: JSON.stringify({
          emailId,
          category: newCategory,
          userId
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to update category: ${response.statusText}`)
      }

      const result = await response.json()
      console.log(`✅ Category override set:`, result)

      // Update local state immediately for responsive UI
      set((state) => ({
        emails: state.emails.map(email =>
          email.uid === emailId || email.id === emailId
            ? {
                ...email,
                category: newCategory,
                manualCategory: true,
                categorizationSource: 'user_override'
              }
            : email
        )
      }))

      return result

    } catch (error) {
      console.error('Failed to update email category:', error)
      throw error
    }
  },

  /**
   * Get category statistics using centralized service
   */
  getCategoryStats: async () => {
    const { selectedAccountId, apiBaseUrl, userId } = get()

    if (!selectedAccountId) {
      return { categories: {}, priorities: {}, sources: {}, total: 0, unread: 0 }
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/categories/stats/${selectedAccountId}?limit=100`, {
        headers: {
          'x-user-id': userId
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to get stats: ${response.statusText}`)
      }

      const result = await response.json()
      return result.stats

    } catch (error) {
      console.error('Failed to get category stats:', error)
      return { categories: {}, priorities: {}, sources: {}, total: 0, unread: 0 }
    }
  },

  /**
   * Get smart inbox data
   */
  getSmartInbox: async () => {
    const { selectedAccountId, apiBaseUrl, userId } = get()

    if (!selectedAccountId) {
      return { inbox: {}, stats: {} }
    }

    try {
      const response = await fetch(`${apiBaseUrl}/smart-inbox/${selectedAccountId}`, {
        headers: {
          'x-user-id': userId
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to get smart inbox: ${response.statusText}`)
      }

      const result = await response.json()
      return result

    } catch (error) {
      console.error('Failed to get smart inbox:', error)
      return { inbox: {}, stats: {} }
    }
  },

  /**
   * Sync emails
   */
  syncEmails: async () => {
    const { selectedAccountId, apiBaseUrl } = get()

    if (!selectedAccountId) {
      return
    }

    try {
      const response = await fetch(`${apiBaseUrl}/sync-emails/${selectedAccountId}`, {
        method: 'POST'
      })

      if (!response.ok) {
        throw new Error(`Failed to sync: ${response.statusText}`)
      }

      const result = await response.json()
      console.log('📧 Email sync result:', result)

      // Reload emails after sync
      await get().loadEmails()

      return result

    } catch (error) {
      console.error('Failed to sync emails:', error)
      throw error
    }
  },

  // Legacy methods for backwards compatibility - these now use the centralized service

  /**
   * @deprecated Use updateEmailCategory instead
   */
  applyAiAction: async (emailId, action) => {
    console.warn('applyAiAction is deprecated, use updateEmailCategory instead')
    if (action.category) {
      return get().updateEmailCategory(emailId, action.category)
    }
  },

  bulkMove: async (folder) => {
    const { selectedEmails } = get()
    console.log('Moving emails to folder:', folder, selectedEmails)
    // This would be implemented with new bulk API endpoints
  },

  bulkDelete: async () => {
    const { selectedEmails } = get()
    console.log('Deleting emails:', selectedEmails)
    // This would be implemented with new bulk API endpoints
  }
}))

export default useEmailStore