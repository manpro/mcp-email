'use client';

import React, { useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { LoginPage } from '@/components/auth/LoginPage';
import { useAuth } from '@/contexts/AuthContext';
import Dashboard from '@/components/Dashboard';
import { UserAnalytics } from '@/components/analytics/UserAnalytics';
import { ABTestManager } from '@/components/experiments/ABTestManager';
import { SearchInterface } from '@/components/search/SearchInterface';
import { EmailClient } from '@/components/email/EmailClient';
import { SpotlightTab } from '@/components/SpotlightTab';
import { TrendingTab } from '@/components/TrendingTab';
import { TabType } from '@/components/layout/Sidebar';
import ArticleReader from '@/components/ArticleReader';
import { Article } from '@/lib/api';

export default function Home() {
  const [currentTab, setCurrentTab] = useState<TabType>('browse');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const { isAuthenticated } = useAuth();

  // Show login page if user is not authenticated
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const renderTabContent = () => {
    switch (currentTab) {
      case 'browse':
        return <Dashboard />;
      case 'recommended':
        return <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">AI Recommendations</h2>
          <p className="text-gray-600 dark:text-gray-400">Personalized content recommendations coming soon...</p>
        </div>;
      case 'search':
        return <SearchInterface />;
      case 'ask':
        return <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Ask AI</h2>
          <p className="text-gray-600 dark:text-gray-400">Chat with your content coming soon...</p>
        </div>;
      case 'spotlight':
        return <SpotlightTab onArticleClick={setSelectedArticle} />;
      case 'email':
        return <EmailClient />;
      case 'analytics':
        return <UserAnalytics />;
      case 'experiments':
        return <ABTestManager />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <>
      <Layout currentTab={currentTab} onTabChange={setCurrentTab}>
        {renderTabContent()}
      </Layout>
      
      {selectedArticle && (
        <ArticleReader
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
        />
      )}
    </>
  );
}