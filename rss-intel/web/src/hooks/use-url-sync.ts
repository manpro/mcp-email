'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useMemo } from 'react';

export interface FilterParams {
  min_score?: number;
  label?: string;
  source?: string;
  q?: string;
  has_image?: boolean;
  view?: 'list' | 'cards';
  tab?: 'browse' | 'recommended' | 'search' | 'ask' | 'spotlight' | 'briefings' | 'experiments' | 'spam' | 'email' | 'analytics';
}

export function useUrlSync() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const filters = useMemo((): FilterParams => {
    const params: FilterParams = {};
    
    const minScore = searchParams.get('min_score');
    if (minScore) params.min_score = parseInt(minScore, 10);
    
    const label = searchParams.get('label');
    if (label) params.label = label;
    
    const source = searchParams.get('source');
    if (source) params.source = source;
    
    const q = searchParams.get('q');
    if (q) params.q = q;
    
    const hasImage = searchParams.get('has_image');
    if (hasImage === 'true') params.has_image = true;
    else if (hasImage === 'false') params.has_image = false;
    
    const view = searchParams.get('view');
    if (view === 'list' || view === 'cards') params.view = view;
    
    const tab = searchParams.get('tab');
    if (tab === 'browse' || tab === 'recommended' || tab === 'search' || tab === 'ask' || tab === 'spotlight' || tab === 'briefings' || tab === 'experiments' || tab === 'spam' || tab === 'email' || tab === 'analytics') params.tab = tab;
    
    return params;
  }, [searchParams]);

  const updateFilters = useCallback((newFilters: Partial<FilterParams>) => {
    const params = new URLSearchParams(searchParams.toString());
    
    // Update or remove each filter
    Object.entries(newFilters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    });
    
    // Navigate with new params
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    router.push(newUrl, { scroll: false });
  }, [router, searchParams]);

  const clearFilters = useCallback(() => {
    router.push(window.location.pathname, { scroll: false });
  }, [router]);

  const copyLink = useCallback(() => {
    navigator.clipboard.writeText(window.location.href);
  }, []);

  return {
    filters,
    updateFilters,
    clearFilters,
    copyLink,
  };
}