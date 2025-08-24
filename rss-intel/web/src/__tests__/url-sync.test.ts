/**
 * @jest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useUrlSync } from '@/hooks/use-url-sync';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

const mockPush = jest.fn();
const mockSearchParams = new Map();

beforeEach(() => {
  jest.clearAllMocks();
  
  (useRouter as jest.Mock).mockReturnValue({
    push: mockPush,
  });
  
  (useSearchParams as jest.Mock).mockReturnValue({
    get: (key: string) => mockSearchParams.get(key) || null,
    toString: () => Array.from(mockSearchParams.entries())
      .map(([k, v]) => `${k}=${v}`)
      .join('&'),
  });
  
  // Setup window location
  delete (window as any).location;
  (window as any).location = {
    pathname: '/dashboard',
    href: 'http://localhost:3000/dashboard',
  };
});

describe('useUrlSync', () => {
  it('should parse filters from URL parameters', () => {
    // Setup mock search params
    mockSearchParams.set('min_score', '80');
    mockSearchParams.set('has_image', 'true');
    mockSearchParams.set('view', 'cards');
    mockSearchParams.set('q', 'test query');
    
    const { result } = renderHook(() => useUrlSync());
    
    expect(result.current.filters).toEqual({
      min_score: 80,
      has_image: true,
      view: 'cards',
      q: 'test query',
    });
  });

  it('should handle boolean parameters correctly', () => {
    mockSearchParams.set('has_image', 'false');
    
    const { result } = renderHook(() => useUrlSync());
    
    expect(result.current.filters.has_image).toBe(false);
  });

  it('should update URL when filters change', () => {
    const { result } = renderHook(() => useUrlSync());
    
    act(() => {
      result.current.updateFilters({ min_score: 60, view: 'list' });
    });
    
    expect(mockPush).toHaveBeenCalledWith(
      '/dashboard?min_score=60&view=list',
      { scroll: false }
    );
  });

  it('should remove undefined filters from URL', () => {
    mockSearchParams.set('min_score', '80');
    mockSearchParams.set('view', 'cards');
    
    const { result } = renderHook(() => useUrlSync());
    
    act(() => {
      result.current.updateFilters({ min_score: undefined });
    });
    
    expect(mockPush).toHaveBeenCalledWith(
      '/dashboard?view=cards',
      { scroll: false }
    );
  });

  it('should clear all filters', () => {
    mockSearchParams.set('min_score', '80');
    mockSearchParams.set('has_image', 'true');
    
    const { result } = renderHook(() => useUrlSync());
    
    act(() => {
      result.current.clearFilters();
    });
    
    expect(mockPush).toHaveBeenCalledWith('/dashboard', { scroll: false });
  });

  it('should copy current URL to clipboard', async () => {
    // Mock clipboard API
    const writeText = jest.fn();
    Object.assign(navigator, {
      clipboard: {
        writeText,
      },
    });
    
    const { result } = renderHook(() => useUrlSync());
    
    act(() => {
      result.current.copyLink();
    });
    
    expect(writeText).toHaveBeenCalledWith('http://localhost:3000/dashboard');
  });
});