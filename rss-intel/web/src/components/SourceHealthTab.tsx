import React, { useState, useEffect, useCallback } from 'react';
import { 
  AlertTriangle, Shield, Activity, TrendingDown, Clock, 
  ExternalLink, RefreshCw, Filter, X, CheckCircle, AlertCircle,
  XCircle, MinusCircle, Eye, EyeOff, Settings, BarChart3
} from 'lucide-react';

interface HealthIssue {
  issue_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  detection_time: string;
  confidence: number;
  affected_articles: number;
}

interface ProblematicSource {
  source_name: string;
  health_status: 'healthy' | 'degraded' | 'unhealthy' | 'failing';
  extraction_success_rate: number;
  content_quality_score: number;
  total_articles: number;
  last_successful_extraction: string | null;
  critical_issues: number;
  recommendations: string[];
}

interface HealthOverview {
  summary: {
    total_sources: number;
    healthy_sources: number;
    degraded_sources: number;
    unhealthy_sources: number;
    failing_sources: number;
    overall_extraction_success_rate: number;
    total_articles_analyzed: number;
  };
  health_distribution: {
    healthy: number;
    degraded: number;
    unhealthy: number;
    failing: number;
  };
  top_issues: Array<{
    source: string;
    issue_type: string;
    severity: string;
    description: string;
    confidence: number;
  }>;
  problematic_sources: Array<{
    source: string;
    health_status: string;
    extraction_success_rate: number;
    content_quality_score: number;
    issue_count: number;
    critical_issues: number;
  }>;
  recommendations: string[];
}

