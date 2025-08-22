'use client';

import { useState, useEffect } from 'react';
import { Config } from '@/lib/api';

interface FiltersProps {
  config: Config | null;
  onFilterChange: (filters: FilterState) => void;
}

export interface FilterState {
  min_score?: number;
  label?: string;
  source?: string;
  q?: string;
}

export default function Filters({ config, onFilterChange }: FiltersProps) {
  const [filters, setFilters] = useState<FilterState>({});
  const [searchTerm, setSearchTerm] = useState('');

  const handleScoreChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value ? parseInt(e.target.value) : undefined;
    setFilters(prev => ({ ...prev, min_score: value }));
  };

  const handleLabelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value || undefined;
    setFilters(prev => ({ ...prev, label: value }));
  };

  const handleSourceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value || undefined;
    setFilters(prev => ({ ...prev, source: value }));
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters(prev => ({ ...prev, q: searchTerm || undefined }));
  };

  useEffect(() => {
    onFilterChange(filters);
  }, [filters, onFilterChange]);

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label htmlFor="min-score" className="block text-sm font-medium text-gray-700 mb-1">
            Min Score
          </label>
          <input
            type="number"
            id="min-score"
            min="0"
            max="100"
            placeholder="0"
            onChange={handleScoreChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div>
          <label htmlFor="label" className="block text-sm font-medium text-gray-700 mb-1">
            Label
          </label>
          <select
            id="label"
            onChange={handleLabelChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Labels</option>
            <option value="hot">🔥 Hot</option>
            <option value="interesting">✨ Interesting</option>
            <option value="starred">⭐ Starred</option>
            <option value="read">✓ Read</option>
          </select>
        </div>

        <div>
          <label htmlFor="source" className="block text-sm font-medium text-gray-700 mb-1">
            Source
          </label>
          <select
            id="source"
            onChange={handleSourceChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Sources</option>
            {config?.sources.map(source => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
            Search
          </label>
          <form onSubmit={handleSearchSubmit} className="flex">
            <input
              type="text"
              id="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-r-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              🔍
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}