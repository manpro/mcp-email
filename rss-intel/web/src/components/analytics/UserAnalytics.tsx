'use client';

import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  EyeIcon, 
  HeartIcon, 
  ClockIcon,
  TrendingUpIcon,
  UserIcon,
  TagIcon,
  NewspaperIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '@/contexts/AuthContext';
import { Badge } from '@/components/ui/badge';

interface UserStats {
  total_articles_read: number;
  total_reading_time_minutes: number;
  favorite_topics: Array<{ topic: string; count: number; }>;
  preferred_sources: Array<{ source: string; count: number; }>;
  reading_streak_days: number;
  articles_this_week: number;
  engagement_score: number;
  personalization_accuracy: number;
}

interface ReadingPattern {
  hour: number;
  count: number;
}

export const UserAnalytics: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [readingPatterns, setReadingPatterns] = useState<ReadingPattern[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      if (!isAuthenticated || !user) return;

      try {
        const response = await fetch('/api/proxy/users/analytics', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          setStats(data.stats);
          setReadingPatterns(data.reading_patterns || []);
        }
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
        // Mock data for demonstration
        setStats({
          total_articles_read: 1247,
          total_reading_time_minutes: 18640,
          favorite_topics: [
            { topic: 'AI & Machine Learning', count: 342 },
            { topic: 'Web Development', count: 285 },
            { topic: 'Cybersecurity', count: 178 },
            { topic: 'Blockchain', count: 134 },
            { topic: 'Cloud Computing', count: 98 }
          ],
          preferred_sources: [
            { source: 'TechCrunch', count: 156 },
            { source: 'Hacker News', count: 143 },
            { source: 'MIT Technology Review', count: 89 },
            { source: 'Ars Technica', count: 76 },
            { source: 'The Verge', count: 67 }
          ],
          reading_streak_days: 23,
          articles_this_week: 47,
          engagement_score: 8.7,
          personalization_accuracy: 92.4
        });
        
        // Mock reading patterns (24-hour format)
        const patterns: ReadingPattern[] = [];
        for (let hour = 0; hour < 24; hour++) {
          const baseCount = hour >= 7 && hour <= 22 ? Math.floor(Math.random() * 20) + 5 : Math.floor(Math.random() * 5);
          patterns.push({ hour, count: baseCount });
        }
        setReadingPatterns(patterns);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [isAuthenticated, user]);

  const formatReadingTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  const getEngagementColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400';
    if (score >= 6) return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400';
    return 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400';
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 90) return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400';
    if (accuracy >= 75) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400';
    return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400';
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <UserIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Sign In Required</h2>
        <p className="text-gray-600 dark:text-gray-400">Please sign in to view your reading analytics.</p>
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Reading Analytics</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Insights into your reading habits and preferences
          </p>
        </div>
        <Badge variant="secondary" className="mt-2 sm:mt-0">
          <ClockIcon className="w-4 h-4 mr-1" />
          Last updated: now
        </Badge>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <NewspaperIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Articles Read</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_articles_read?.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <ClockIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Reading Time</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats ? formatReadingTime(stats.total_reading_time_minutes) : '0h 0m'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
              <TrendingUpIcon className="h-6 w-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Reading Streak</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.reading_streak_days} days</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <EyeIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">This Week</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.articles_this_week}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Engagement & Accuracy */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Engagement Score</h3>
            <Badge className={getEngagementColor(stats?.engagement_score || 0)}>
              {stats?.engagement_score?.toFixed(1)}/10
            </Badge>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${(stats?.engagement_score || 0) * 10}%` }}
            />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Based on reading time, interactions, and feedback
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">AI Accuracy</h3>
            <Badge className={getAccuracyColor(stats?.personalization_accuracy || 0)}>
              {stats?.personalization_accuracy?.toFixed(1)}%
            </Badge>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-green-500 to-blue-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${stats?.personalization_accuracy || 0}%` }}
            />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            How well our AI matches your preferences
          </p>
        </div>
      </div>

      {/* Topics & Sources */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center mb-4">
            <TagIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Favorite Topics</h3>
          </div>
          <div className="space-y-3">
            {stats?.favorite_topics?.map((topic, index) => (
              <div key={topic.topic} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-3 ${
                    index === 0 ? 'bg-blue-500' :
                    index === 1 ? 'bg-green-500' :
                    index === 2 ? 'bg-yellow-500' :
                    index === 3 ? 'bg-purple-500' : 'bg-gray-400'
                  }`} />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{topic.topic}</span>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">{topic.count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center mb-4">
            <HeartIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Preferred Sources</h3>
          </div>
          <div className="space-y-3">
            {stats?.preferred_sources?.map((source, index) => (
              <div key={source.source} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-3 ${
                    index === 0 ? 'bg-red-500' :
                    index === 1 ? 'bg-orange-500' :
                    index === 2 ? 'bg-indigo-500' :
                    index === 3 ? 'bg-pink-500' : 'bg-gray-400'
                  }`} />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{source.source}</span>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">{source.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Reading Patterns */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center mb-6">
          <ChartBarIcon className="h-5 w-5 text-gray-400 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Reading Patterns</h3>
        </div>
        <div className="h-64 flex items-end justify-between space-x-1">
          {readingPatterns.map((pattern) => {
            const maxCount = Math.max(...readingPatterns.map(p => p.count));
            const height = maxCount > 0 ? (pattern.count / maxCount) * 100 : 0;
            
            return (
              <div key={pattern.hour} className="flex flex-col items-center">
                <div 
                  className="bg-gradient-to-t from-blue-500 to-blue-300 rounded-t-sm min-w-[8px] transition-all duration-300 hover:from-blue-600 hover:to-blue-400"
                  style={{ height: `${height}%` }}
                  title={`${pattern.hour}:00 - ${pattern.count} articles`}
                />
                <span className="text-xs text-gray-500 dark:text-gray-400 mt-2 rotate-45 origin-bottom">
                  {pattern.hour.toString().padStart(2, '0')}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-4 text-center">
          Articles read by hour (24-hour format)
        </p>
      </div>
    </div>
  );
};