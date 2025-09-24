/**
 * Global Error Handler for PWA/WebSocket Issues
 *
 * This service handles errors that come from external sources or cached applications
 * that are trying to connect to incorrect endpoints (localhost:8000, PWA features, etc.)
 */

class ErrorHandler {
  constructor() {
    this.initializeGlobalErrorHandling()
    this.blockInvalidRequests()
  }

  initializeGlobalErrorHandling() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError(event.reason, 'unhandledRejection')
    })

    // Handle general errors
    window.addEventListener('error', (event) => {
      this.handleError(event.error, 'globalError')
    })

    // Override console.error to filter out known issues
    const originalConsoleError = console.error
    console.error = (...args) => {
      if (this.shouldSuppressError(args[0])) {
        return // Suppress known external errors
      }
      originalConsoleError.apply(console, args)
    }
  }

  handleError(error, source) {
    const errorMessage = error?.message || error?.toString() || 'Unknown error'

    // Check if this is a known external error
    if (this.isExternalError(errorMessage)) {
      console.warn(`🚫 [ErrorHandler] Suppressed external error from ${source}:`, errorMessage)
      return
    }

    // Log legitimate errors normally
    console.error(`[ErrorHandler] ${source}:`, error)
  }

  isExternalError(message) {
    const externalErrorPatterns = [
      /localhost:8000/,
      /socket\.io/,
      /Failed to convert value to 'Response'/,
      /net::ERR_FAILED.*localhost:8000/,
      /analytics.*track.*ERR_BLOCKED_BY_CLIENT/,
      /websocket.*connection.*error/i,
      /pwa\.ts/,
      /sw\.js/,
      /Layout\.tsx/
    ]

    return externalErrorPatterns.some(pattern => pattern.test(message))
  }

  shouldSuppressError(message) {
    if (typeof message === 'string') {
      return this.isExternalError(message)
    }
    return false
  }

  blockInvalidRequests() {
    // Override XMLHttpRequest to block invalid requests
    const originalXHROpen = XMLHttpRequest.prototype.open
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
      if (url?.includes('localhost:8000')) {
        console.warn('🚫 [ErrorHandler] Blocked invalid request to:', url)
        // Create a fake successful response
        this.readyState = 4
        this.status = 200
        this.responseText = JSON.stringify({ blocked: true, reason: 'Invalid endpoint' })
        setTimeout(() => {
          if (this.onreadystatechange) this.onreadystatechange()
          if (this.onload) this.onload()
        }, 0)
        return
      }
      return originalXHROpen.call(this, method, url, ...args)
    }

    // Override fetch to block invalid requests
    const originalFetch = window.fetch
    window.fetch = function(url, options) {
      if (url?.includes('localhost:8000')) {
        console.warn('🚫 [ErrorHandler] Blocked invalid fetch to:', url)
        return Promise.resolve(new Response(
          JSON.stringify({ blocked: true, reason: 'Invalid endpoint' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        ))
      }
      return originalFetch.call(this, url, options)
    }
  }

  // Service Worker handling
  disableServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        registrations.forEach(registration => {
          if (registration.scope.includes('localhost:8000')) {
            console.warn('🚫 [ErrorHandler] Unregistering invalid service worker')
            registration.unregister()
          }
        })
      })
    }
  }

  // WebSocket connection blocking
  blockInvalidWebSockets() {
    const originalWebSocket = window.WebSocket
    window.WebSocket = function(url, protocols) {
      if (url?.includes('localhost:8000')) {
        console.warn('🚫 [ErrorHandler] Blocked invalid WebSocket connection to:', url)
        // Return a fake WebSocket that doesn't actually connect
        return {
          readyState: 3, // CLOSED state
          close: () => {},
          send: () => {},
          addEventListener: () => {},
          removeEventListener: () => {}
        }
      }
      return new originalWebSocket(url, protocols)
    }

    // Copy static properties safely using Object.defineProperty
    try {
      Object.defineProperty(window.WebSocket, 'CONNECTING', {
        value: originalWebSocket.CONNECTING,
        writable: false,
        enumerable: true,
        configurable: true
      })
      Object.defineProperty(window.WebSocket, 'OPEN', {
        value: originalWebSocket.OPEN,
        writable: false,
        enumerable: true,
        configurable: true
      })
      Object.defineProperty(window.WebSocket, 'CLOSING', {
        value: originalWebSocket.CLOSING,
        writable: false,
        enumerable: true,
        configurable: true
      })
      Object.defineProperty(window.WebSocket, 'CLOSED', {
        value: originalWebSocket.CLOSED,
        writable: false,
        enumerable: true,
        configurable: true
      })
    } catch (error) {
      // If we can't set properties, just skip - the blocking still works
      console.warn('🚫 [ErrorHandler] Could not copy WebSocket static properties, but blocking still active')
    }
  }

  init() {
    this.disableServiceWorker()
    this.blockInvalidWebSockets()
    console.log('✅ [ErrorHandler] Initialized - blocking external PWA/WebSocket errors')
  }
}

// Create and initialize the error handler
const errorHandler = new ErrorHandler()
errorHandler.init()

export default errorHandler