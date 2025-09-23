import { useState } from 'react'
import CategorySelector from './CategorySelector'
import CompactCategorySelector from './CompactCategorySelector'

const mockEmail = {
  uid: 'demo-email-1',
  from: 'example@example.com',
  subject: 'Demo Email för UX Jämförelse',
  text: 'Detta är en demo för att visa skillnaden mellan olika kategori-UX lösningar.',
  category: 'newsletter'
}

export default function CategoryComparisonDemo() {
  const [originalCategory, setOriginalCategory] = useState('newsletter')
  const [compactCategory, setCompactCategory] = useState('newsletter')
  const [compactCompactCategory, setCompactCompactCategory] = useState('newsletter')

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Kategori UX Jämförelse
        </h1>
        <p className="text-gray-600">
          Jämförelse mellan olika ansatser för att visa e-postkategorier
        </p>
      </div>

      {/* Original implementation */}
      <div className="border border-gray-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          🔴 Original: Fullständig text + dropdown
        </h2>
        <div className="bg-gray-50 p-3 rounded">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Tar mycket plats →</span>
            <CategorySelector
              email={mockEmail}
              currentCategory={originalCategory}
              onCategoryChange={setOriginalCategory}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          ❌ Problem: Tar ~120-150px horisontellt utrymme per kategori
        </p>
      </div>

      {/* Compact implementation */}
      <div className="border border-green-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          🟢 Ny: Kollapsbar toolbar + tooltips
        </h2>
        <div className="bg-gray-50 p-3 rounded">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Kompakt design →</span>
            <CompactCategorySelector
              email={mockEmail}
              currentCategory={compactCategory}
              onCategoryChange={setCompactCategory}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          ✅ Fördelar: Visar 4 prioritets-kategorier + expanderbar för resten. ~160px totalt.
        </p>
      </div>

      {/* Ultra compact implementation */}
      <div className="border border-blue-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          🔵 Ultra-kompakt: Endast nuvarande kategori
        </h2>
        <div className="bg-gray-50 p-3 rounded">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Minimal footprint →</span>
            <CompactCategorySelector
              email={mockEmail}
              currentCategory={compactCompactCategory}
              onCategoryChange={setCompactCompactCategory}
              compact={true}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          ✅ Extremt kompakt: Endast 24px bredd. Perfekt för mobila enheter.
        </p>
      </div>

      {/* Space comparison */}
      <div className="border border-purple-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          📊 Utrymmes-jämförelse
        </h2>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-32 h-6 bg-red-200 rounded flex items-center justify-center text-xs">
              Original: ~150px
            </div>
            <span className="text-gray-600">per kategori</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-40 h-6 bg-green-200 rounded flex items-center justify-center text-xs">
              Kompakt: ~160px totalt
            </div>
            <span className="text-gray-600">för alla kategorier</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-blue-200 rounded flex items-center justify-center text-xs">
              24
            </div>
            <span className="text-gray-600">ultra-kompakt</span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          💡 Besparingen: ~85% mindre utrymme på mobilenheter
        </p>
      </div>

      {/* Feature comparison */}
      <div className="border border-gray-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          ⚖️ Funktions-jämförelse
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Funktion</th>
                <th className="text-center py-2">Original</th>
                <th className="text-center py-2">Kompakt</th>
                <th className="text-center py-2">Ultra-kompakt</th>
              </tr>
            </thead>
            <tbody className="text-xs">
              <tr className="border-b">
                <td className="py-2">Visar kategori-namn</td>
                <td className="text-center">✅</td>
                <td className="text-center">✅ (tooltip)</td>
                <td className="text-center">✅ (tooltip)</td>
              </tr>
              <tr className="border-b">
                <td className="py-2">Prioritets-kategorier synliga</td>
                <td className="text-center">❌</td>
                <td className="text-center">✅</td>
                <td className="text-center">❌</td>
              </tr>
              <tr className="border-b">
                <td className="py-2">Senast använda kategorier</td>
                <td className="text-center">❌</td>
                <td className="text-center">✅</td>
                <td className="text-center">❌</td>
              </tr>
              <tr className="border-b">
                <td className="py-2">Mobil-anpassad</td>
                <td className="text-center">⚠️</td>
                <td className="text-center">✅</td>
                <td className="text-center">✅✅</td>
              </tr>
              <tr className="border-b">
                <td className="py-2">Utrymme per email-rad</td>
                <td className="text-center">~150px</td>
                <td className="text-center">~160px</td>
                <td className="text-center">~24px</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}