'use client';

import React from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  HomeIcon,
  SparklesIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftRightIcon,
  EyeIcon,
  ChartBarIcon,
  BeakerIcon,
  Cog6ToothIcon,
  EnvelopeIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

export type TabType = 'browse' | 'recommended' | 'search' | 'ask' | 'spotlight' | 'analytics' | 'experiments' | 'email';

interface NavigationItem {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  tab: TabType;
  badge?: string;
  description: string;
}

const navigationItems: NavigationItem[] = [
  {
    name: 'Browse',
    icon: HomeIcon,
    tab: 'browse',
    description: 'Browse all articles and feeds',
  },
  {
    name: 'Recommended',
    icon: SparklesIcon,
    tab: 'recommended',
    badge: 'AI',
    description: 'Personalized recommendations',
  },
  {
    name: 'Search',
    icon: MagnifyingGlassIcon,
    tab: 'search',
    description: 'Semantic search with filters',
  },
  {
    name: 'Ask AI',
    icon: ChatBubbleLeftRightIcon,
    tab: 'ask',
    badge: 'GPT',
    description: 'Ask questions about your content',
  },
  {
    name: 'Spotlight',
    icon: EyeIcon,
    tab: 'spotlight',
    description: 'Featured and trending content',
  },
  {
    name: 'Email',
    icon: EnvelopeIcon,
    tab: 'email',
    badge: 'New',
    description: 'Newsletter and email content',
  },
  {
    name: 'Analytics',
    icon: ChartBarIcon,
    tab: 'analytics',
    description: 'User insights and behavior',
  },
  {
    name: 'Experiments',
    icon: BeakerIcon,
    tab: 'experiments',
    badge: 'A/B',
    description: 'A/B testing and optimization',
  },
];

interface SidebarProps {
  currentTab: TabType;
  onTabChange: (tab: TabType) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  isOpen,
  onClose,
}) => {
  const handleNavClick = (tab: TabType) => {
    onTabChange(tab);
    onClose(); // Close mobile sidebar after selection
  };

  const SidebarContent = (
    <div className="flex h-full flex-col">
      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigationItems.map((item) => {
          const isActive = currentTab === item.tab;
          return (
            <button
              key={item.name}
              onClick={() => handleNavClick(item.tab)}
              className={cn(
                'group flex w-full items-center rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
              )}
            >
              <item.icon
                className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive
                    ? 'text-blue-500 dark:text-blue-400'
                    : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300'
                )}
              />
              <span className="flex-1">{item.name}</span>
              {item.badge && (
                <Badge
                  variant={isActive ? 'default' : 'secondary'}
                  className="ml-2 text-xs"
                >
                  {item.badge}
                </Badge>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-3">
        <button className="group flex w-full items-center rounded-lg px-3 py-2 text-left text-sm font-medium text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors">
          <Cog6ToothIcon className="mr-3 h-5 w-5 flex-shrink-0 text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300" />
          Settings
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
        <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 pt-16">
          {SidebarContent}
        </div>
      </div>

      {/* Mobile Sidebar */}
      <Transition show={isOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50 lg:hidden" onClose={onClose}>
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-gray-900/80" />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
                <Transition.Child
                  as={Fragment}
                  enter="ease-in-out duration-300"
                  enterFrom="opacity-0"
                  enterTo="opacity-100"
                  leave="ease-in-out duration-300"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                    <button
                      type="button"
                      className="-m-2.5 p-2.5"
                      onClick={onClose}
                    >
                      <span className="sr-only">Close sidebar</span>
                      <XMarkIcon className="h-6 w-6 text-white" />
                    </button>
                  </div>
                </Transition.Child>

                <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white dark:bg-gray-900 pt-16">
                  {SidebarContent}
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </>
  );
};