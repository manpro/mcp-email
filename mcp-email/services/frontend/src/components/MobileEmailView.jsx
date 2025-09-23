import { useState } from 'react'
import {
  Menu, Search, Mail, Filter, Plus, Home, Folder,
  Settings, ChevronLeft, ChevronRight, X, Sparkles
} from 'lucide-react'
import useEmailStore from '../store/emailStore'
import EmailList from './EmailList'
import SmartFilters from './SmartFilters'
import FolderTree from './FolderTree'
import SearchBar from './SearchBar'
import AccountManager from './AccountManager'
import PredictiveActionsPanel from './PredictiveActionsPanel'

export default function MobileEmailView() {
  const [activeView, setActiveView] = useState('inbox')
  const [showSidebar, setShowSidebar] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedEmail, setSelectedEmail] = useState(null)
  const { emails, selectedFolder } = useEmailStore()

  const renderNavBar = () => (
    <div className="fixed top-0 left-0 right-0 z-40 bg-gradient-to-r from-purple-600 to-blue-600 text-white">
      <div className="flex items-center justify-between p-3">
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="p-2 hover:bg-white/20 rounded-lg transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-yellow-300" />
          <span className="font-semibold text-sm">AI Email</span>
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className="p-2 hover:bg-white/20 rounded-lg transition-colors"
        >
          <Filter className="w-5 h-5" />
        </button>
      </div>

      {/* Search Bar */}
      <div className="px-3 pb-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/70" />
          <input
            type="search"
            placeholder="Sök emails..."
            className="w-full pl-10 pr-4 py-2 bg-white/20 backdrop-blur-sm rounded-lg
                     text-white placeholder-white/70 text-sm
                     border border-white/30 focus:border-white/50 focus:outline-none"
          />
        </div>
      </div>
    </div>
  )

  const renderSidebar = () => (
    <div className={`fixed top-0 left-0 bottom-0 w-72 bg-white z-50 transform transition-transform duration-300 ${
      showSidebar ? 'translate-x-0' : '-translate-x-full'
    } shadow-xl`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Konton & Mappar</h2>
          <button
            onClick={() => setShowSidebar(false)}
            className="p-1 hover:bg-gray-100 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="overflow-y-auto max-h-[calc(100vh-80px)]">
        <AccountManager />
        <FolderTree />
      </div>
    </div>
  )

  const renderFilterPanel = () => (
    <div className={`fixed top-0 right-0 bottom-0 w-80 bg-white z-50 transform transition-transform duration-300 ${
      showFilters ? 'translate-x-0' : 'translate-x-full'
    } shadow-xl overflow-y-auto`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Smarta Filter</h2>
          <button
            onClick={() => setShowFilters(false)}
            className="p-1 hover:bg-gray-100 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      <SmartFilters />
    </div>
  )

  const renderEmailDetail = () => {
    if (!selectedEmail) return null

    return (
      <div className="fixed inset-0 bg-white z-30">
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSelectedEmail(null)}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="font-medium">Email Detaljer</span>
            <button className="p-2 hover:bg-gray-100 rounded-lg">
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-4">
          <h2 className="text-lg font-semibold mb-2">{selectedEmail.subject}</h2>
          <p className="text-sm text-gray-600 mb-4">Från: {selectedEmail.from}</p>
          <div className="prose prose-sm max-w-none">
            {selectedEmail.text || selectedEmail.bodyPreview}
          </div>
        </div>

        {/* Predictive Actions for mobile */}
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t border-gray-200">
          <PredictiveActionsPanel email={selectedEmail} />
        </div>
      </div>
    )
  }

  const renderBottomNav = () => (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-30">
      <div className="grid grid-cols-4 py-2">
        <button
          onClick={() => setActiveView('inbox')}
          className={`flex flex-col items-center gap-1 py-2 ${
            activeView === 'inbox' ? 'text-blue-600' : 'text-gray-600'
          }`}
        >
          <Mail className="w-5 h-5" />
          <span className="text-xs">Inbox</span>
        </button>

        <button
          onClick={() => setActiveView('folders')}
          className={`flex flex-col items-center gap-1 py-2 ${
            activeView === 'folders' ? 'text-blue-600' : 'text-gray-600'
          }`}
        >
          <Folder className="w-5 h-5" />
          <span className="text-xs">Mappar</span>
        </button>

        <button
          onClick={() => setActiveView('ai')}
          className={`flex flex-col items-center gap-1 py-2 ${
            activeView === 'ai' ? 'text-blue-600' : 'text-gray-600'
          }`}
        >
          <Sparkles className="w-5 h-5" />
          <span className="text-xs">AI</span>
        </button>

        <button
          onClick={() => setActiveView('settings')}
          className={`flex flex-col items-center gap-1 py-2 ${
            activeView === 'settings' ? 'text-blue-600' : 'text-gray-600'
          }`}
        >
          <Settings className="w-5 h-5" />
          <span className="text-xs">Inställningar</span>
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {renderNavBar()}
      {renderSidebar()}
      {renderFilterPanel()}

      {/* Main Content Area */}
      <div className="pt-24 pb-16">
        {selectedEmail ? (
          renderEmailDetail()
        ) : (
          <EmailList aiMode={true} />
        )}
      </div>

      {renderBottomNav()}

      {/* Overlay for sidebar/filter */}
      {(showSidebar || showFilters) && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => {
            setShowSidebar(false)
            setShowFilters(false)
          }}
        />
      )}
    </div>
  )
}