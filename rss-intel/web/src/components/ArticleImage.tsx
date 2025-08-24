'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface ArticleImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  blurhash?: string;
  className?: string;
  priority?: boolean;
}

export function ArticleImage({
  src,
  alt,
  width = 300,
  height = 200,
  blurhash,
  className,
  priority = false,
}: ArticleImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [placeholderUrl, setPlaceholderUrl] = useState<string>();

  useEffect(() => {
    if (blurhash) {
      // Create a simple blur placeholder
      const canvas = document.createElement('canvas');
      canvas.width = 40;
      canvas.height = 27;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        // Simple gradient placeholder based on blurhash concept
        const gradient = ctx.createLinearGradient(0, 0, 40, 27);
        gradient.addColorStop(0, '#e5e7eb');
        gradient.addColorStop(1, '#d1d5db');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 40, 27);
        setPlaceholderUrl(canvas.toDataURL());
      }
    }
  }, [blurhash]);

  return (
    <div className={cn("relative overflow-hidden bg-gray-100", className)} style={{ width, height }}>
      {!isLoaded && !hasError && (
        <div className="absolute inset-0 bg-gradient-to-br from-gray-200 to-gray-300 animate-pulse" />
      )}
      {!hasError && (
        <img
          src={src}
          alt={alt}
          className={cn(
            "w-full h-full object-cover transition-opacity duration-300",
            isLoaded ? "opacity-100" : "opacity-0"
          )}
          onLoad={() => setIsLoaded(true)}
          onError={() => {
            setHasError(true);
            console.log('Image failed to load:', src);
          }}
          loading={priority ? "eager" : "lazy"}
        />
      )}
      {hasError && (
        <div className="absolute inset-0 bg-gray-200 flex items-center justify-center">
          <div className="text-gray-400 text-xs text-center">
            <div>📷</div>
            <div>Image unavailable</div>
          </div>
        </div>
      )}
    </div>
  );
}