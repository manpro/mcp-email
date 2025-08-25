'use client';

import React, { useState, useEffect } from 'react';
import {
  Beaker,
  Play,
  Pause,
  Square,
  BarChart3,
  Users,
  TrendingUp,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface ABTest {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'running' | 'paused' | 'completed';
  variant_a: {
    name: string;
    description: string;
    users: number;
    conversions: number;
    conversion_rate: number;
  };
  variant_b: {
    name: string;
    description: string;
    users: number;
    conversions: number;
    conversion_rate: number;
  };
  start_date: string;
  end_date?: string;
  significance: number;
  confidence_interval: number;
  winner?: 'A' | 'B' | null;
  traffic_split: number;
  total_users: number;
  created_by: string;
  created_at: string;
}

export const ABTestManager: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [tests, setTests] = useState<ABTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTest, setSelectedTest] = useState<ABTest | null>(null);

  useEffect(() => {
    const fetchTests = async () => {
      if (!isAuthenticated || !user) return;

      try {
        const response = await fetch('/api/proxy/experiments', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          setTests(data.experiments || []);
        }
      } catch (error) {
        console.error('Failed to fetch experiments:', error);
        // Mock data for demonstration
        setTests([
          {
            id: '1',
            name: 'Personalized Feed Algorithm',
            description: 'Testing improved ML model for article recommendations',
            status: 'running',
            variant_a: {
              name: 'Current Algorithm',
              description: 'Existing collaborative filtering',
              users: 1247,
              conversions: 892,
              conversion_rate: 71.5
            },
            variant_b: {
              name: 'Enhanced ML Model',
              description: 'Deep learning with user embeddings',
              users: 1289,
              conversions: 1034,
              conversion_rate: 80.2
            },
            start_date: '2024-01-15',
            significance: 95.7,
            confidence_interval: 2.3,
            winner: 'B',
            traffic_split: 50,
            total_users: 2536,
            created_by: 'micke',
            created_at: '2024-01-10'
          },
          {
            id: '2',
            name: 'Mobile Interface Layout',
            description: 'Comparing card vs list view for mobile users',
            status: 'running',
            variant_a: {
              name: 'Card View',
              description: 'Traditional card layout',
              users: 892,
              conversions: 445,
              conversion_rate: 49.9
            },
            variant_b: {
              name: 'List View',
              description: 'Compact list layout',
              users: 907,
              conversions: 507,
              conversion_rate: 55.9
            },
            start_date: '2024-01-20',
            significance: 87.2,
            confidence_interval: 4.1,
            traffic_split: 50,
            total_users: 1799,
            created_by: 'micke',
            created_at: '2024-01-18'
          },
          {
            id: '3',
            name: 'Email Newsletter Frequency',
            description: 'Testing optimal newsletter delivery frequency',
            status: 'completed',
            variant_a: {
              name: 'Daily Digest',
              description: 'Daily summary emails',
              users: 756,
              conversions: 234,
              conversion_rate: 31.0
            },
            variant_b: {
              name: 'Weekly Digest',
              description: 'Weekly comprehensive emails',
              users: 744,
              conversions: 298,
              conversion_rate: 40.1
            },
            start_date: '2023-12-01',
            end_date: '2024-01-01',
            significance: 98.3,
            confidence_interval: 1.8,
            winner: 'B',
            traffic_split: 50,
            total_users: 1500,
            created_by: 'micke',
            created_at: '2023-11-28'
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchTests();
  }, [isAuthenticated, user]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'completed':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Play className="h-4 w-4" />;
      case 'paused':
        return <Pause className="h-4 w-4" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getWinnerColor = (winner: string | null) => {
    if (winner === 'A') return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400';
    if (winner === 'B') return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400';
    return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20 dark:text-gray-400';
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <Beaker className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Sign In Required</h2>
        <p className="text-gray-600 dark:text-gray-400">Please sign in to manage A/B experiments.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">A/B Experiments</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage and monitor your A/B testing campaigns
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex gap-3">
          <Button variant="outline" size="sm">
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </Button>
          <Button size="sm">
            <Beaker className="w-4 h-4 mr-2" />
            New Experiment
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <Beaker className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Tests</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{tests.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <Play className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Running</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {tests.filter(t => t.status === 'running').length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Users</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {tests.reduce((sum, test) => sum + test.total_users, 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              <TrendingUp className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Win Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {Math.round((tests.filter(t => t.winner).length / tests.length) * 100)}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Experiments List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Active Experiments</h3>
        </div>
        
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {tests.map((test) => (
            <div key={test.id} className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white">{test.name}</h4>
                    <Badge className={getStatusColor(test.status)}>
                      {getStatusIcon(test.status)}
                      <span className="ml-1 capitalize">{test.status}</span>
                    </Badge>
                    {test.winner && (
                      <Badge className={getWinnerColor(test.winner)}>
                        Winner: Variant {test.winner}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{test.description}</p>
                  
                  {/* Variant Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium text-gray-900 dark:text-white">Variant A: {test.variant_a.name}</h5>
                        {test.winner === 'A' && <CheckCircle className="h-5 w-5 text-green-500" />}
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">{test.variant_a.description}</p>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>
                          <p className="text-gray-500 dark:text-gray-400">Users</p>
                          <p className="font-semibold text-gray-900 dark:text-white">{test.variant_a.users.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400">Conversions</p>
                          <p className="font-semibold text-gray-900 dark:text-white">{test.variant_a.conversions}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400">Rate</p>
                          <p className="font-semibold text-blue-600 dark:text-blue-400">{test.variant_a.conversion_rate}%</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium text-gray-900 dark:text-white">Variant B: {test.variant_b.name}</h5>
                        {test.winner === 'B' && <CheckCircle className="h-5 w-5 text-green-500" />}
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">{test.variant_b.description}</p>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>
                          <p className="text-gray-500 dark:text-gray-400">Users</p>
                          <p className="font-semibold text-gray-900 dark:text-white">{test.variant_b.users.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400">Conversions</p>
                          <p className="font-semibold text-gray-900 dark:text-white">{test.variant_b.conversions}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400">Rate</p>
                          <p className="font-semibold text-green-600 dark:text-green-400">{test.variant_b.conversion_rate}%</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <span>Significance: {test.significance}%</span>
                    <span>Confidence: ±{test.confidence_interval}%</span>
                    <span>Started: {new Date(test.start_date).toLocaleDateString()}</span>
                    {test.end_date && <span>Ended: {new Date(test.end_date).toLocaleDateString()}</span>}
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-4 lg:mt-0 lg:ml-6 flex gap-2">
                  <Button variant="outline" size="sm">
                    <BarChart3 className="w-4 h-4 mr-1" />
                    Details
                  </Button>
                  {test.status === 'running' && (
                    <Button variant="outline" size="sm">
                      <Pause className="w-4 h-4 mr-1" />
                      Pause
                    </Button>
                  )}
                  {test.status === 'paused' && (
                    <Button variant="outline" size="sm">
                      <Play className="w-4 h-4 mr-1" />
                      Resume
                    </Button>
                  )}
                  {test.status === 'running' && (
                    <Button variant="destructive" size="sm">
                      <Square className="w-4 h-4 mr-1" />
                      Stop
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};