const SourceHealthTab: React.FC = () => {
  const [overview, setOverview] = useState<HealthOverview | null>(null);
  const [problematicSources, setProblematicSources] = useState<ProblematicSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  
  const [filters, setFilters] = useState({
    severity: 'medium',
    status: 'all',
    days: 7
  });
  
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [sourceDetails, setSourceDetails] = useState<any>(null);
  const [showOnlyProblematic, setShowOnlyProblematic] = useState(true);

  const fetchHealthOverview = useCallback(async () => {
    try {
      const response = await fetch(`/api/proxy/api/source-health/overview?days=${filters.days}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch overview: ${response.statusText}`);
      }
      const data = await response.json();
      setOverview(data.overview);
    } catch (err) {
      console.error('Error fetching health overview:', err);
      setError(err instanceof Error ? err.message : 'Failed to load overview');
    }
  }, [filters.days]);

  const fetchProblematicSources = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/proxy/api/source-health/problematic?days=${filters.days}&min_severity=${filters.severity}&limit=100`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch sources: ${response.statusText}`);
      }
      const data = await response.json();
      setProblematicSources(data.problematic_sources);
    } catch (err) {
      console.error('Error fetching problematic sources:', err);
      setError(err instanceof Error ? err.message : 'Failed to load sources');
    }
  }, [filters.days, filters.severity]);

  const fetchSourceDetails = useCallback(async (sourceName: string) => {
    try {
      const response = await fetch(
        `/api/proxy/api/source-health/${encodeURIComponent(sourceName)}?days=${filters.days}`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch source details: ${response.statusText}`);
      }
      const data = await response.json();
      setSourceDetails(data);
    } catch (err) {
      console.error('Error fetching source details:', err);
    }
  }, [filters.days]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        await Promise.all([fetchHealthOverview(), fetchProblematicSources()]);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [fetchHealthOverview, fetchProblematicSources]);

  useEffect(() => {
    if (selectedSource) {
      fetchSourceDetails(selectedSource);
    }
  }, [selectedSource, fetchSourceDetails]);

  const triggerAnalysis = async () => {
    setAnalyzing(true);
    try {
      const response = await fetch(`/api/proxy/api/source-health/analyze?days=${filters.days}`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error('Failed to trigger analysis');
      }
      // Refresh data after analysis
      setTimeout(() => {
        fetchHealthOverview();
        fetchProblematicSources();
      }, 2000);
    } catch (err) {
      console.error('Error triggering analysis:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const disableSource = async (sourceName: string, reason: string) => {
    try {
      const response = await fetch(
        `/api/proxy/api/source-health/sources/${encodeURIComponent(sourceName)}?reason=${encodeURIComponent(reason)}`,
        { method: 'DELETE' }
      );
      if (!response.ok) {
        throw new Error('Failed to disable source');
      }
      // Refresh data
      fetchProblematicSources();
    } catch (err) {
      console.error('Error disabling source:', err);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'unhealthy':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />;
      case 'failing':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <MinusCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading && !overview) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Activity className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-pulse" />
          <h2 className="text-xl font-semibold text-gray-700">Analyzing source health...</h2>
          <p className="text-gray-500 mt-2">Checking content extraction and quality</p>
        </div>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-700">Unable to load health data</h2>
          <p className="text-gray-500 mt-2">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Shield className="w-8 h-8 text-red-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Source Health Monitor</h1>
              <p className="text-gray-600">Monitor RSS feeds for extraction issues and content problems</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={triggerAnalysis}
              disabled={analyzing}
              className={`flex items-center space-x-2 px-4 py-2 bg-white rounded-lg border transition-all ${
                analyzing 
                  ? 'border-gray-200 text-gray-400 cursor-not-allowed' 
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <RefreshCw className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Analyzing...' : 'Analyze Now'}</span>
            </button>
            <button
              onClick={() => setShowOnlyProblematic(!showOnlyProblematic)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-all ${
                showOnlyProblematic
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {showOnlyProblematic ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              <span>{showOnlyProblematic ? 'Show All' : 'Problems Only'}</span>
            </button>
          </div>
        </div>

        {/* Overview Stats */}
        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="bg-white bg-opacity-70 rounded-lg p-3">
              <div className="text-2xl font-bold text-green-600">{overview.summary.healthy_sources}</div>
              <div className="text-sm text-gray-600">Healthy Sources</div>
            </div>
            <div className="bg-white bg-opacity-70 rounded-lg p-3">
              <div className="text-2xl font-bold text-red-600">{overview.summary.failing_sources}</div>
              <div className="text-sm text-gray-600">Failing Sources</div>
            </div>
            <div className="bg-white bg-opacity-70 rounded-lg p-3">
              <div className="text-2xl font-bold text-blue-600">
                {Math.round(overview.summary.overall_extraction_success_rate * 100)}%
              </div>
              <div className="text-sm text-gray-600">Success Rate</div>
            </div>
            <div className="bg-white bg-opacity-70 rounded-lg p-3">
              <div className="text-2xl font-bold text-purple-600">{overview.summary.total_sources}</div>
              <div className="text-sm text-gray-600">Total Sources</div>
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={filters.severity}
              onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
              className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">Low Severity+</option>
              <option value="medium">Medium Severity+</option>
              <option value="high">High Severity+</option>
              <option value="critical">Critical Only</option>
            </select>
            <select
              value={filters.days}
              onChange={(e) => setFilters(prev => ({ ...prev, days: parseInt(e.target.value) }))}
              className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>Last 24 hours</option>
              <option value={3}>Last 3 days</option>
              <option value={7}>Last week</option>
              <option value={14}>Last 2 weeks</option>
              <option value={30}>Last month</option>
            </select>
          </div>
          <span className="text-sm text-gray-500">
            {problematicSources.length} problematic sources found
          </span>
        </div>
      </div>

      {/* Problematic Sources List */}
      {problematicSources.length === 0 ? (
        <div className="text-center py-12">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-700">All sources are healthy!</h3>
          <p className="text-gray-500 mt-2">No sources match your current filter criteria</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Problematic Sources</h2>
          </div>
          
          <div className="divide-y divide-gray-200">
            {problematicSources.map((source) => (
              <div key={source.source_name} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {getStatusIcon(source.health_status)}
                      <h3 className="text-lg font-medium text-gray-900">{source.source_name}</h3>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        source.health_status === 'failing' ? 'bg-red-100 text-red-800' :
                        source.health_status === 'unhealthy' ? 'bg-orange-100 text-orange-800' :
                        source.health_status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {source.health_status}
                      </span>
                      {source.critical_issues > 0 && (
                        <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-full">
                          {source.critical_issues} critical issues
                        </span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                      <div>
                        <div className="text-sm text-gray-500">Success Rate</div>
                        <div className={`text-lg font-medium ${
                          source.extraction_success_rate >= 0.8 ? 'text-green-600' :
                          source.extraction_success_rate >= 0.6 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {Math.round(source.extraction_success_rate * 100)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Content Quality</div>
                        <div className={`text-lg font-medium ${
                          source.content_quality_score >= 0.7 ? 'text-green-600' :
                          source.content_quality_score >= 0.4 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {Math.round(source.content_quality_score * 100)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Articles</div>
                        <div className="text-lg font-medium text-gray-900">{source.total_articles}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Last Success</div>
                        <div className="text-sm text-gray-700">{formatDate(source.last_successful_extraction)}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => setSelectedSource(source.source_name)}
                      className="flex items-center space-x-1 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
                    >
                      <BarChart3 className="w-4 h-4" />
                      <span>Details</span>
                    </button>
                    {source.health_status === 'failing' && (
                      <button
                        onClick={() => disableSource(source.source_name, 'Too many extraction failures')}
                        className="flex items-center space-x-1 px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Disable</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source Detail Modal */}
      {selectedSource && sourceDetails && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(sourceDetails.health_status)}
                  <h2 className="text-xl font-bold text-gray-900">{selectedSource}</h2>
                  <span className={`px-2 py-1 text-sm font-medium rounded-full ${
                    sourceDetails.health_status === 'failing' ? 'bg-red-100 text-red-800' :
                    sourceDetails.health_status === 'unhealthy' ? 'bg-orange-100 text-orange-800' :
                    sourceDetails.health_status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {sourceDetails.health_status}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedSource(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            <div className="p-6">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Total Articles</div>
                  <div className="text-2xl font-bold text-gray-900">{sourceDetails.metrics.total_articles}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Success Rate</div>
                  <div className={`text-2xl font-bold ${
                    sourceDetails.metrics.extraction_success_rate >= 0.8 ? 'text-green-600' :
                    sourceDetails.metrics.extraction_success_rate >= 0.6 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {Math.round(sourceDetails.metrics.extraction_success_rate * 100)}%
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Quality Score</div>
                  <div className={`text-2xl font-bold ${
                    sourceDetails.metrics.content_quality_score >= 0.7 ? 'text-green-600' :
                    sourceDetails.metrics.content_quality_score >= 0.4 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {Math.round(sourceDetails.metrics.content_quality_score * 100)}%
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Cloudflare Blocks</div>
                  <div className="text-2xl font-bold text-orange-600">{sourceDetails.metrics.cloudflare_blocks}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Paywall Hits</div>
                  <div className="text-2xl font-bold text-purple-600">{sourceDetails.metrics.paywall_hits}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-sm text-gray-500">Spam Articles</div>
                  <div className="text-2xl font-bold text-red-600">{sourceDetails.metrics.spam_articles}</div>
                </div>
              </div>

              {/* Issues */}
              {sourceDetails.issues.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Detected Issues</h3>
                  <div className="space-y-2">
                    {sourceDetails.issues.map((issue: HealthIssue, index: number) => (
                      <div key={index} className={`p-3 border rounded-lg ${getSeverityColor(issue.severity)}`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium">{issue.issue_type.replace('_', ' ').toUpperCase()}</div>
                            <div className="text-sm mt-1">{issue.description}</div>
                          </div>
                          <div className="text-sm">
                            {Math.round(issue.confidence * 100)}% confidence
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Failures */}
              {sourceDetails.recent_failures.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Recent Failures</h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {sourceDetails.recent_failures.map((failure: any, index: number) => (
                      <div key={index} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="text-sm font-medium text-red-800">{failure.failure_reason}</div>
                            <div className="text-xs text-red-600 mt-1">{failure.error_message}</div>
                            <a 
                              href={failure.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:text-blue-800 flex items-center mt-1"
                            >
                              <ExternalLink className="w-3 h-3 mr-1" />
                              {failure.url}
                            </a>
                          </div>
                          <div className="text-xs text-red-500 ml-4">
                            HTTP {failure.http_status || 'N/A'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Recommendations */}
      {overview && overview.recommendations.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-start space-x-3">
            <Settings className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-blue-900 mb-2">Recommendations</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                {overview.recommendations.map((rec, index) => (
                  <li key={index}>• {rec}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SourceHealthTab;