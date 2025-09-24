/**
 * Global cache for custom categories to prevent multiple API calls
 */

import axiosInstance from '../lib/axiosInstance.js'
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

// Icon resolver function to get React component from icon name
const getIconComponent = (iconName) => {
  const iconMap = {
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
  }
  return iconMap[iconName] || null
}

class CustomCategoriesCache {
  constructor() {
    this.cache = null
    this.loading = false
    this.loadPromise = null
    this.listeners = new Set()
  }

  // Subscribe to cache updates
  subscribe(callback) {
    this.listeners.add(callback)
    return () => this.listeners.delete(callback)
  }

  // Notify all listeners
  notify() {
    this.listeners.forEach(callback => callback(this.cache))
  }

  // Load custom categories (only once)
  async loadCustomCategories() {
    // If already cached, return immediately
    if (this.cache !== null) {
      return this.cache
    }

    // If already loading, return the existing promise
    if (this.loading && this.loadPromise) {
      return this.loadPromise
    }

    this.loading = true

    this.loadPromise = this._fetchCustomCategories()

    try {
      const categories = await this.loadPromise
      this.cache = categories
      this.loading = false
      this.notify()
      return categories
    } catch (error) {
      this.loading = false
      this.loadPromise = null
      throw error
    }
  }

  async _fetchCustomCategories() {
    try {
      console.log('🔥 [CACHE] Loading custom categories from API...')
      const response = await axiosInstance.get('/api/custom-categories/default')

      if (response.status === 200) {
        const categories = response.data
        // Convert icon names back to icon components
        const categoriesWithIcons = categories.map(category => ({
          ...category,
          icon: getIconComponent(category.icon) || Mail // fallback to Mail icon
        }))

        console.log(`✅ [CACHE] Loaded ${categoriesWithIcons.length} custom categories`)
        return categoriesWithIcons
      }

      return []
    } catch (error) {
      console.error('❌ [CACHE] Failed to load custom categories:', error)
      return [] // Return empty array on error instead of throwing
    }
  }

  // Get cached categories or load if not cached
  getCategories() {
    if (this.cache !== null) {
      return this.cache
    }

    // Start loading if not already
    if (!this.loading) {
      this.loadCustomCategories()
    }

    return [] // Return empty array while loading
  }

  // Clear cache (useful for testing or when categories change)
  clearCache() {
    this.cache = null
    this.loading = false
    this.loadPromise = null
  }
}

// Export singleton instance
const customCategoriesCache = new CustomCategoriesCache()
export default customCategoriesCache