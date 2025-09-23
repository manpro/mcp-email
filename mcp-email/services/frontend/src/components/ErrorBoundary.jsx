import React from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0
    }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console in development
    console.error('ErrorBoundary caught an error:', error, errorInfo)

    // Update state with error details
    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1
    }))

    // Send error to logging service (if available)
    try {
      const errorData = {
        message: error.toString(),
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      }

      // Store in localStorage for debugging
      const errors = JSON.parse(localStorage.getItem('appErrors') || '[]')
      errors.push(errorData)
      if (errors.length > 10) errors.shift() // Keep only last 10 errors
      localStorage.setItem('appErrors', JSON.stringify(errors))
    } catch (logError) {
      console.error('Failed to log error:', logError)
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      const isDevelopment = process.env.NODE_ENV === 'development'

      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full bg-white rounded-lg shadow-lg p-6 md:p-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Något gick fel
                </h1>
                <p className="text-sm text-gray-500">
                  Error #{this.state.errorCount}
                </p>
              </div>
            </div>

            <div className="mb-6">
              <p className="text-gray-700 mb-2">
                Ett oväntat fel har uppstått. Vi har loggat felet och arbetar på att lösa problemet.
              </p>
              {isDevelopment && this.state.error && (
                <div className="mt-4 p-4 bg-red-50 rounded-lg">
                  <p className="text-sm font-mono text-red-800 mb-2">
                    {this.state.error.toString()}
                  </p>
                  {this.state.error.stack && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-sm text-red-600 hover:text-red-700">
                        Visa stack trace
                      </summary>
                      <pre className="mt-2 text-xs text-red-700 overflow-x-auto whitespace-pre-wrap">
                        {this.state.error.stack}
                      </pre>
                    </details>
                  )}
                  {this.state.errorInfo && this.state.errorInfo.componentStack && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-sm text-red-600 hover:text-red-700">
                        Visa component stack
                      </summary>
                      <pre className="mt-2 text-xs text-red-700 overflow-x-auto whitespace-pre-wrap">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Försök igen
              </button>

              <button
                onClick={this.handleReload}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Ladda om sidan
              </button>

              <button
                onClick={this.handleGoHome}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                <Home className="w-4 h-4" />
                Till startsidan
              </button>
            </div>

            {isDevelopment && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  💡 Tips: Detta fel visas endast i utvecklingsläge.
                  I produktion kommer användare se en förenklad version.
                </p>
              </div>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary