'use client';

import React, { useState } from 'react';
import { Header } from './Header';
import { Sidebar, TabType } from './Sidebar';
import { AuthProvider } from '@/contexts/AuthContext';
import { Toaster } from 'sonner';

interface LayoutProps {
  children: React.ReactNode;
  currentTab?: TabType;
  onTabChange?: (tab: TabType) => void;
}

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  currentTab = 'browse',
  onTabChange = () => {} 
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleToggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const handleCloseSidebar = () => {
    setIsSidebarOpen(false);
  };

  return (
    <AuthProvider>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        {/* Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onTabChange={onTabChange}
          isOpen={isSidebarOpen}
          onClose={handleCloseSidebar}
        />

        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden lg:pl-64">
          {/* Header */}
          <Header 
            onToggleMenu={handleToggleSidebar}
            isMenuOpen={isSidebarOpen}
          />

          {/* Main content */}
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
              {children}
            </div>
          </main>
        </div>
      </div>

      {/* Toast notifications */}
      <Toaster 
        position="bottom-right"
        toastOptions={{
          className: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700',
        }}
      />
    </AuthProvider>
  );
};