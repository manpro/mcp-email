'use client';

import { useState } from 'react';
import { Article, apiClient } from '@/lib/api';
import ScoreBadge from './ScoreBadge';
import { ClientTime } from './ClientTime';
import { clsx } from 'clsx';

interface TableProps {
  articles: Article[];
  onUpdate: () => void;
}

export default function Table({ articles, onUpdate }: TableProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (entryId: string, action: string, label?: string) => {
    setLoading(entryId);
    try {
      await apiClient.decideAction(entryId, { 
        action: action as any, 
        label 
      });
      onUpdate();
    } catch (error) {
      console.error('Action failed:', error);
    } finally {
      setLoading(null);
    }
  };


  const truncateTitle = (title: string, maxLength: number = 80) => {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Score
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Source
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Title
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Age
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Labels
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {articles.map((article) => (
            <tr key={article.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <ScoreBadge score={article.score_total} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {article.source}
              </td>
              <td className="px-6 py-4 text-sm text-gray-900 max-w-md">
                <div>
                  <a 
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-primary-600 hover:underline font-medium"
                    title={article.title}
                  >
                    {truncateTitle(article.title)}
                  </a>
                  {article.content && (
                    <p 
                      className="mt-2 text-sm text-gray-700 leading-relaxed overflow-hidden"
                      style={{
                        display: '-webkit-box',
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: 'vertical',
                      }}
                    >
                      {article.content}
                    </p>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <ClientTime date={article.published_at} format="relative" />
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex gap-1 flex-wrap">
                  {article.flags?.hot && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      🔥 Hot
                    </span>
                  )}
                  {article.flags?.interesting && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                      ✨ Interesting
                    </span>
                  )}
                  {article.flags?.starred && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                      ⭐ Starred
                    </span>
                  )}
                  {article.topics?.slice(0, 2).map(topic => (
                    <span 
                      key={topic}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAction(
                      article.freshrss_entry_id,
                      article.flags?.starred ? 'unstar' : 'star'
                    )}
                    disabled={loading === article.freshrss_entry_id}
                    className={clsx(
                      'px-2 py-1 rounded text-xs font-medium transition-colors',
                      article.flags?.starred
                        ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
                      loading === article.freshrss_entry_id && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {article.flags?.starred ? '★' : '☆'}
                  </button>
                  
                  {article.score_total >= 80 && !article.flags?.hot && (
                    <button
                      onClick={() => handleAction(article.freshrss_entry_id, 'label_add', 'hot')}
                      disabled={loading === article.freshrss_entry_id}
                      className={clsx(
                        'px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200',
                        loading === article.freshrss_entry_id && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      + Hot
                    </button>
                  )}
                  
                  {article.score_total >= 60 && !article.flags?.interesting && (
                    <button
                      onClick={() => handleAction(article.freshrss_entry_id, 'label_add', 'interesting')}
                      disabled={loading === article.freshrss_entry_id}
                      className={clsx(
                        'px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200',
                        loading === article.freshrss_entry_id && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      + Interesting
                    </button>
                  )}
                  
                  {!article.flags?.read && (
                    <button
                      onClick={() => handleAction(article.freshrss_entry_id, 'mark_read')}
                      disabled={loading === article.freshrss_entry_id}
                      className={clsx(
                        'px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200',
                        loading === article.freshrss_entry_id && 'opacity-50 cursor-not-allowed'
                      )}
                    >
                      ✓
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}