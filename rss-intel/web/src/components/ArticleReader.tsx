import React, { useState, useEffect } from 'react';
import { X, ExternalLink, Loader2, AlertCircle, RefreshCw, Maximize2, Minimize2 } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface ArticleReaderProps {
  article: {
    id: number;
    title: string;
    url: string;
    source: string;
    published_at: string;
  };
  onClose: () => void;
}

interface ArticleContent {
  full_content?: string;
  content_html?: string;
  content_summary?: string;
  content_keywords?: string[];
  authors?: string[];
  top_image_url?: string;
  extracted_at?: string;
  extraction_status: string;
  extraction_error?: string;
}

const ArticleReader: React.FC<ArticleReaderProps> = ({ article, onClose }) => {
  const [content, setContent] = useState<ArticleContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'extracted' | 'iframe'>('extracted');
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    fetchContent();
  }, [article.id]);

  const fetchContent = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await apiClient.getArticleContent(article.id);
      setContent(data);
      
      // If content not extracted yet, trigger extraction
      if (data.extraction_status === 'pending') {
        await triggerExtraction();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load article');
    } finally {
      setLoading(false);
    }
  };

  const triggerExtraction = async (force: boolean = false) => {
    setExtracting(true);
    setError(null);
    
    try {
      const result = await apiClient.extractArticleContent(article.id, force);
      
      if (result.status === 'success') {
        // Fetch updated content
        await fetchContent();
      } else {
        setError(result.message || 'Extraction failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to extract article');
    } finally {
      setExtracting(false);
    }
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const fixImageUrls = (html: string, baseUrl: string): string => {
    if (!html) return html;
    
    // Create a temporary div to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // Find all images
    const images = tempDiv.querySelectorAll('img');
    
    images.forEach(img => {
      const src = img.getAttribute('src');
      if (src && !src.startsWith('http') && !src.startsWith('data:')) {
        // It's a relative URL, make it absolute
        try {
          const absoluteUrl = new URL(src, baseUrl).href;
          img.setAttribute('src', absoluteUrl);
        } catch (e) {
          console.warn('Failed to fix image URL:', src, e);
        }
      }
    });
    
    return tempDiv.innerHTML;
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <AlertCircle className="w-12 h-12 text-red-500" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => triggerExtraction(true)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry Extraction
          </button>
        </div>
      );
    }

    if (viewMode === 'iframe') {
      return (
        <iframe
          src={article.url}
          className="w-full h-full border-0"
          title={article.title}
          sandbox="allow-scripts allow-same-origin"
        />
      );
    }

    if (!content?.full_content && content?.extraction_status === 'pending') {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-gray-600">Extracting article content...</p>
        </div>
      );
    }

    if (!content?.full_content) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <AlertCircle className="w-12 h-12 text-yellow-500" />
          <p className="text-gray-600">No content available</p>
          <button
            onClick={() => triggerExtraction(false)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            disabled={extracting}
          >
            {extracting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              'Extract Content'
            )}
          </button>
        </div>
      );
    }

    return (
      <div className="prose prose-lg max-w-none p-6">
        {content.top_image_url && (
          <img
            src={content.top_image_url}
            alt={article.title}
            className="w-full max-h-96 object-cover rounded-lg mb-6"
          />
        )}
        
        <h1 className="text-3xl font-bold mb-4">{article.title}</h1>
        
        <div className="text-sm text-gray-600 mb-6 space-y-1">
          {content.authors && content.authors.length > 0 && (
            <p>By {content.authors.join(', ')}</p>
          )}
          <p>{new Date(article.published_at).toLocaleDateString()}</p>
          <p className="text-blue-600">{article.source}</p>
        </div>

        {content.content_summary && (
          <div className="bg-gray-100 p-4 rounded-lg mb-6">
            <h3 className="font-semibold mb-2">Summary</h3>
            <p className="text-gray-700">{content.content_summary}</p>
          </div>
        )}

        {content.content_keywords && content.content_keywords.length > 0 && (
          <div className="mb-6">
            <div className="flex flex-wrap gap-2">
              {content.content_keywords.map((keyword, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {content.content_html ? (
          <div
            className="article-content"
            dangerouslySetInnerHTML={{ 
              __html: fixImageUrls(content.content_html, article.url) 
            }}
          />
        ) : (
          <div className="whitespace-pre-wrap">{content.full_content}</div>
        )}
      </div>
    );
  };

  const handleBackgroundClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleEscapeKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  useEffect(() => {
    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, []);

  return (
    <div 
      className={`fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4 ${isFullscreen ? 'p-0' : ''}`}
      onClick={handleBackgroundClick}
    >
      <div className={`bg-white rounded-lg shadow-xl ${isFullscreen ? 'w-full h-full rounded-none' : 'max-w-5xl w-full max-h-[90vh]'} flex flex-col`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold truncate max-w-xl">
              {article.title}
            </h2>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* View mode toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('extracted')}
                className={`px-3 py-1 rounded ${viewMode === 'extracted' ? 'bg-white shadow' : ''}`}
              >
                Reader
              </button>
              <button
                onClick={() => setViewMode('iframe')}
                className={`px-3 py-1 rounded ${viewMode === 'iframe' ? 'bg-white shadow' : ''}`}
              >
                Original
              </button>
            </div>
            
            {/* Action buttons */}
            <button
              onClick={() => window.open(article.url, '_blank')}
              className="p-2 hover:bg-gray-100 rounded"
              title="Open in new tab"
            >
              <ExternalLink className="w-5 h-5" />
            </button>
            
            {content?.extraction_status === 'success' && (
              <button
                onClick={() => triggerExtraction(true)}
                className="p-2 hover:bg-gray-100 rounded"
                title="Re-extract content"
                disabled={extracting}
              >
                {extracting ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <RefreshCw className="w-5 h-5" />
                )}
              </button>
            )}
            
            <button
              onClick={toggleFullscreen}
              className="p-2 hover:bg-gray-100 rounded"
              title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? (
                <Minimize2 className="w-5 h-5" />
              ) : (
                <Maximize2 className="w-5 h-5" />
              )}
            </button>
            
            <button
              onClick={onClose}
              className="p-2 hover:bg-red-50 hover:text-red-600 rounded-full border border-gray-200 hover:border-red-300 transition-colors"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-auto">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default ArticleReader;