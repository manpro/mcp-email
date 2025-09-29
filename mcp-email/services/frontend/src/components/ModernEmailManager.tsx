import React, { Suspense, useState } from 'react'
import { Mail, Settings, Menu, X, RefreshCw, Activity, Wifi, WifiOff } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import LoadingSpinner from './ui/LoadingSpinner'
import ErrorMessage from './ui/ErrorMessage'
import Sidebar from './Sidebar'
import { useEmailsQuery } from '@/hooks/useEmailQueries'
import { useEmailStore } from '@/store/emailStore'
import { usePolling } from '@/hooks/usePolling'

// Lazy load heavy components for better performance
const EmailList = React.lazy(() => import('./EmailList'))
const EmailDetail = React.lazy(() => import('./EmailDetail'))
const AIPanel = React.lazy(() => import('./AIPanel'))
const AccountManager = React.lazy(() => import('./AccountManager'))
const CategoryFilterStrip = React.lazy(() => import('./CategoryFilterStrip'))

interface ModernEmailManagerProps {
  className?: string
}

export default function ModernEmailManager({ className = '' }: ModernEmailManagerProps) {
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null)
  const [showAIPanel, setShowAIPanel] = useState(true)
  const [showAccountManager, setShowAccountManager] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Store state
  const { selectedFolder, searchQuery } = useEmailStore()

  // Polling integration for updates (no WebSocket)
  const { isConnected, refresh: refreshPolling, triggerSync } = usePolling({
    emailsInterval: 30000,  // Check every 30 seconds
    statsInterval: 120000,  // Update stats every 2 minutes
    enabled: true
  })

  // Fetch emails with React Query
  const {
    data: emails = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching
  } = useEmailsQuery(
    'default', // Use default account
    searchQuery ? { search: searchQuery } : undefined
  )

  const handleRefresh = () => {
    refetch()
    refreshPolling()
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <ErrorMessage
          title="Failed to load emails"
          message={error instanceof Error ? error.message : 'Unknown error occurred'}
          onRetry={handleRefresh}
        />
      </div>
    )
  }

  return (
    <div className={`h-screen bg-gray-50 flex ${className}`}>
      {/* Sidebar - Desktop */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {isMobileMenuOpen ? (
                <X className="w-5 h-5 text-gray-600" />
              ) : (
                <Menu className="w-5 h-5 text-gray-600" />
              )}
            </button>

            <div className="flex items-center space-x-2 lg:hidden">
              <Mail className="w-6 h-6 text-blue-600" />
              <h1 className="text-xl font-semibold text-gray-900">
                Email Manager
              </h1>
            </div>
          </div>

          <div className="flex items-center space-x-2">
          {/* WebSocket Connection Indicator */}
          <div
            className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${
              isConnected
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}
            title={isConnected ? 'Real-time updates active' : 'Real-time updates disconnected'}
          >
            {isConnected ? (
              <Wifi className="w-3 h-3 mr-1" />
            ) : (
              <WifiOff className="w-3 h-3 mr-1" />
            )}
            {isConnected ? 'Live' : 'Offline'}
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            disabled={isFetching}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh emails"
          >
            <RefreshCw className={`w-5 h-5 text-gray-600 ${isFetching ? 'animate-spin' : ''}`} />
          </motion.button>

          <button
            onClick={() => setShowAIPanel(!showAIPanel)}
            className={`p-2 rounded-lg transition-colors ${
              showAIPanel
                ? 'bg-blue-100 text-blue-600'
                : 'hover:bg-gray-100 text-gray-600'
            }`}
            title="Toggle AI Panel"
          >
            <Activity className="w-5 h-5" />
          </button>

          <button
            onClick={() => setShowAccountManager(!showAccountManager)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Account Settings"
          >
            <Settings className="w-5 h-5 text-gray-600" />
          </button>
          </div>
        </header>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Email List */}
        <div className="flex-1 flex flex-col max-w-2xl border-r border-gray-200">
          {/* Compact Category Filter Strip */}
          <Suspense
            fallback={
              <div className="h-16 bg-white border-b border-gray-100 flex items-center px-4">
                <div className="animate-pulse bg-gray-200 h-4 w-64 rounded"></div>
              </div>
            }
          >
            <CategoryFilterStrip emails={emails} />
          </Suspense>

          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <LoadingSpinner size="lg" />
              </div>
            ) : (
              <Suspense
                fallback={
                  <div className="flex items-center justify-center h-full">
                    <LoadingSpinner size="lg" />
                  </div>
                }
              >
                <EmailList
                  emails={emails}
                  selectedEmailId={selectedEmailId}
                  onEmailSelect={setSelectedEmailId}
                />
              </Suspense>
            )}
          </div>
        </div>

        {/* Email Detail */}
        {selectedEmailId && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="flex-1 bg-white border-r border-gray-200"
          >
            <Suspense
              fallback={
                <div className="flex items-center justify-center h-full">
                  <LoadingSpinner size="lg" />
                </div>
              }
            >
              <EmailDetail
                emailId={selectedEmailId}
                onClose={() => setSelectedEmailId(null)}
              />
            </Suspense>
          </motion.div>
        )}

        {/* AI Panel */}
        <AnimatePresence>
          {showAIPanel && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 384 }}
              exit={{ opacity: 0, width: 0 }}
              className="bg-white border-l border-gray-200 overflow-hidden"
            >
              <Suspense
                fallback={
                  <div className="flex items-center justify-center h-full">
                    <LoadingSpinner />
                  </div>
                }
              >
                <AIPanel selectedEmailId={selectedEmailId} />
              </Suspense>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-50"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              className="w-80 h-full bg-white shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Menu</h3>
              </div>

              <Sidebar className="border-0" />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Account Manager Modal */}
      <AnimatePresence>
        {showAccountManager && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setShowAccountManager(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <Suspense
                fallback={
                  <div className="flex items-center justify-center h-64">
                    <LoadingSpinner />
                  </div>
                }
              >
                <AccountManager onClose={() => setShowAccountManager(false)} />
              </Suspense>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}