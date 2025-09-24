import { useState, useRef, useEffect } from 'react'
import {
  FileText, User, Calendar, Bot, Users, Ban,
  Mail, ShoppingCart, Shield, Briefcase, Folder,
  Building2, Calculator, ChartBar, ClipboardList,
  Coffee, Computer, DollarSign, Handshake,
  MessageSquare, Phone, Video, Zap, Wifi,
  Heart, Globe, Rss, Share2, UserPlus,
  Archive, Book, BookOpen, Database, File, FileImage,
  FolderOpen, HardDrive, Paperclip, Save, Upload,
  ShoppingBag, CreditCard, Gift, Package,
  Truck, Store, Tag, TrendingUp, Coins,
  Lock, Key, Eye, EyeOff, AlertTriangle,
  CheckCircle, XCircle, Info, AlertCircle,
  Camera, Music, Play, Headphones, Film, Image,
  Gamepad2, Tv, Radio, Disc,
  Settings, Cog, Wrench, Hammer, Clock, Timer, Bell, AlarmClock,
  Car, Plane, Train, MapPin, Map, Compass,
  Home, Building, Flag, Route
} from 'lucide-react'
import learningService from '../services/learningService'
import CategoryMenu from './CategoryMenu'
import customCategoriesCache from '../services/customCategoriesCache'

// Removed - now handled by customCategoriesCache

const defaultCategories = [
  { id: 'newsletter', label: 'Nyhetsbrev', icon: Mail, color: 'bg-blue-100 text-blue-700', priority: 1 },
  { id: 'work', label: 'Arbete', icon: Briefcase, color: 'bg-purple-100 text-purple-700', priority: 2 },
  { id: 'personal', label: 'Personligt', icon: User, color: 'bg-green-100 text-green-700', priority: 3 },
  { id: 'invoice', label: 'Faktura', icon: FileText, color: 'bg-yellow-100 text-yellow-700', priority: 4 },
  { id: 'security', label: 'Säkerhet', icon: Shield, color: 'bg-red-100 text-red-700', priority: 5 },
  { id: 'meetings', label: 'Möten', icon: Calendar, color: 'bg-indigo-100 text-indigo-700', priority: 6 },
  { id: 'automated', label: 'Automatiskt', icon: Bot, color: 'bg-gray-100 text-gray-700', priority: 7 },
  { id: 'social', label: 'Socialt', icon: Users, color: 'bg-pink-100 text-pink-700', priority: 8 },
  { id: 'spam', label: 'Spam', icon: Ban, color: 'bg-gray-100 text-gray-700', priority: 9 },
  { id: 'other', label: 'Övrigt', icon: Folder, color: 'bg-gray-100 text-gray-700', priority: 10 }
]

export default function MinimalCategorySelector({ email, currentCategory, onCategoryChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const [customCategories, setCustomCategories] = useState([])
  const dropdownRef = useRef(null)

  useEffect(() => {
    // Get custom categories from cache
    const cachedCategories = customCategoriesCache.getCategories()
    setCustomCategories(cachedCategories)

    // Subscribe to cache updates
    const unsubscribe = customCategoriesCache.subscribe((categories) => {
      setCustomCategories(categories || [])
    })

    // Load categories if not already loaded
    customCategoriesCache.loadCustomCategories()

    return unsubscribe
  }, [])

  const allCategories = [...defaultCategories, ...customCategories.map((cat, idx) => ({
    ...cat,
    priority: 100 + idx
  }))]

  const current = allCategories.find(c => c.id === currentCategory) || defaultCategories[9]

  const handleCategorySelect = (categoryId) => {
    learningService.trackAction('categorize', email, {
      oldCategory: currentCategory,
      newCategory: categoryId,
      userCorrection: true
    })

    onCategoryChange(categoryId)
    setIsOpen(false)
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="group relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`w-8 h-6 rounded flex items-center justify-center text-xs transition-all hover:scale-105 focus:outline-none focus:ring-1 focus:ring-offset-1 ${current.color}`}
          title={current.label}
        >
          {current.icon && typeof current.icon === 'function' ? (
            <current.icon className="w-3 h-3" />
          ) : (
            <Mail className="w-3 h-3" />
          )}
        </button>

        {/* Tooltip */}
        <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 text-xs text-white bg-gray-900 rounded whitespace-nowrap z-50">
          {current.label}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-2 border-transparent border-t-gray-900"></div>
        </div>
      </div>

      {isOpen && (
        <CategoryMenu
          categories={allCategories}
          onSelect={handleCategorySelect}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}