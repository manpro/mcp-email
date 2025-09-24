import { useState, useEffect } from 'react'
import { Menu, X, Mail, Search, Filter, RefreshCw, ChevronRight, Clock, Star, AlertCircle } from 'lucide-react'
import useEmailStore from '../store/emailStore-refactored'
import AccountManager from './AccountManager'

function EmailItem({ email, onClick }) {
  const categoryColors = {
    work: 'bg-blue-100 text-blue-800',
    personal: 'bg-green-100 text-green-800',
    newsletter: 'bg-purple-100 text-purple-800',
    spam: 'bg-red-100 text-red-800',
    notification: 'bg-yellow-100 text-yellow-800',
    social: 'bg-pink-100 text-pink-800',
    billing: 'bg-orange-100 text-orange-800',
    support: 'bg-indigo-100 text-indigo-800',
    marketing: 'bg-gray-100 text-gray-800',
    travel: 'bg-teal-100 text-teal-800',
    education: 'bg-cyan-100 text-cyan-800',
    health: 'bg-lime-100 text-lime-800'
  }

  const priorityIcons = {
    high: <AlertCircle className="w-4 h-4 text-red-500" />,
    medium: <Clock className="w-4 h-4 text-yellow-500" />,
    low: null
  }

  return (
    <div
      onClick={onClick}
      className="bg-white border-b hover:bg-gray-50 cursor-pointer transition-colors p-4"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-medium text-gray-900 text-sm line-clamp-1 flex-1">
          {email.from || 'Unknown Sender'}
        </h3>
        <div className="flex items-center gap-2 ml-2">
          {priorityIcons[email.priority]}
          <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[email.category] || categoryColors.notification}`}>
            {email.category}
          </span>
        </div>
      </div>

      <p className="text-sm text-gray-700 font-medium mb-1 line-clamp-1">
        {email.subject || 'No Subject'}
      </p>

      <p className="text-xs text-gray-500 line-clamp-2">
        {email.summary || email.bodyPreview || 'No preview available'}
      </p>

      <div className="flex justify-between items-center mt-2">
        <span className="text-xs text-gray-400">
          {new Date(email.date).toLocaleDateString()}
        </span>
        {email.actionRequired && (
          <span className="text-xs text-red-600 font-medium">Action Required</span>
        )}
      </div>
    </div>
  )
}

export default function MobileEmailManager() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [activeTab, setActiveTab] = useState('inbox')
  const {
    emails,
    loadEmails,
    syncEmails,
    selectedAccountId,
    searchQuery,
    setSearchQuery
  } = useEmailStore()

  const [isLoading, setIsLoading] = useState(false)
  const [filteredEmails, setFilteredEmails] = useState([])

  useEffect(() => {
    console.log('MobileEmailManager: selectedAccountId:', selectedAccountId)
    if (selectedAccountId) {
      console.log('Loading emails for account:', selectedAccountId)
      loadEmails().then(() => {
        console.log('Emails loaded, count:', emails.length)
      }).catch(err => {
        console.error('Failed to load emails:', err)
      })
    }
  }, [selectedAccountId])

  useEffect(() => {
    // Filter emails based on search and active tab
    console.log('Filtering emails, total count:', emails?.length || 0)
    let filtered = emails || []

    if (searchQuery) {
      filtered = filtered.filter(email =>
        email.subject?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        email.from?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        email.summary?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    // Filter by tab
    switch (activeTab) {
      case 'priority':
        filtered = filtered.filter(e => e.priority === 'high')
        break
      case 'action':
        filtered = filtered.filter(e => e.actionRequired)
        break
      case 'work':
        filtered = filtered.filter(e => e.category === 'work')
        break
      case 'personal':
        filtered = filtered.filter(e => e.category === 'personal')
        break
    }

    setFilteredEmails(filtered)
  }, [emails, searchQuery, activeTab])

  const handleSync = async () => {
    setIsLoading(true)
    try {
      await syncEmails()
    } finally {
      setIsLoading(false)
    }
  }

  const tabs = [
    { id: 'inbox', label: 'All', count: emails.length },
    { id: 'priority', label: 'Priority', count: emails.filter(e => e.priority === 'high').length },
    { id: 'action', label: 'Action', count: emails.filter(e => e.actionRequired).length },
    { id: 'work', label: 'Work', count: emails.filter(e => e.category === 'work').length },
    { id: 'personal', label: 'Personal', count: emails.filter(e => e.category === 'personal').length }
  ]

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Mobile Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center justify-between lg:hidden">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <Menu className="w-5 h-5" />
        </button>

        <h1 className="font-semibold text-lg">Email</h1>

        <button
          onClick={handleSync}
          className={`p-2 hover:bg-gray-100 rounded-lg ${isLoading ? 'animate-spin' : ''}`}
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Mobile Overlay */}
        <div className={`
          fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity
          ${sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}
        `} onClick={() => setSidebarOpen(false)} />

        {/* Sidebar Content */}
        <aside className={`
          fixed lg:relative inset-y-0 left-0 z-50
          w-72 bg-white border-r transform transition-transform
          lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <div className="flex flex-col h-full">
            <div className="p-4 border-b flex justify-between items-center lg:hidden">
              <h2 className="font-semibold">Menu</h2>
              <button onClick={() => setSidebarOpen(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Desktop Header */}
            <div className="hidden lg:block p-4 border-b">
              <h1 className="text-xl font-bold">Email Manager</h1>
            </div>

            <div className="flex-1 overflow-y-auto">
              <AccountManager />
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Search Bar */}
          <div className="p-4 bg-white border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search emails..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Tabs - Horizontal Scrollable on Mobile */}
          <div className="bg-white border-b overflow-x-auto">
            <div className="flex min-w-max">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    px-4 py-3 text-sm font-medium whitespace-nowrap
                    border-b-2 transition-colors
                    ${activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'}
                  `}
                >
                  {tab.label}
                  {tab.count > 0 && (
                    <span className="ml-2 px-2 py-0.5 text-xs bg-gray-100 rounded-full">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Email List - Split View on Desktop */}
          <div className="flex-1 flex overflow-hidden">
            <div className={`
              ${selectedEmail ? 'hidden md:block' : 'block'}
              w-full md:w-2/5 lg:w-1/3 overflow-y-auto bg-gray-50
            `}>
              {filteredEmails.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Mail className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p>No emails found</p>
                </div>
              ) : (
                filteredEmails.map(email => (
                  <EmailItem
                    key={email.uid || email.id}
                    email={email}
                    onClick={() => setSelectedEmail(email)}
                  />
                ))
              )}
            </div>

            {/* Email Detail - Full Screen on Mobile */}
            {selectedEmail && (
              <div className={`
                ${selectedEmail ? 'block' : 'hidden md:block'}
                flex-1 bg-white overflow-y-auto
              `}>
                <div className="p-4 md:p-6">
                  <button
                    onClick={() => setSelectedEmail(null)}
                    className="md:hidden mb-4 text-blue-600 hover:text-blue-700 flex items-center gap-1"
                  >
                    <ChevronRight className="w-4 h-4 rotate-180" />
                    Back to list
                  </button>

                  <h2 className="text-xl font-bold mb-2">{selectedEmail.subject}</h2>
                  <div className="text-sm text-gray-600 mb-4">
                    <p>From: {selectedEmail.from}</p>
                    <p>Date: {new Date(selectedEmail.date).toLocaleString()}</p>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-4">
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                      {selectedEmail.category}
                    </span>
                    <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">
                      {selectedEmail.priority} priority
                    </span>
                    {selectedEmail.sentiment && (
                      <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                        {selectedEmail.sentiment}
                      </span>
                    )}
                  </div>

                  <div className="prose max-w-none">
                    <h3 className="font-semibold mb-2">Summary</h3>
                    <p className="text-gray-700">{selectedEmail.summary}</p>

                    <h3 className="font-semibold mt-4 mb-2">Preview</h3>
                    <p className="text-gray-700 whitespace-pre-wrap">
                      {selectedEmail.bodyPreview || 'No content available'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}