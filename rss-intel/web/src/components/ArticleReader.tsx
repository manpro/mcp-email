import React, { useState, useEffect } from 'react';
import { X, ExternalLink, Loader2, AlertCircle, RefreshCw, Maximize2, Minimize2, Sparkles } from 'lucide-react';
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
  const [formatting, setFormatting] = useState(false);
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

  const formatWithAI = async () => {
    setFormatting(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/intelligence/format/article/${article.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`AI formatting failed: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.success && result.formatted_content) {
        // Update content with AI-formatted version
        setContent(prev => prev ? {
          ...prev,
          content_html: result.formatted_content
        } : null);
      } else {
        setError('AI formatting failed to improve the content');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to format with AI');
    } finally {
      setFormatting(false);
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

  // Format plain text into readable paragraphs
  const formatTextContent = (text: string) => {
    if (!text) return [];
    
    // Split by double newlines first (paragraph breaks)
    let paragraphs = text.split(/\n\s*\n/);
    
    // If no double newlines, split by single newlines but be more selective
    if (paragraphs.length === 1) {
      paragraphs = text.split(/\n(?=[A-Z]|[0-9]|\s*[-•*])/);
    }
    
    return paragraphs
      .map(para => para.trim())
      .filter(para => para.length > 0 && para.length > 10) // Filter out very short lines
      .map((paragraph, index) => (
        <p key={index} className="mb-6 text-lg leading-8 text-gray-800 dark:text-gray-200">
          {paragraph}
        </p>
      ));
  };

  // Process HTML content to add better styling
  const processHtmlContent = (html: string): string => {
    if (!html) return html;
    
    // Create a temporary div to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // If it's just one big text block without proper paragraphs
    const textContent = tempDiv.textContent || tempDiv.innerText || '';
    if (!html.includes('<p>') && !html.includes('<br>') && textContent.length > 200) {
      // Convert plain text to paragraphs
      const paragraphs = textContent.split(/\n\s*\n/).filter(p => p.trim().length > 10);
      if (paragraphs.length > 1) {
        return paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
      }
      
      // If still no paragraphs, split by sentence groups
      const sentences = textContent.split(/\.\s+/).filter(s => s.trim().length > 0);
      if (sentences.length > 3) {
        const paragraphGroups = [];
        for (let i = 0; i < sentences.length; i += 3) {
          const group = sentences.slice(i, i + 3).join('. ') + (i + 3 < sentences.length ? '.' : '');
          paragraphGroups.push(`<p>${group}</p>`);
        }
        return paragraphGroups.join('');
      }
    }
    
    return html;
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
      <article className="max-w-4xl mx-auto px-8 py-12 bg-white dark:bg-gray-900">
        {content.top_image_url && (
          <div className="mb-8">
            <img
              src={content.top_image_url}
              alt={article.title}
              className="w-full max-h-[500px] object-cover rounded-xl shadow-lg"
            />
          </div>
        )}
        
        <header className="mb-12">
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6 text-gray-900 dark:text-white">
            {article.title}
          </h1>
          
          <div className="flex flex-wrap items-center gap-6 text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 pb-6">
            {content.authors && content.authors.length > 0 && (
              <div className="flex items-center">
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {content.authors.join(', ')}
                </span>
              </div>
            )}
            <div className="flex items-center space-x-4">
              <time className="text-sm">
                {new Date(article.published_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long', 
                  day: 'numeric'
                })}
              </time>
              <span className="text-blue-600 dark:text-blue-400 font-medium">
                {article.source}
              </span>
            </div>
          </div>
        </header>

        {content.content_summary && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-700 p-6 rounded-xl mb-8 border-l-4 border-blue-500">
            <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
              Article Summary
            </h3>
            <p className="text-gray-700 dark:text-gray-300 text-lg leading-relaxed">
              {content.content_summary}
            </p>
          </div>
        )}

        {content.content_keywords && content.content_keywords.length > 0 && (
          <div className="mb-8">
            <div className="flex flex-wrap gap-3">
              {content.content_keywords.map((keyword, index) => (
                <span
                  key={index}
                  className="px-4 py-2 bg-gradient-to-r from-blue-100 to-indigo-100 dark:from-blue-900 dark:to-indigo-900 text-blue-800 dark:text-blue-200 rounded-full text-sm font-medium hover:shadow-md transition-shadow"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="prose prose-xl prose-gray dark:prose-invert max-w-none">
          {content.content_html ? (
            <div
              className="article-content text-lg leading-8 [&>p]:mb-6 [&>h1]:text-3xl [&>h1]:font-bold [&>h1]:mt-12 [&>h1]:mb-6 [&>h2]:text-2xl [&>h2]:font-semibold [&>h2]:mt-10 [&>h2]:mb-4 [&>h3]:text-xl [&>h3]:font-medium [&>h3]:mt-8 [&>h3]:mb-3 [&>blockquote]:border-l-4 [&>blockquote]:border-gray-300 [&>blockquote]:pl-6 [&>blockquote]:italic [&>blockquote]:my-6 [&>ul]:my-6 [&>ol]:my-6 [&>li]:mb-2 [&>img]:rounded-lg [&>img]:shadow-md [&>img]:my-8"
              dangerouslySetInnerHTML={{ 
                __html: fixImageUrls(processHtmlContent(content.content_html), article.url) 
              }}
            />
          ) : (
            <div className="formatted-content">
              {formatTextContent(content.full_content)}
            </div>
          )}
        </div>
      </article>
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
            
            {content?.full_content && (
              <button
                onClick={formatWithAI}
                className="p-2 hover:bg-purple-50 hover:text-purple-600 rounded"
                title="AI Format (GPT-4o-mini)"
                disabled={formatting}
              >
                {formatting ? (
                  <Loader2 className="w-5 h-5 animate-spin text-purple-600" />
                ) : (
                  <Sparkles className="w-5 h-5" />
                )}
              </button>
            )}
            
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