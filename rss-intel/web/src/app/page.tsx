'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, Article, Config } from '@/lib/api';
import Table from '@/components/Table';
import Filters, { FilterState } from '@/components/Filters';
import { ClientTime } from '@/components/ClientTime';

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterState>({});
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchArticles = useCallback(async () => {
    try {
      const data = await apiClient.getArticles({
        ...filters,
        page,
        page_size: 50,
      });
      setArticles(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to fetch articles:', error);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  const fetchConfig = async () => {
    try {
      const data = await apiClient.getConfig();
      setConfig(data);
    } catch (error) {
      console.error('Failed to fetch config:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await apiClient.refresh();
      console.log('Refresh result:', result);
      setLastRefresh(new Date());
      await fetchArticles();
    } catch (error) {
      console.error('Failed to refresh:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  useEffect(() => {
    fetchConfig();
  }, []);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  // Auto-refresh every 10 minutes
  useEffect(() => {
    const interval = setInterval(() => {
      fetchArticles();
    }, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, [fetchArticles]);

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Articles</h2>
          <p className="mt-1 text-sm text-gray-500">
            {total} total articles • Last refresh: <ClientTime date={lastRefresh} format="absolute" />
          </p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {refreshing ? 'Refreshing...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      <Filters config={config} onFilterChange={handleFilterChange} />

      {loading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-500">Loading articles...</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No articles found. Try adjusting your filters or trigger a refresh.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <Table articles={articles} onUpdate={fetchArticles} />
          
          {total > 50 && (
            <div className="px-6 py-4 border-t flex justify-between items-center">
              <div className="text-sm text-gray-500">
                Showing {((page - 1) * 50) + 1} - {Math.min(page * 50, total)} of {total}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm">
                  Page {page} of {Math.ceil(total / 50)}
                </span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= Math.ceil(total / 50)}
                  className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}