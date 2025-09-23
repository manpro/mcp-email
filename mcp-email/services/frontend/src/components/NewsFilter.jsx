import { useState, useEffect } from 'react'
import { Globe, TrendingUp, Shield, AlertCircle, X } from 'lucide-react'
import useEmailStore from '../store/emailStore'
import { userProfile } from '../config/userProfile'

export default function NewsFilter({ emails }) {
  const [filteredNews, setFilteredNews] = useState({
    critical: [],
    sweden: [],
    economy: [],
    geopolitics: [],
    ignored: []
  })

  useEffect(() => {
    categorizeNews()
  }, [emails])

  const categorizeNews = () => {
    const categories = {
      critical: [],
      sweden: [],
      economy: [],
      geopolitics: [],
      ignored: []
    }

    emails.forEach(email => {
      const subject = email.subject?.toLowerCase() || ''
      const from = email.from?.toLowerCase() || ''
      const text = (email.text || email.html || '').toLowerCase()

      // Kritiska nyheter - Ukraina/Israel
      if (text.includes('ukraina') || text.includes('ukraine') ||
          text.includes('israel') || text.includes('gaza') ||
          text.includes('palestina')) {
        categories.critical.push(email)
      }
      // Svenska/EU nyheter
      else if (text.includes('sverige') || text.includes('swedish') ||
               text.includes('stockholm') || text.includes('eu') ||
               from.includes('.se') || from.includes('svenska')) {
        categories.sweden.push(email)
      }
      // Ekonomi/Finans
      else if (text.includes('ränta') || text.includes('inflation') ||
               text.includes('centralbank') || text.includes('riksbank') ||
               text.includes('ecb') || text.includes('federal reserve') ||
               text.includes('makroekonomi')) {
        categories.economy.push(email)
      }
      // Geopolitik
      else if (text.includes('nato') || text.includes('konflikt') ||
               text.includes('sanktion')) {
        categories.geopolitics.push(email)
      }
      // Ignorera - lokala nyheter Asien/USA
      else if (text.includes('local news') &&
               (text.includes('asia') || text.includes('america') ||
                text.includes('usa') || text.includes('california') ||
                text.includes('tokyo') || text.includes('singapore'))) {
        categories.ignored.push(email)
      }
    })

    setFilteredNews(categories)
  }

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'critical': return <AlertCircle className="w-4 h-4 text-red-500" />
      case 'sweden': return <Globe className="w-4 h-4 text-blue-500" />
      case 'economy': return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'geopolitics': return <Shield className="w-4 h-4 text-purple-500" />
      case 'ignored': return <X className="w-4 h-4 text-gray-400" />
      default: return null
    }
  }

  const getCategoryLabel = (category) => {
    switch (category) {
      case 'critical': return 'Kritiska nyheter (Ukraina/Israel)'
      case 'sweden': return 'Sverige & EU'
      case 'economy': return 'Makroekonomi'
      case 'geopolitics': return 'Geopolitik'
      case 'ignored': return 'Filtrerat bort'
      default: return category
    }
  }

  return (
    <div className="p-4 space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Nyhetsfiltrering</h3>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-sm text-blue-800">
          <strong>Dina preferenser:</strong> Prioriterar svenska/EU-nyheter, Ukraina/Israel-konflikter,
          och makroekonomi. Filtrerar bort lokala nyheter från Asien/USA.
        </p>
      </div>

      {Object.entries(filteredNews).map(([category, items]) => (
        <div key={category} className="border rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {getCategoryIcon(category)}
              <span className="font-medium text-gray-900">
                {getCategoryLabel(category)}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {items.length} email{items.length !== 1 ? 's' : ''}
            </span>
          </div>

          {items.length > 0 && (
            <div className="space-y-1 mt-2">
              {items.slice(0, 3).map((email, idx) => (
                <div key={idx} className="text-xs text-gray-600 truncate">
                  • {email.subject}
                </div>
              ))}
              {items.length > 3 && (
                <div className="text-xs text-gray-500">
                  +{items.length - 3} mer...
                </div>
              )}
            </div>
          )}

          {category === 'ignored' && items.length > 0 && (
            <button className="mt-2 text-xs text-red-600 hover:text-red-700">
              Avprenumerera från alla
            </button>
          )}
        </div>
      ))}

      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
        <p className="text-sm text-green-800 font-medium mb-2">
          AI-förslag baserat på dina preferenser:
        </p>
        <ul className="text-sm text-green-700 space-y-1">
          <li>• Flytta {filteredNews.critical.length} kritiska nyheter till "Prioriterat"</li>
          <li>• Arkivera {filteredNews.ignored.length} ointressanta nyheter</li>
          <li>• Skapa sammanfattning av dagens makronyheter</li>
        </ul>
        <button className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm">
          Applicera alla förslag
        </button>
      </div>
    </div>
  )
}