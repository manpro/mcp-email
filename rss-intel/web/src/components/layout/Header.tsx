'use client';

import React, { useState } from 'react';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  Menu as MenuIcon,
  X,
  User,
  LogOut,
  Settings,
  BarChart3,
  Beaker,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { LoginModal } from '@/components/auth/LoginModal';
import { cn } from '@/lib/utils';

interface HeaderProps {
  onToggleMenu: () => void;
  isMenuOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onToggleMenu, isMenuOpen }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  const handleLogout = () => {
    logout();
  };

  return (
    <>
      <header className="sticky top-0 z-40 w-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-gray-200 dark:border-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Left side - Mobile menu button & Logo */}
            <div className="flex items-center gap-4">
              <button
                onClick={onToggleMenu}
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors lg:hidden"
                aria-label="Open menu"
              >
                {isMenuOpen ? (
                  <X className="h-6 w-6" />
                ) : (
                  <MenuIcon className="h-6 w-6" />
                )}
              </button>

              {/* Logo */}
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-8 h-8 bg-blue-600 rounded-lg">
                  <span className="text-white font-bold text-sm">RI</span>
                </div>
                <div className="hidden sm:block">
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                    RSS Intelligence
                  </h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    AI-Powered Content Discovery
                  </p>
                </div>
              </div>
            </div>

            {/* Right side - User menu */}
            <div className="flex items-center gap-3">
              {/* User status badge */}
              {isAuthenticated && user && (
                <Badge variant="secondary" className="hidden sm:flex">
                  <User className="w-3 h-3 mr-1" />
                  {user.username}
                </Badge>
              )}

              {/* User menu */}
              {isAuthenticated ? (
                <Menu as="div" className="relative">
                  <Menu.Button className="flex items-center gap-2 p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                    <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                    <span className="hidden sm:block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {user?.username || 'User'}
                    </span>
                  </Menu.Button>

                  <Transition
                    as={Fragment}
                    enter="transition ease-out duration-100"
                    enterFrom="transform opacity-0 scale-95"
                    enterTo="transform opacity-100 scale-100"
                    leave="transition ease-in duration-75"
                    leaveFrom="transform opacity-100 scale-100"
                    leaveTo="transform opacity-0 scale-95"
                  >
                    <Menu.Items className="absolute right-0 mt-2 w-56 origin-top-right divide-y divide-gray-100 dark:divide-gray-800 rounded-lg bg-white dark:bg-gray-900 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                      {/* User info */}
                      <div className="px-4 py-3">
                        <p className="text-sm text-gray-900 dark:text-white font-medium">
                          {user?.username}
                        </p>
                        {user?.email && (
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {user.email}
                          </p>
                        )}
                      </div>

                      {/* Menu items */}
                      <div className="py-1">
                        <Menu.Item>
                          {({ active }) => (
                            <button
                              className={cn(
                                'flex w-full items-center px-4 py-2 text-sm',
                                active
                                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                                  : 'text-gray-700 dark:text-gray-300'
                              )}
                            >
                              <BarChart3 className="mr-3 h-4 w-4" />
                              User Analytics
                            </button>
                          )}
                        </Menu.Item>

                        <Menu.Item>
                          {({ active }) => (
                            <button
                              className={cn(
                                'flex w-full items-center px-4 py-2 text-sm',
                                active
                                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                                  : 'text-gray-700 dark:text-gray-300'
                              )}
                            >
                              <Beaker className="mr-3 h-4 w-4" />
                              A/B Experiments
                            </button>
                          )}
                        </Menu.Item>

                        <Menu.Item>
                          {({ active }) => (
                            <button
                              className={cn(
                                'flex w-full items-center px-4 py-2 text-sm',
                                active
                                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                                  : 'text-gray-700 dark:text-gray-300'
                              )}
                            >
                              <Settings className="mr-3 h-4 w-4" />
                              Preferences
                            </button>
                          )}
                        </Menu.Item>
                      </div>

                      {/* Logout */}
                      <div className="py-1">
                        <Menu.Item>
                          {({ active }) => (
                            <button
                              onClick={handleLogout}
                              className={cn(
                                'flex w-full items-center px-4 py-2 text-sm',
                                active
                                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                                  : 'text-gray-700 dark:text-gray-300'
                              )}
                            >
                              <LogOut className="mr-3 h-4 w-4" />
                              Sign Out
                            </button>
                          )}
                        </Menu.Item>
                      </div>
                    </Menu.Items>
                  </Transition>
                </Menu>
              ) : (
                <Button
                  onClick={() => setShowLoginModal(true)}
                  variant="default"
                  size="sm"
                  className="font-medium"
                >
                  <User className="w-4 h-4 mr-2" />
                  Sign In
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Login Modal */}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
      />
    </>
  );
};