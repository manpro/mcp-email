'use client';

import React, { useState, useEffect } from 'react';
import {
  EnvelopeIcon,
  InboxArrowDownIcon,
  FolderIcon,
  TagIcon,
  StarIcon,
  EyeIcon,
  EyeSlashIcon,
  ArchiveBoxIcon,
  TrashIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  CalendarIcon,
  ClockIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '@/contexts/AuthContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface EmailNewsletter {
  id: string;
  subject: string;
  sender: string;
  sender_name: string;
  excerpt: string;
  content: string;
  received_date: string;
  is_read: boolean;
  is_starred: boolean;
  is_archived: boolean;
  tags: string[];
  newsletter_type: 'tech' | 'business' | 'science' | 'general';
  reading_time_minutes: number;
  images: string[];
  links_count: number;
  unsubscribe_link?: string;
}

interface NewsletterSubscription {
  id: string;
  email: string;
  name: string;
  description: string;
  sender: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'irregular';
  is_active: boolean;
  last_email_date?: string;
  total_emails: number;
  category: string;
  tags: string[];
}

type ViewType = 'inbox' | 'unread' | 'starred' | 'archived' | 'subscriptions';
type SortType = 'date' | 'sender' | 'subject' | 'reading_time';

export const EmailClient: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [emails, setEmails] = useState<EmailNewsletter[]>([]);
  const [subscriptions, setSubscriptions] = useState<NewsletterSubscription[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<EmailNewsletter | null>(null);
  const [currentView, setCurrentView] = useState<ViewType>('inbox');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortType>('date');
  const [loading, setLoading] = useState(true);
  const [showAddSubscription, setShowAddSubscription] = useState(false);

  useEffect(() => {
    const fetchEmails = async () => {
      if (!isAuthenticated || !user) return;

      try {
        const response = await fetch('/api/proxy/emails/newsletters', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          setEmails(data.emails || []);
          setSubscriptions(data.subscriptions || []);
        }
      } catch (error) {
        console.error('Failed to fetch emails:', error);
        // Mock data for demonstration
        setEmails([
          {
            id: '1',
            subject: 'Weekly Tech Roundup: AI Breakthrough & Quantum Computing',
            sender: 'newsletter@techcrunch.com',
            sender_name: 'TechCrunch Weekly',
            excerpt: 'This week\'s biggest stories include a major AI breakthrough from OpenAI, quantum computing advances, and the latest in startup funding...',
            content: '<html><body><h1>Weekly Tech Roundup</h1><p>This week has been exciting...</p></body></html>',
            received_date: '2024-01-25T10:30:00Z',
            is_read: false,
            is_starred: true,
            is_archived: false,
            tags: ['technology', 'weekly', 'ai'],
            newsletter_type: 'tech',
            reading_time_minutes: 8,
            images: ['https://example.com/tech1.jpg', 'https://example.com/tech2.jpg'],
            links_count: 12
          },
          {
            id: '2',
            subject: 'Morning Brew: Market Updates & Business News',
            sender: 'crew@morningbrew.com',
            sender_name: 'Morning Brew',
            excerpt: 'Markets opened strong today with tech stocks leading gains. Plus, the latest on Tesla\'s earnings and crypto regulatory news...',
            content: '<html><body><h1>Morning Brew</h1><p>Good morning! Here\'s what you need to know...</p></body></html>',
            received_date: '2024-01-25T08:00:00Z',
            is_read: true,
            is_starred: false,
            is_archived: false,
            tags: ['business', 'daily', 'finance'],
            newsletter_type: 'business',
            reading_time_minutes: 5,
            images: ['https://example.com/biz1.jpg'],
            links_count: 8
          },
          {
            id: '3',
            subject: 'Science Digest: New Climate Research & Space Discoveries',
            sender: 'editor@naturenews.com',
            sender_name: 'Nature News',
            excerpt: 'Latest climate research shows promising carbon capture methods, while NASA announces new exoplanet discoveries...',
            content: '<html><body><h1>Science Digest</h1><p>Recent scientific breakthroughs...</p></body></html>',
            received_date: '2024-01-24T15:45:00Z',
            is_read: false,
            is_starred: false,
            is_archived: false,
            tags: ['science', 'climate', 'space'],
            newsletter_type: 'science',
            reading_time_minutes: 12,
            images: [],
            links_count: 6
          }
        ]);

        setSubscriptions([
          {
            id: '1',
            email: 'newsletter@techcrunch.com',
            name: 'TechCrunch Weekly',
            description: 'Weekly roundup of the biggest tech news and startup stories',
            sender: 'TechCrunch',
            frequency: 'weekly',
            is_active: true,
            last_email_date: '2024-01-25T10:30:00Z',
            total_emails: 52,
            category: 'Technology',
            tags: ['tech', 'startups', 'news']
          },
          {
            id: '2',
            email: 'crew@morningbrew.com',
            name: 'Morning Brew',
            description: 'Daily business and finance news delivered with wit',
            sender: 'Morning Brew',
            frequency: 'daily',
            is_active: true,
            last_email_date: '2024-01-25T08:00:00Z',
            total_emails: 365,
            category: 'Business',
            tags: ['business', 'finance', 'daily']
          },
          {
            id: '3',
            email: 'editor@naturenews.com',
            name: 'Nature News',
            description: 'Latest scientific research and discoveries',
            sender: 'Nature',
            frequency: 'weekly',
            is_active: true,
            last_email_date: '2024-01-24T15:45:00Z',
            total_emails: 48,
            category: 'Science',
            tags: ['science', 'research', 'nature']
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchEmails();
  }, [isAuthenticated, user]);

  const getFilteredEmails = () => {
    let filtered = [...emails];

    // Apply view filter
    switch (currentView) {
      case 'unread':
        filtered = filtered.filter(email => !email.is_read);
        break;
      case 'starred':
        filtered = filtered.filter(email => email.is_starred);
        break;
      case 'archived':
        filtered = filtered.filter(email => email.is_archived);
        break;
      case 'inbox':
      default:
        filtered = filtered.filter(email => !email.is_archived);
        break;
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(email =>
        email.subject.toLowerCase().includes(query) ||
        email.sender_name.toLowerCase().includes(query) ||
        email.excerpt.toLowerCase().includes(query) ||
        email.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'sender':
          return a.sender_name.localeCompare(b.sender_name);
        case 'subject':
          return a.subject.localeCompare(b.subject);
        case 'reading_time':
          return b.reading_time_minutes - a.reading_time_minutes;
        case 'date':
        default:
          return new Date(b.received_date).getTime() - new Date(a.received_date).getTime();
      }
    });

    return filtered;
  };

  const toggleEmailRead = (emailId: string) => {
    setEmails(prev => prev.map(email =>
      email.id === emailId ? { ...email, is_read: !email.is_read } : email
    ));
  };

  const toggleEmailStar = (emailId: string) => {
    setEmails(prev => prev.map(email =>
      email.id === emailId ? { ...email, is_starred: !email.is_starred } : email
    ));
  };

  const archiveEmail = (emailId: string) => {
    setEmails(prev => prev.map(email =>
      email.id === emailId ? { ...email, is_archived: true } : email
    ));
  };

  const getNewsletterTypeColor = (type: string) => {
    switch (type) {
      case 'tech':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400';
      case 'business':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'science':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const getFrequencyColor = (frequency: string) => {
    switch (frequency) {
      case 'daily':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      case 'weekly':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'monthly':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Sign In Required</h2>
        <p className="text-gray-600 dark:text-gray-400">Please sign in to access your email newsletters.</p>
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

  const filteredEmails = getFilteredEmails();
  const unreadCount = emails.filter(e => !e.is_read && !e.is_archived).length;

  return (
    <div className="flex h-[calc(100vh-8rem)] bg-white dark:bg-gray-900">
      {/* Sidebar */}
      <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Email</h2>
            <Button size="sm" onClick={() => setShowAddSubscription(true)}>
              <PlusIcon className="h-4 w-4" />
            </Button>
          </div>
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search emails..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 text-sm"
            />
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto p-3">
          <div className="space-y-1">
            <button
              onClick={() => setCurrentView('inbox')}
              className={`w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors ${
                currentView === 'inbox'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <InboxArrowDownIcon className="h-4 w-4 mr-3" />
              Inbox
              {unreadCount > 0 && (
                <Badge variant="secondary" className="ml-auto text-xs">
                  {unreadCount}
                </Badge>
              )}
            </button>

            <button
              onClick={() => setCurrentView('unread')}
              className={`w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors ${
                currentView === 'unread'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <EyeSlashIcon className="h-4 w-4 mr-3" />
              Unread
            </button>

            <button
              onClick={() => setCurrentView('starred')}
              className={`w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors ${
                currentView === 'starred'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <StarIcon className="h-4 w-4 mr-3" />
              Starred
            </button>

            <button
              onClick={() => setCurrentView('archived')}
              className={`w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors ${
                currentView === 'archived'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <ArchiveBoxIcon className="h-4 w-4 mr-3" />
              Archived
            </button>

            <button
              onClick={() => setCurrentView('subscriptions')}
              className={`w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors ${
                currentView === 'subscriptions'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <FolderIcon className="h-4 w-4 mr-3" />
              Subscriptions
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {currentView === 'subscriptions' ? (
          /* Subscriptions View */
          <div className="flex-1 overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Newsletter Subscriptions
                </h3>
                <Button onClick={() => setShowAddSubscription(true)}>
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Add Subscription
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {subscriptions.map((subscription) => (
                  <div
                    key={subscription.id}
                    className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {subscription.name}
                      </h4>
                      <Badge className={getFrequencyColor(subscription.frequency)}>
                        {subscription.frequency}
                      </Badge>
                    </div>
                    
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      {subscription.description}
                    </p>
                    
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-3">
                      <span>{subscription.total_emails} emails</span>
                      {subscription.last_email_date && (
                        <span>
                          Last: {new Date(subscription.last_email_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap gap-1">
                      {subscription.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Email List View */
          <>
            {/* Toolbar */}
            <div className="border-b border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {filteredEmails.length} emails
                  </span>
                  {currentView === 'inbox' && unreadCount > 0 && (
                    <Badge variant="secondary">
                      {unreadCount} unread
                    </Badge>
                  )}
                </div>
                
                <div className="flex items-center gap-2">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as SortType)}
                    className="text-sm border border-gray-200 dark:border-gray-700 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="date">Sort by Date</option>
                    <option value="sender">Sort by Sender</option>
                    <option value="subject">Sort by Subject</option>
                    <option value="reading_time">Sort by Length</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Email List */}
            <div className="flex-1 overflow-y-auto">
              {filteredEmails.length === 0 ? (
                <div className="text-center py-12">
                  <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No emails found
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    {searchQuery ? 'Try adjusting your search terms.' : 'Your inbox is empty.'}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredEmails.map((email) => (
                    <div
                      key={email.id}
                      className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors ${
                        !email.is_read ? 'bg-blue-50/30 dark:bg-blue-900/10' : ''
                      }`}
                      onClick={() => setSelectedEmail(email)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className={`text-sm truncate ${
                              !email.is_read 
                                ? 'font-semibold text-gray-900 dark:text-white' 
                                : 'font-medium text-gray-700 dark:text-gray-300'
                            }`}>
                              {email.subject}
                            </h3>
                            {!email.is_read && (
                              <div className="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0" />
                            )}
                          </div>
                          
                          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                            {email.sender_name} • {new Date(email.received_date).toLocaleDateString()}
                          </p>
                          
                          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                            {email.excerpt}
                          </p>
                        </div>
                        
                        <div className="flex items-center gap-2 ml-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleEmailStar(email.id);
                            }}
                            className="text-gray-400 hover:text-yellow-500 transition-colors"
                          >
                            <StarIcon className={`h-4 w-4 ${email.is_starred ? 'fill-yellow-500 text-yellow-500' : ''}`} />
                          </button>
                          
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleEmailRead(email.id);
                            }}
                            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                          >
                            {email.is_read ? (
                              <EyeSlashIcon className="h-4 w-4" />
                            ) : (
                              <EyeIcon className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-2">
                        <Badge className={getNewsletterTypeColor(email.newsletter_type)}>
                          {email.newsletter_type}
                        </Badge>
                        
                        <Badge variant="outline">
                          <ClockIcon className="h-3 w-3 mr-1" />
                          {email.reading_time_minutes} min
                        </Badge>
                        
                        {email.tags.slice(0, 2).map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Email Reader Modal/Panel - Would implement as a separate component */}
      {selectedEmail && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {selectedEmail.subject}
                </h2>
                <Button variant="ghost" onClick={() => setSelectedEmail(null)}>
                  ✕
                </Button>
              </div>
              
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                From: {selectedEmail.sender_name} • {new Date(selectedEmail.received_date).toLocaleString()}
              </div>
              
              <div className="prose dark:prose-invert max-w-none">
                <div dangerouslySetInnerHTML={{ __html: selectedEmail.content }} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};