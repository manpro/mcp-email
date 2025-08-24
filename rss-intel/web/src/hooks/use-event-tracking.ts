'use client';

import { useEffect } from 'react';
import { useEventTracking, impressionTracker } from '../lib/events';

export function useArticleTracking() {
  const eventTracker = useEventTracking();
  
  useEffect(() => {
    // Initialize impression tracker for articles
    const observer = impressionTracker;
    
    // Find all article elements and start tracking
    const articleElements = document.querySelectorAll('[data-article-id]');
    articleElements.forEach(element => {
      observer.observe(element);
    });
    
    return () => {
      observer.disconnect();
    };
  }, []);
  
  return eventTracker;
}