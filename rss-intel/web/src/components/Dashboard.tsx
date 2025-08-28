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
import { RefreshCw, Search, Link, X, Image, Sparkles, MessageSquare, Compass, Settings, Mail, BarChart3, Beaker, AlertTriangle, ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import ArticleReader from './ArticleReader';
import { SearchTab } from './SearchTab';
import { AskTab } from './AskTab';
import { SpotlightTab } from './SpotlightTab';
import { GlobalSearch } from './GlobalSearch';
import { SpamTab } from './SpamTab';
import FediverseTab from './FediverseTab';
import SourceHealthTab from './SourceHealthTab';
import { TrendingTab } from './TrendingTab';
import BriefingsTab from './BriefingsTab';
import BriefingsTabSimple from './BriefingsTabSimple';

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
  const [headerCollapsed, setHeaderCollapsed] = useState(false);
  const pageSize = 200;
  
  const { filters, updateFilters, clearFilters, copyLink } = useUrlSync();
  const { toast } = useToast();

  // Tab management
  type TabType = 'browse' | 'recommended' | 'search' | 'ask' | 'spotlight' | 'briefings' | 'experiments' | 'spam' | 'email' | 'analytics' | 'fediverse' | 'health' | 'trending';
  const currentTab: TabType = (filters.tab as TabType) || 'browse';
  
  // Debug: Log tab information
  console.log('DEBUG - filters:', filters);
  console.log('DEBUG - filters.tab:', filters.tab);
  console.log('DEBUG - currentTab:', currentTab);

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
    setCurrentView(view);
    updateFilters({ view });
    // Store preference in localStorage
    localStorage.setItem('rss-intel-view', view);
  };

  const handleReportSpam = async (articleId: number) => {
    try {
      const response = await fetch(`/api/articles/${articleId}/report-spam`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to report spam');
      }

      const result = await response.json();
      
      toast({
        title: "Rapporterad som spam",
        description: "Artikeln har markerats som spam och tas bort från flödet",
        type: "success",
      });

      // Remove article from current view
      setArticles(prev => prev.filter(article => article.id !== articleId));
      setTotal(prev => prev - 1);

    } catch (error) {
      console.error('Error reporting spam:', error);
      toast({
        title: "Fel",
        description: "Kunde inte rapportera spam",
        type: "error",
      });
    }
  };

  // Get view mode with proper SSR handling
  const [currentView, setCurrentView] = useState<ViewMode>('list');
  
  useEffect(() => {
    // Set view from URL or localStorage after hydration
    const viewFromUrl = filters.view;
    const viewFromStorage = typeof window !== 'undefined' ? localStorage.getItem('rss-intel-view') as ViewMode : null;
    const finalView = viewFromUrl || viewFromStorage || 'list';
    setCurrentView(finalView);
  }, [filters.view]);

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
      <div className="border-b bg-white px-4 py-2 sm:p-4">
        {/* Mobile header with collapse */}
        <div className="flex md:hidden items-center justify-between mb-2">
          <h1 className={cn("font-bold transition-all", headerCollapsed ? "text-lg" : "text-xl")}>
            RSS Intelligence
          </h1>
          <div className="flex items-center gap-2">
            {!headerCollapsed && (
              <Badge variant="outline" className="text-xs">
                {total}
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setHeaderCollapsed(!headerCollapsed)}
              className="p-1 h-6 w-6"
            >
              {headerCollapsed ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
              )}
            </Button>
          </div>
        </div>
        
        {/* Desktop header - always visible */}
        <div className="hidden md:flex items-center justify-between mb-4">
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

        {/* Mobile collapsible content */}
        {!headerCollapsed && (
          <div className="md:hidden mb-3">
            <div className="flex items-center justify-between mb-2">
              <GlobalSearch />
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  variant="ghost"
                  size="sm"
                >
                  <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
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
        )}

        {/* Tab navigation - always visible but responsive */}
        <div className={cn(
          "mb-4 transition-all",
          headerCollapsed ? "hidden md:flex md:space-x-1" : "flex space-x-1 overflow-x-auto"
        )}>
          <Button
            variant={currentTab === 'browse' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'browse' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <Compass className="h-4 w-4" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Browse</span>
          </Button>
          <Button
            variant={currentTab === 'recommended' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'recommended' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <Sparkles className="h-4 w-4" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Recommended</span>
          </Button>
          <Button
            variant={currentTab === 'search' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'search' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <Search className="h-4 w-4" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Search</span>
          </Button>
          <Button
            variant={currentTab === 'ask' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'ask' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <MessageSquare className="h-4 w-4" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Ask AI</span>
          </Button>
          <Button
            variant={currentTab === 'spotlight' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'spotlight' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <Sparkles className="h-4 w-4 text-amber-500" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Spotlight</span>
          </Button>
          <Button
            variant={currentTab === 'briefings' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'briefings' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <Mail className="h-4 w-4 text-blue-500" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Briefings</span>
          </Button>
          <Button
            variant={currentTab === 'experiments' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'experiments' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <Beaker className="h-4 w-4 text-purple-500" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Experiments</span>
          </Button>
          <Button
            variant={currentTab === 'fediverse' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'fediverse' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <MessageSquare className="h-4 w-4 text-blue-500" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Fediverse</span>
          </Button>
          <Button
            variant={currentTab === 'health' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'health' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <AlertTriangle className="h-4 w-4 text-orange-500" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Health</span>
          </Button>
          <Button
            variant={currentTab === 'trending' ? 'default' : 'ghost'}
            onClick={() => updateFilters({ tab: 'trending' })}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap",
              headerCollapsed ? "text-sm px-2" : ""
            )}
          >
            <BarChart3 className="h-4 w-4 text-green-500" />
            <span className={headerCollapsed ? "hidden lg:inline" : ""}>Trending</span>
          </Button>
        </div>

        {/* Filters - only show for Browse tab and when not collapsed on mobile */}
        {currentTab === 'browse' && (
        <div className={cn(
          "flex flex-col gap-4",
          headerCollapsed ? "hidden md:flex" : "flex"
        )}>
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
                onArticleClick={setSelectedArticle}
                onReportSpam={handleReportSpam}
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
        ) : currentTab === 'spotlight' ? (
          <div className="p-4 overflow-y-auto h-full">
            <SpotlightTab onArticleClick={setSelectedArticle} />
          </div>
        ) : currentTab === 'briefings' ? (
          <div className="p-4 overflow-y-auto h-full">
            <BriefingsTab />
          </div>
        ) : currentTab === 'email' ? (
          <div className="p-4 overflow-y-auto h-full">
            <div className="text-center py-8">
              <Mail className="h-12 w-12 text-blue-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Email Integration</h2>
              <p className="text-muted-foreground">Email newsletter management coming soon</p>
            </div>
          </div>
        ) : currentTab === 'analytics' ? (
          <div className="p-4 overflow-y-auto h-full">
            <div className="text-center py-8">
              <BarChart3 className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Analytics Dashboard</h2>
              <p className="text-muted-foreground">Reading analytics and insights coming soon</p>
            </div>
          </div>
        ) : currentTab === 'experiments' ? (
          <div className="p-4 overflow-y-auto h-full">
            <div className="text-center py-8">
              <Beaker className="h-12 w-12 text-purple-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Experimental Features</h2>
              <p className="text-muted-foreground">Try new AI-powered content features</p>
            </div>
          </div>
        ) : currentTab === 'spam' ? (
          <div className="p-4 overflow-y-auto h-full">
            <SpamTab onArticleClick={setSelectedArticle} />
          </div>
        ) : currentTab === 'fediverse' ? (
          <div className="p-4 overflow-y-auto h-full">
            <FediverseTab />
          </div>
        ) : currentTab === 'health' ? (
          <div className="p-4 overflow-y-auto h-full">
            <SourceHealthTab />
          </div>
        ) : currentTab === 'trending' ? (
          <div className="p-4 overflow-y-auto h-full">
            <TrendingTab />
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
      
      {/* Admin link - only show for browse tab */}
      {currentTab === 'browse' && (
        <div className="fixed bottom-4 right-4 z-30">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => updateFilters({ tab: 'admin' })}
            className="bg-gray-50 hover:bg-gray-100 text-xs text-muted-foreground border border-gray-200 shadow-sm"
            title="Admin panel for content quality review"
          >
            <Settings className="h-3 w-3 mr-1" />
            Admin
          </Button>
        </div>
      )}
    </div>
  );
}