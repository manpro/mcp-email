import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EmailManager from './components/EmailManager'
import ErrorBoundary from './components/ErrorBoundary'

const queryClient = new QueryClient()

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <div className="h-screen bg-gray-50">
          <EmailManager />
        </div>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App