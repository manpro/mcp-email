import { io, Socket } from 'socket.io-client'
import type {
  Email,
  EmailFilters,
  MLFeedback,
  EmailAccount,
  EmailCredentials,
  CustomCategory,
  EmailFolder,
  APIResponse,
  MLAnalysis
} from '@/types'

// API Base Configuration - Updated for 6-component architecture
const API_BASE_URL = import.meta.env.VITE_API_URL || ''
// No WebSocket URL needed in the new architecture

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'APIError'
  }
}

// Email data transformation utility
interface RawEmail {
  uid?: string
  id?: string
  from_address?: string
  received_at?: string
  html_content?: string
  text_content?: string
  subject?: string
  flags?: any
  label?: string
  [key: string]: any
}

const transformEmailData = (rawEmails: RawEmail[]): Email[] => {
  if (!Array.isArray(rawEmails)) {
    console.warn('Expected array of emails, got:', typeof rawEmails)
    return []
  }

  return rawEmails.map(email => ({
    // Keep original fields
    ...email,
    // Map API fields to frontend expected fields
    from: email.from_address || email.from || 'Unknown',
    date: email.received_at || email.date || new Date().toISOString(),
    content: email.html_content || email.text_content || email.content || '',
    // Map content fields for EmailItem.jsx preview
    text: email.text_content || email.text || '',
    html: email.html_content || email.html || '',
    // Ensure required fields exist
    uid: email.uid || email.id,
    subject: email.subject || 'No Subject',
    seen: email.flags?.includes?.('\\Seen') || false,
    flagged: email.flags?.includes?.('\\Flagged') || false,
    category: email.label || email.category || 'inbox'
  })) as Email[]
}

// Core Email API Service
export class EmailAPIService {
  private baseURL: string
  private wsConnection: Socket | null = null

  constructor() {
    this.baseURL = API_BASE_URL
    this.initWebSocket()
  }

  // WebSocket Connection för Real-time Updates
  private initWebSocket() {
    try {
      // Build WebSocket URL from API URL
      const wsUrl = this.baseURL.replace(/^http/, 'ws')

      this.wsConnection = io(wsUrl, {
        transports: ['websocket'],
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: 5
      })

      this.wsConnection.on('connect', () => {
        console.log('✅ WebSocket connected')
      })

      this.wsConnection.on('disconnect', () => {
        console.log('📡 WebSocket disconnected')
      })

      this.wsConnection.on('error', (error) => {
        console.error('❌ WebSocket error:', error)
      })
    } catch (error) {
      console.warn('⚠️ WebSocket initialization failed:', error)
    }
  }

  // Subscribe to real-time email updates
  onEmailUpdate(callback: (email: Email) => void) {
    this.wsConnection?.on('email-updated', callback)
  }

  onEmailNew(callback: (email: Email) => void) {
    this.wsConnection?.on('email-new', callback)
  }

  onSyncComplete(callback: (data: any) => void) {
    this.wsConnection?.on('sync-complete', callback)
  }

  // Generic API request helper
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      })

      if (!response.ok) {
        throw new APIError(response.status, `HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof APIError) {
        throw error
      }
      throw new APIError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  // Email Management Methods
  async getEmails(accountId?: string, filters?: EmailFilters): Promise<Email[]> {
    const params = new URLSearchParams()
    if (accountId) params.set('accountId', accountId)
    if (filters?.category) params.set('category', filters.category)
    if (filters?.priority) params.set('priority', filters.priority)
    if (filters?.search) params.set('search', filters.search)
    if (filters?.isRead !== undefined) params.set('isRead', filters.isRead.toString())

    // Set high limit to get ALL emails
    params.set('limit', '1000')

    const queryString = params.toString() ? `?${params.toString()}` : ''

    // Get raw response which contains {emails: [], pagination: {}}
    const response = await this.request<{emails: RawEmail[], pagination: any}>(`/api/emails${queryString}`)

    // Extract emails array and transform to frontend format
    const rawEmails = response.emails || []
    return transformEmailData(rawEmails)
  }

  async getEmailAnalysis(uid: string): Promise<MLAnalysis> {
    return this.request<MLAnalysis>(`/api/emails/${uid}/analysis`)
  }

  // ML & AI Integration
  async submitMLFeedback(emailId: string, feedback: MLFeedback): Promise<void> {
    await this.request('/api/ml/feedback', {
      method: 'POST',
      body: JSON.stringify({ emailId, ...feedback })
    })
  }

  async overrideCategory(emailId: string, category: string): Promise<void> {
    await this.request('/api/categories/override', {
      method: 'POST',
      body: JSON.stringify({ emailId, category })
    })
  }

  async getCategoryStats(accountId: string): Promise<any> {
    return this.request(`/api/categories/stats/${accountId}`)
  }

  // Inbox Zero Integration
  async getInboxZeroStats(accountId: string): Promise<any> {
    return this.request(`/api/inbox-zero/stats/${accountId}`)
  }

  async getInboxZeroAchievements(accountId: string): Promise<any> {
    return this.request(`/api/inbox-zero/achievements/${accountId}`)
  }

  async getWeeklyProgress(accountId: string): Promise<any> {
    return this.request(`/api/inbox-zero/weekly-progress/${accountId}`)
  }

  // Cache Management
  async clearCache(): Promise<void> {
    await this.request('/api/cache/clear', { method: 'POST' })
  }

  async getCacheStats(): Promise<any> {
    return this.request('/api/cache/stats')
  }
}

// Account Management API Service
export class AccountAPIService {
  private baseURL = API_BASE_URL

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      throw new APIError(response.status, `HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  }

  async getAccounts(): Promise<EmailAccount[]> {
    return this.request<EmailAccount[]>('/api/accounts')
  }

  async connectAccount(credentials: EmailCredentials): Promise<APIResponse<any>> {
    return this.request<APIResponse<any>>('/api/accounts', {
      method: 'POST',
      body: JSON.stringify(credentials)
    })
  }

  async syncEmails(accountId: string): Promise<void> {
    await this.request(`/sync-emails/${accountId}`, {
      method: 'POST'
    })
  }

  async toggleAccount(accountId: string): Promise<void> {
    await this.request(`/api/accounts/${accountId}/toggle`, {
      method: 'POST'
    })
  }

  async deleteAccount(accountId: string): Promise<void> {
    await this.request(`/api/accounts/${accountId}`, {
      method: 'DELETE'
    })
  }

  async getMailboxes(accountId: string): Promise<any[]> {
    return this.request<any[]>(`/api/accounts/${accountId}/mailboxes`)
  }
}

// Custom Categories API Service
export class CustomCategoriesAPIService {
  private baseURL = API_BASE_URL

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      throw new APIError(response.status, `HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  }

  async getCustomCategories(userId: string): Promise<CustomCategory[]> {
    return this.request<CustomCategory[]>(`/api/custom-categories/${userId}`)
  }

  async createCustomCategory(userId: string, category: Omit<CustomCategory, 'id'>): Promise<APIResponse<any>> {
    return this.request<APIResponse<any>>(`/api/custom-categories/${userId}`, {
      method: 'POST',
      body: JSON.stringify(category)
    })
  }

  async deleteCustomCategory(userId: string, categoryId: string): Promise<void> {
    await this.request(`/api/custom-categories/${userId}/${categoryId}`, {
      method: 'DELETE'
    })
  }
}

// Folder Management API Service
export class FolderAPIService {
  private baseURL = API_BASE_URL

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      throw new APIError(response.status, `HTTP ${response.status}: ${response.statusText}`)
    }

    return await response.json()
  }

  async getFolders(): Promise<EmailFolder[]> {
    return this.request<EmailFolder[]>('/api/folders')
  }

  async createFolder(folder: Omit<EmailFolder, 'id' | 'emailCount'>): Promise<void> {
    await this.request('/api/folders', {
      method: 'POST',
      body: JSON.stringify(folder)
    })
  }

  async moveEmailToFolder(emailId: string, folderId: string): Promise<void> {
    await this.request('/api/folders/move', {
      method: 'POST',
      body: JSON.stringify({ emailId, folderId })
    })
  }

  async getFolderSuggestions(accountId?: string): Promise<any[]> {
    const endpoint = accountId
      ? `/api/folders/suggestions/${accountId}`
      : '/api/folders/suggestions'
    return this.request<any[]>(endpoint)
  }
}

// Export singleton instances
export const emailAPI = new EmailAPIService()
export const accountAPI = new AccountAPIService()
export const categoriesAPI = new CustomCategoriesAPIService()
export const folderAPI = new FolderAPIService()

// Export error types
export { APIError }