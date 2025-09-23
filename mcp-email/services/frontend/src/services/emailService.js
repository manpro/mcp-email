/**
 * Email Service - Uses centralized Axios instance
 *
 * This service handles all email-related API calls.
 * It now uses the centralized axios instance instead of direct axios calls,
 * which ensures proper URL configuration and error handling.
 */

import axiosInstance from '../lib/axiosInstance'

// No need for API_BASE anymore - it's configured in axiosInstance
// The axios instance already has the base URL configured from VITE_API_URL

export const fetchMailboxes = async (connectionId) => {
  try {
    // Direct to email-service API
    const response = await axiosInstance.get(`/api/mailboxes?userId=user-1`)

    // Handle authentication error
    if (response.data.requiresAuth) {
      throw new Error(response.data.error || 'Authentication required')
    }

    // Transform the flat mailbox list into a hierarchical structure
    const folders = {}
    const mailboxes = response.data.mailboxes || []

    mailboxes.forEach(mailbox => {
      const parts = (mailbox.path || mailbox.name || '').split('.')
      let current = folders

      parts.forEach((part, index) => {
        const path = parts.slice(0, index + 1).join('.')

        if (!current[part]) {
          current[part] = {
            name: part,
            path: path,
            displayName: mailbox.name || part,
            children: {},
            unread: mailbox.unread || 0,
            count: mailbox.count || 0
          }
        }

        if (index < parts.length - 1) {
          current = current[part].children
        }
      })
    })

    return folders
  } catch (error) {
    console.error('Failed to fetch mailboxes:', error)
    throw error
  }
}

export const fetchEmails = async (connectionId, mailbox = 'INBOX', count = 50) => {
  try {
    // Direct to email-service API
    const response = await axiosInstance.get(`/api/recent-emails?userId=user-1&mailbox=${mailbox}&limit=${count}`)

    // Handle authentication error
    if (response.data.requiresAuth) {
      throw new Error(response.data.error || 'Authentication required')
    }

    return response.data.emails || []
  } catch (error) {
    console.error('Failed to fetch emails:', error)
    throw error
  }
}

export const searchEmails = async (connectionId, criteria, mailbox = 'INBOX', limit = 20) => {
  try {
    // Using axiosInstance with relative path
    const response = await axiosInstance.post('/api/search-emails', {
      connectionId,
      criteria,
      mailbox,
      limit
    })

    return response.data.emails || []
  } catch (error) {
    console.error('Failed to search emails:', error)
    throw error
  }
}

export const moveEmails = async (connectionId, emailUids, targetFolder) => {
  // This would be implemented when the backend supports it
  console.log('Moving emails:', emailUids, 'to', targetFolder)
  return true
}

export const deleteEmails = async (connectionId, emailUids) => {
  try {
    // Using axiosInstance with relative path
    const response = await axiosInstance.post('/api/delete-emails', {
      connectionId,
      emailUids
    })

    return response.data.success
  } catch (error) {
    console.error('Failed to delete emails:', error)
    throw error
  }
}

export const connectEmail = async (email, password, provider = 'auto', testMode = false) => {
  try {
    // Direct to email-service API
    const response = await axiosInstance.post('/connect', {
      userId: 'user-1',
      email,
      password,
      provider
    }, {
      timeout: 15000 // 15 second timeout for connection
    })

    return response.data.success
  } catch (error) {
    console.error('Failed to connect email:', error)
    throw error
  }
}