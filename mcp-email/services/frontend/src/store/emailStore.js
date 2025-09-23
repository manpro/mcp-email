import { create } from 'zustand'

const useEmailStore = create((set, get) => ({
  // State
  selectedFolder: 'INBOX',
  searchQuery: '',
  emails: [],
  searchResults: [], // Search results displayed above inbox
  isSearchActive: false, // Whether search results are shown
  activeFilters: new Set(), // Active smart filters
  folders: [],
  selectedEmails: [],
  aiSuggestions: {},
  connectionId: 'user-1', // Must match userId used in connect
  isConnected: false,
  selectedAccountId: null, // Currently selected account
  accounts: [], // All accounts

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

  // AI Actions
  applyAiAction: async (emailId, action) => {
    // This will be implemented to call backend
    console.log('Applying AI action:', action, 'to email:', emailId)
  },

  // Bulk Actions
  bulkMove: async (folder) => {
    const { selectedEmails } = get()
    console.log('Moving emails to folder:', folder, selectedEmails)
    // Call backend API
  },

  bulkDelete: async () => {
    const { selectedEmails } = get()
    console.log('Deleting emails:', selectedEmails)
    // Call backend API
  },

  // Update email category and save to localStorage
  updateEmailCategory: (emailId, newCategory) => set((state) => {
    // Save manual category override to localStorage
    const manualCategories = JSON.parse(localStorage.getItem('manualEmailCategories') || '{}')
    manualCategories[emailId] = {
      category: newCategory,
      timestamp: Date.now()
    }
    localStorage.setItem('manualEmailCategories', JSON.stringify(manualCategories))

    const updatedEmails = state.emails.map(email =>
      email.uid === emailId || email.id === emailId
        ? { ...email, category: newCategory, manualCategory: true }
        : email
    )
    return { emails: updatedEmails }
  }),

  // Apply manual category overrides when emails are loaded
  setEmails: (emails) => set((state) => {
    const manualCategories = JSON.parse(localStorage.getItem('manualEmailCategories') || '{}')

    console.log('📧 Loading emails with manual categories:', {
      totalEmails: emails.length,
      manualCategoriesCount: Object.keys(manualCategories).length,
      manualCategories: Object.keys(manualCategories)
    })

    let overrideCount = 0
    const emailsWithOverrides = emails.map(email => {
      const emailId = email.uid || email.id
      if (manualCategories[emailId]) {
        overrideCount++
        console.log(`🔄 Applying manual category to email ${emailId}:`, {
          original: email.category,
          manual: manualCategories[emailId].category
        })
        return {
          ...email,
          category: manualCategories[emailId].category,
          manualCategory: true,
          originalCategory: email.category // Keep track of original ML category
        }
      }
      return email
    })

    console.log(`✅ Applied ${overrideCount} manual category overrides`)
    return { emails: emailsWithOverrides }
  })
}))

export default useEmailStore