import { useState } from 'react'
import { Mail, CheckCircle, AlertCircle, X, User, Lock, Server } from 'lucide-react'
import { connectEmail } from '../services/emailService'
import useEmailStore from '../store/emailStore'

export default function ConnectEmail() {
  const [showDialog, setShowDialog] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [status, setStatus] = useState('')
  const { setConnection, isConnected } = useEmailStore()

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    provider: 'auto',
    host: '',
    port: '993'
  })

  // Removed test mode - now only supports real email connections

  const providers = [
    { value: 'auto', label: 'Automatisk detektering' },
    { value: 'gmail', label: 'Gmail' },
    { value: 'outlook', label: 'Outlook/Hotmail' },
    { value: 'oneCom', label: 'One.com' },
    { value: 'custom', label: 'Annan IMAP server' }
  ]

  const handleProviderChange = (e) => {
    const provider = e.target.value
    setFormData({
      ...formData,
      provider,
      host: provider === 'gmail' ? 'imap.gmail.com' :
            provider === 'outlook' ? 'outlook.office365.com' :
            provider === 'oneCom' ? 'imap.one.com' : '',
      port: '993'
    })
  }

  const handleConnect = async (e) => {
    e.preventDefault()

    if (!formData.email || !formData.password) {
      setStatus('❌ Email och lösenord krävs')
      return
    }

    setIsConnecting(true)
    setStatus('Ansluter...')

    try {
      const result = await connectEmail(
        formData.email,
        formData.password,
        formData.provider === 'custom' ? formData.host : formData.provider
      )

      if (result) {
        setConnection(true)
        setStatus(`✅ Ansluten till ${formData.email}`)
        setTimeout(() => {
          setShowDialog(false)
          setStatus('')
        }, 2000)
      } else {
        setStatus('❌ Anslutning misslyckades')
      }
    } catch (error) {
      setStatus(`❌ Fel: ${error.message}`)
    } finally {
      setIsConnecting(false)
    }
  }

  const handleDisconnect = async () => {
    try {
      // Call disconnect API
      const response = await fetch('/api/disconnect/user-1', {
        method: 'POST'
      })

      if (response.ok) {
        setConnection(false)
        setStatus('Frånkopplad')
      }
    } catch (error) {
      console.error('Failed to disconnect:', error)
    }
  }

  return (
    <>
      <div className="p-4 border-b border-gray-200">
        {!isConnected ? (
          <button
            onClick={() => setShowDialog(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-green-500 text-white hover:bg-green-600 transition-all"
          >
            <Mail className="w-4 h-4" />
            Anslut Email
          </button>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-green-600 flex items-center gap-1">
                <CheckCircle className="w-4 h-4" />
                Ansluten
              </span>
              <button
                onClick={handleDisconnect}
                className="text-xs text-red-600 hover:text-red-700"
              >
                Koppla från
              </button>
            </div>
          </div>
        )}

        {status && !showDialog && (
          <div className={`mt-2 text-sm ${
            status.includes('✅') ? 'text-green-600' :
            status.includes('❌') ? 'text-red-600' : 'text-gray-600'
          }`}>
            {status}
          </div>
        )}
      </div>

      {/* Connection Dialog */}
      {showDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Mail className="w-5 h-5" />
                Anslut Email Konto
              </h2>
              <button
                onClick={() => setShowDialog(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleConnect} className="p-6 space-y-4">

              {/* Provider Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Provider
                </label>
                <select
                  value={formData.provider}
                  onChange={handleProviderChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                >
                  {providers.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>

              {/* Email Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Adress
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    placeholder="din@email.com"
                      className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                    required
                  />
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Lösenord
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    placeholder="••••••••"
                      className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                    required
                  />
                </div>
                {formData.provider === 'gmail' && (
                  <p className="mt-1 text-xs text-gray-600">
                    För Gmail, använd ett app-specifikt lösenord om du har 2FA aktiverat
                  </p>
                )}
              </div>

              {/* Custom IMAP Settings */}
              {formData.provider === 'custom' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      IMAP Server
                    </label>
                    <div className="relative">
                      <Server className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={formData.host}
                        onChange={(e) => setFormData({...formData, host: e.target.value})}
                        placeholder="imap.example.com"
                        className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Port
                    </label>
                    <input
                      type="text"
                      value={formData.port}
                      onChange={(e) => setFormData({...formData, port: e.target.value})}
                      placeholder="993"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </>
              )}

              {/* Status Message */}
              {status && (
                <div className={`text-sm ${
                  status.includes('✅') ? 'text-green-600' :
                  status.includes('❌') ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {status}
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowDialog(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Avbryt
                </button>
                <button
                  type="submit"
                  disabled={isConnecting}
                  className={`flex-1 px-4 py-2 rounded-md transition-colors ${
                    isConnecting
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                >
                  {isConnecting ? 'Ansluter...' : 'Anslut'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}