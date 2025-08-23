'use client';

import { useState, useEffect } from 'react';
import { Article, ArticleList, apiClient, Config } from '@/lib/api';
import { VirtualizedList, ViewMode } from './VirtualizedList';
import { ViewToggle } from './ViewToggle';
import { RecommendedTab } from './RecommendedTab';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Toggle } from '@/components/ui/toggle';
import { useUrlSync } from '@/hooks/use-url-sync';
import { useToast } from '@/hooks/use-toast';
import { RefreshCw, Search, Link, X, Image, Sparkles, MessageSquare, Compass } from 'lucide-react';
import { cn } from '@/lib/utils';
import ArticleReader from './ArticleReader';
import { SearchTab } from './SearchTab';
import { AskTab } from './AskTab';
import { GlobalSearch } from './GlobalSearch';

export default function Dashboard() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;
  
  const { filters, updateFilters, clearFilters, copyLink } = useUrlSync();
  const { toast } = useToast();

  // Tab management
  type TabType = 'browse' | 'recommended' | 'search' | 'ask';
  const currentTab: TabType = (filters.tab as TabType) || 'browse';

  // Load config on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const configData = await apiClient.getConfig();
        setConfig(configData);
      } catch (error) {
        console.error('Failed to load config:', error);
      }
    };
    loadConfig();
  }, []);

  // Load articles when filters change
  useEffect(() => {
    const loadArticles = async () => {
      try {
        setLoading(true);
        setCurrentPage(1);
        const response = await apiClient.getArticles({
          ...filters,
          page: 1,
          page_size: pageSize
        });
        setArticles(response.items);
        setTotal(response.total);
      } catch (error) {
        console.error('Failed to load articles:', error);
        toast({
          type: 'error',
          title: 'Error',
          description: 'Failed to load articles'
        });
      } finally {
        setLoading(false);
      }
    };
    loadArticles();
  }, [filters]);

  // Sync search input with URL
  useEffect(() => {
    setSearchInput(filters.q || '');
  }, [filters.q]);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await apiClient.refresh();
      // Reload articles
      setCurrentPage(1);
      const response = await apiClient.getArticles({
        ...filters,
        page: 1,
        page_size: pageSize
      });
      setArticles(response.items);
      setTotal(response.total);
      toast({
        type: 'success',
        title: 'Refreshed',
        description: 'Articles refreshed successfully'
      });
    } catch (error) {
      console.error('Refresh failed:', error);
      toast({
        type: 'error',
        title: 'Refresh Failed',
        description: 'Failed to refresh articles'
      });
    } finally {
      setRefreshing(false);
    }
  };

  const loadMoreArticles = async () => {
    if (loadingMore || articles.length >= total) return;
    
    try {
      setLoadingMore(true);
      const nextPage = currentPage + 1;
      const response = await apiClient.getArticles({
        ...filters,
        page: nextPage,
        page_size: pageSize
      });
      
      setArticles(prevArticles => [...prevArticles, ...response.items]);
      setCurrentPage(nextPage);
    } catch (error) {
      console.error('Failed to load more articles:', error);
      toast({
        type: 'error',
        title: 'Load More Failed',
        description: 'Failed to load more articles'
      });
    } finally {
      setLoadingMore(false);
    }
  };

  const handleExtractContent = async (articleId: number) => {
    try {
      setActionLoading(`extract_${articleId}`);
      
      // Update article status to 'processing'
      setArticles(prevArticles =>
        prevArticles.map(article =>
          article.id === articleId
            ? { ...article, extraction_status: 'processing' }
            : article
        )
      );
      
      const response = await apiClient.extractArticleContent(articleId, true);
      
      if (response.status === 'success') {
        // Update article with extracted content
        setArticles(prevArticles =>
          prevArticles.map(article =>
            article.id === articleId
              ? { 
                  ...article, 
                  extraction_status: 'success',
                  extracted_at: new Date().toISOString(),
                  full_content: response.data?.full_content,
                  content_summary: response.data?.content_summary
                }
              : article
          )
        );
        
        toast({
          type: 'success',
          title: 'Content Extracted',
          description: 'Article content extracted successfully',
          duration: 3000
        });
      } else {
        // Update article status to 'failed'
        setArticles(prevArticles =>
          prevArticles.map(article =>
            article.id === articleId
              ? { ...article, extraction_status: 'failed', extraction_error: response.message }
              : article
          )
        );
        
        toast({
          type: 'error',
          title: 'Extraction Failed',
          description: response.message || 'Failed to extract content'
        });
      }
    } catch (error) {
      console.error('Content extraction failed:', error);
      
      // Update article status to 'failed'
      setArticles(prevArticles =>
        prevArticles.map(article =>
          article.id === articleId
            ? { ...article, extraction_status: 'failed', extraction_error: 'Network error' }
            : article
        )
      );
      
      toast({
        type: 'error',
        title: 'Extraction Failed',
        description: 'Failed to extract article content'
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleAction = async (entryId: string, action: string, label?: string) => {
    // Handle read action to open ArticleReader
    if (action === 'read') {
      const article = articles.find(a => a.freshrss_entry_id === entryId);
      if (article) {
        setSelectedArticle(article);
      }
      return;
    }
    
    try {
      setActionLoading(entryId);
      await apiClient.decideAction(entryId, { action: action as any, label });
      
      // Optimistic update
      setArticles(prevArticles => 
        prevArticles.map(article => {
          if (article.freshrss_entry_id === entryId) {
            const newFlags = { ...article.flags };
            
            if (action === 'star') {
              newFlags.starred = true;
            } else if (action === 'unstar') {
              newFlags.starred = false;
            } else if (action === 'mark_read') {
              newFlags.read = true;
            } else if (action === 'label_add' && label) {
              newFlags[label] = true;
            } else if (action === 'label_remove' && label) {
              delete newFlags[label];
            }
            
            return { ...article, flags: newFlags };
          }
          return article;
        })
      );

      toast({
        type: 'success',
        title: 'Success',
        description: `Action ${action} completed`,
        duration: 2000
      });
    } catch (error) {
      console.error('Action failed:', error);
      toast({
        type: 'error',
        title: 'Action Failed',
        description: `Failed to ${action} article`
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ q: searchInput || undefined });
  };

  const clearSearch = () => {
    setSearchInput('');
    updateFilters({ q: undefined });
  };

  const handleViewChange = (view: ViewMode) => {
    updateFilters({ view });
    // Store preference in localStorage
    localStorage.setItem('rss-intel-view', view);
  };

  // Get view mode from URL or localStorage
  const currentView: ViewMode = filters.view || 
    (typeof window !== 'undefined' ? localStorage.getItem('rss-intel-view') as ViewMode : null) || 
    'list';

  // Get image toggle state from localStorage
  const [imageMode, setImageMode] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('rss-intel-images');
      setImageMode(saved === 'true');
    }
  }, []);

  const toggleImages = (enabled: boolean) => {
    setImageMode(enabled);
    localStorage.setItem('rss-intel-images', String(enabled));
    updateFilters({ 
      has_image: enabled ? true : undefined,
      view: enabled && currentView === 'list' ? 'cards' : currentView 
    });
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b bg-white p-4">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">RSS Intelligence Dashboard</h1>
          <div className="flex items-center gap-4">
            <GlobalSearch />
            <div className="flex items-center gap-2">
              <Button
                onClick={handleRefresh}
                disabled={refreshing}
                size="sm"
              >
                <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
                Refresh
              </Button>
              <Button
                onClick={copyLink}
                variant="ghost"
                size="sm"
              >
                <Link className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Tab navigation */}
        <div className="flex space-x-1 mb-4">
          <Button
            variant={currentTab === 'browse' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'browse' })}
            className="flex items-center gap-2"
          >
            <Compass className="h-4 w-4" />
            Browse
          </Button>
          <Button
            variant={currentTab === 'recommended' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'recommended' })}
            className="flex items-center gap-2"
          >
            <Sparkles className="h-4 w-4" />
            Recommended
          </Button>
          <Button
            variant={currentTab === 'search' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'search' })}
            className="flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            Search
          </Button>
          <Button
            variant={currentTab === 'ask' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'ask' })}
            className="flex items-center gap-2"
          >
            <MessageSquare className="h-4 w-4" />
            Ask AI
          </Button>
        </div>

        {/* Filters - only show for Browse tab */}
        {currentTab === 'browse' && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 max-w-md">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search articles..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-10"
                />
                {searchInput && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={clearSearch}
                    className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
              <Button type="submit" size="sm">
                <Search className="h-4 w-4" />
              </Button>
            </form>

            {/* Score filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Min Score:</span>
              {[60, 80].map((score) => (
                <Button
                  key={score}
                  variant={filters.min_score === score ? "default" : "outline"}
                  size="sm"
                  onClick={() => updateFilters({
                    min_score: filters.min_score === score ? undefined : score
                  })}
                >
                  {score}+
                </Button>
              ))}
            </div>

            {/* Image toggle */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Images:</span>
              <Toggle
                pressed={imageMode}
                onPressedChange={toggleImages}
                size="sm"
              >
                <Image className="h-4 w-4 mr-2" />
                {imageMode ? 'On' : 'Off'}
              </Toggle>
            </div>

            {/* View toggle */}
            <ViewToggle
              view={currentView}
              onViewChange={handleViewChange}
            />
          </div>

          {/* Active filters */}
          <div className="flex items-center gap-2">
            {filters.min_score && (
              <Badge variant="secondary">
                Score ≥ {filters.min_score}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => updateFilters({ min_score: undefined })}
                  className="ml-2 h-4 w-4 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            )}
            {filters.label && (
              <Badge variant="secondary">
                Label: {filters.label}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => updateFilters({ label: undefined })}
                  className="ml-2 h-4 w-4 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            )}
            {filters.source && (
              <Badge variant="secondary">
                Source: {filters.source}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => updateFilters({ source: undefined })}
                  className="ml-2 h-4 w-4 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            )}
            {filters.has_image && (
              <Badge variant="secondary">
                With images
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => updateFilters({ has_image: undefined })}
                  className="ml-2 h-4 w-4 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            )}
            {(filters.min_score || filters.label || filters.source || filters.q || filters.has_image) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="text-muted-foreground"
              >
                Clear all
              </Button>
            )}
          </div>

          {/* Results count */}
          <div className="text-sm text-muted-foreground">
            Showing {articles.length} of {total} articles
          </div>
        </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {currentTab === 'browse' ? (
          loading ? (
            <div className="flex items-center justify-center h-full">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <VirtualizedList
                articles={articles}
                viewMode={currentView}
                onAction={handleAction}
                onExtractContent={handleExtractContent}
                loading={actionLoading}
                imageProxyBase={config?.imageProxyBase || '/img'}
              />
              
              {/* Load More Button */}
              {articles.length < total && (
                <div className="flex justify-center p-4 border-t">
                  <Button
                    onClick={loadMoreArticles}
                    disabled={loadingMore}
                    variant="outline"
                    size="lg"
                    className="min-w-[200px]"
                  >
                    {loadingMore ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Loading more...
                      </>
                    ) : (
                      <>
                        Load More ({articles.length} of {total})
                      </>
                    )}
                  </Button>
                </div>
              )}
            </>
          )
        ) : currentTab === 'recommended' ? (
          <div className="p-4">
            <RecommendedTab
              onArticleClick={(articleId) => {
                // For now, just log - we need to adapt ArticleReader to work with recommendation data
                console.log('Open recommended article:', articleId);
              }}
              onExternalClick={(articleId) => {
                console.log('External click for article:', articleId);
                // URL is already available in the RecommendedTab component
              }}
              onStar={(articleId) => {
                toast({
                  type: 'success',
                  title: 'Starred',
                  description: 'Article starred successfully',
                  duration: 2000
                });
              }}
              onDismiss={(articleId) => {
                toast({
                  type: 'info',
                  title: 'Dismissed',
                  description: 'Article marked as not interested',
                  duration: 2000
                });
              }}
            />
          </div>
        ) : currentTab === 'search' ? (
          <div className="p-4 overflow-y-auto h-full">
            <SearchTab />
          </div>
        ) : currentTab === 'ask' ? (
          <div className="p-4 overflow-y-auto h-full">
            <AskTab />
          </div>
        ) : null}
      </div>
      
      {/* Article Reader Modal */}
      {selectedArticle && (
        <ArticleReader
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
        />
      )}
    </div>
  );
}