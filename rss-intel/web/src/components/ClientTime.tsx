'use client';

import { useEffect, useState } from 'react';

interface ClientTimeProps {
  date: string | Date;
  format?: 'relative' | 'absolute';
}

export function ClientTime({ date, format = 'relative' }: ClientTimeProps) {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Return a placeholder that matches server render
    return <span>Loading...</span>;
  }

  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  if (format === 'relative') {
    const now = new Date();
    const diff = now.getTime() - dateObj.getTime();
    
    // Handle future dates
    if (diff < 0) {
      return <span>in future</span>;
    }
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    
    if (days > 365) {
      // Very old dates, show years
      const years = Math.floor(days / 365);
      return <span>{years}y ago</span>;
    } else if (days > 30) {
      // Show months for dates older than 30 days
      const months = Math.floor(days / 30);
      return <span>{months}mo ago</span>;
    } else if (days > 0) {
      return <span>{days}d ago</span>;
    } else if (hours > 0) {
      return <span>{hours}h ago</span>;
    } else {
      const minutes = Math.floor(diff / (1000 * 60));
      return <span>{Math.max(0, minutes)}m ago</span>;
    }
  }
  
  // Absolute format
  return <span>{dateObj.toLocaleString()}</span>;
}