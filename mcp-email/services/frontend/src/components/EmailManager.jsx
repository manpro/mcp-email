import { useState, useEffect } from 'react'
import { Search, Mail, Trash2, Archive, FolderOpen, Sparkles, Filter, Menu, X } from 'lucide-react'
import FolderTree from './FolderTree'
import EmailList from './EmailList'
import AIPanel from './AIPanel'
import SearchBar from './SearchBar'
import SearchResults from './SearchResults'
import SmartFiltersCompact from './SmartFilters-compact'
import ConnectEmail from './ConnectEmail'
import AccountManager from './AccountManager'
import useEmailStore from '../store/emailStore-refactored'

export default function EmailManager({ isTablet = false }) {
  const { selectedFolder, searchQuery } = useEmailStore()
  const [aiMode, setAiMode] = useState(true)
  const [showSidebar, setShowSidebar] = useState(!isTablet)
  const [showAiPanel, setShowAiPanel] = useState(!isTablet)

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar - Folders */}
      <div className={`${showSidebar ? 'w-64' : 'w-0'} transition-all duration-300 bg-white border-r border-gray-200 flex flex-col overflow-hidden ${isTablet ? 'absolute left-0 top-0 bottom-0 z-20' : ''}`}>
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-500" />
            AI Email Manager
          </h1>
        </div>

        <AccountManager />

        <SearchBar />

        <div className="p-4">
          <button
            onClick={() => setAiMode(!aiMode)}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-all ${
              aiMode
                ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {aiMode ? 'AI Mode Active' : 'Enable AI Mode'}
          </button>
        </div>

        <FolderTree />
      </div>

      {/* Middle - Email List */}
      <div className="flex-1 flex flex-col max-w-3xl border-r border-gray-200">
        <div className="p-4 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {selectedFolder || 'Inbox'}
            </h2>
            <div className="flex items-center gap-2">
              <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <Filter className="w-4 h-4 text-gray-600" />
              </button>
              <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <Archive className="w-4 h-4 text-gray-600" />
              </button>
              <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <Trash2 className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>
        </div>

        <SearchResults />
        <SmartFiltersCompact />
        <EmailList aiMode={aiMode} />
      </div>

      {/* Right Panel - AI Actions */}
      {aiMode && (
        <div className={`${showAiPanel ? 'w-96' : 'w-0'} transition-all duration-300 bg-white overflow-hidden ${isTablet ? 'absolute right-0 top-0 bottom-0 z-20' : ''}`}>
          <AIPanel />
        </div>
      )}
    </div>
  )
}