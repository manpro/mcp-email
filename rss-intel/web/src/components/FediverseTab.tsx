import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Badge } from './ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { 
  MessageSquare, 
  Hash, 
  User, 
  Server, 
  RefreshCw, 
  Plus, 
  Trash2, 
  ExternalLink,
  Heart,
  Repeat,
  Reply,
  Calendar
} from 'lucide-react'

interface FediversePost {
  id: string
  url: string
  content_preview: string
  author_username: string
  author_display_name: string
  published_at: string
  replies_count: number
  reblogs_count: number
  favourites_count: number
  tags: string[]
  instance_domain: string
}

interface FediverseSource {
  id: number
  source_type: string
  identifier: string
  title: string
  description: string
  is_active: boolean
  created_at: string
}

interface MastodonInstance {
  domain: string
  name: string
  description: string
  version: string
  user_count: number
  status_count: number
  is_alive: boolean
}

const FediverseTab: React.FC = () => {
  const [posts, setPosts] = useState<FediversePost[]>([])
  const [sources, setSources] = useState<FediverseSource[]>([])
  const [instances, setInstances] = useState<MastodonInstance[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Form states
  const [newSourceType, setNewSourceType] = useState<string>('account')
  const [newSourceIdentifier, setNewSourceIdentifier] = useState('')
  const [selectedInstance, setSelectedInstance] = useState('')
  const [newSourceDescription, setNewSourceDescription] = useState('')
  
  // View states
  const [activeView, setActiveView] = useState<'posts' | 'sources' | 'instances'>('posts')
  const [selectedHashtag, setSelectedHashtag] = useState('')
  const [selectedAccount, setSelectedAccount] = useState('')

  useEffect(() => {
    loadSources()
    loadInstances()
  }, [])

  const loadSources = async () => {
    try {
      const response = await fetch('/api/proxy/fediverse/sources')
      if (response.ok) {
        const data = await response.json()
        setSources(data.sources || [])
      }
    } catch (err) {
      console.error('Failed to load Fediverse sources:', err)
    }
  }

  const loadInstances = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/proxy/fediverse/instances')
      if (response.ok) {
        const data = await response.json()
        setInstances(data.instances || [])
      }
    } catch (err) {
      console.error('Failed to load instances:', err)
      setError('Failed to load Mastodon instances')
    } finally {
      setLoading(false)
    }
  }

  const loadHashtagPosts = async (hashtag: string, instanceDomain: string) => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`/api/proxy/fediverse/hashtag/${hashtag}?instance_domain=${instanceDomain}&limit=20`)
      
      if (response.ok) {
        const data = await response.json()
        setPosts(data.posts || [])
      } else {
        setError('Failed to load hashtag posts')
      }
    } catch (err) {
      console.error('Failed to load hashtag posts:', err)
      setError('Failed to load hashtag posts')
    } finally {
      setLoading(false)
    }
  }

  const loadAccountPosts = async (username: string, domain: string) => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`/api/proxy/fediverse/account/${username}/posts?domain=${domain}&limit=20`)
      
      if (response.ok) {
        const data = await response.json()
        setPosts(data.posts || [])
      } else {
        setError('Failed to load account posts')
      }
    } catch (err) {
      console.error('Failed to load account posts:', err)
      setError('Failed to load account posts')
    } finally {
      setLoading(false)
    }
  }

  const loadPublicTimeline = async (instanceDomain: string) => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`/api/proxy/fediverse/timeline/public?instance_domain=${instanceDomain}&limit=20`)
      
      if (response.ok) {
        const data = await response.json()
        setPosts(data.posts || [])
      } else {
        setError('Failed to load public timeline')
      }
    } catch (err) {
      console.error('Failed to load public timeline:', err)
      setError('Failed to load public timeline')
    } finally {
      setLoading(false)
    }
  }

  const addFediverseSource = async () => {
    if (!newSourceIdentifier || !selectedInstance) {
      setError('Please fill in all required fields')
      return
    }

    try {
      const response = await fetch('/api/proxy/fediverse/sources', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_type: newSourceType,
          identifier: newSourceIdentifier,
          instance_domain: selectedInstance,
          description: newSourceDescription
        })
      })

      if (response.ok) {
        setNewSourceIdentifier('')
        setNewSourceDescription('')
        loadSources()
        setError(null)
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to add source')
      }
    } catch (err) {
      console.error('Failed to add source:', err)
      setError('Failed to add source')
    }
  }

  const removeFediverseSource = async (sourceId: number) => {
    try {
      const response = await fetch(`/api/proxy/fediverse/sources/${sourceId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        loadSources()
      } else {
        setError('Failed to remove source')
      }
    } catch (err) {
      console.error('Failed to remove source:', err)
      setError('Failed to remove source')
    }
  }

  const syncFediverseSources = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/proxy/fediverse/sync', {
        method: 'POST'
      })

      if (response.ok) {
        setError(null)
        // Optionally refresh data after sync
      } else {
        setError('Failed to start sync')
      }
    } catch (err) {
      console.error('Failed to sync sources:', err)
      setError('Failed to sync sources')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString()
    } catch {
      return dateStr
    }
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`
    }
    return num.toString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Fediverse Integration</h2>
          <p className="text-gray-600">Monitor Mastodon accounts, hashtags, and instances</p>
        </div>
        
        <div className="flex space-x-2">
          <Button
            variant={activeView === 'posts' ? 'default' : 'outline'}
            onClick={() => setActiveView('posts')}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Posts
          </Button>
          <Button
            variant={activeView === 'sources' ? 'default' : 'outline'}
            onClick={() => setActiveView('sources')}
          >
            <Plus className="w-4 h-4 mr-2" />
            Sources
          </Button>
          <Button
            variant={activeView === 'instances' ? 'default' : 'outline'}
            onClick={() => setActiveView('instances')}
          >
            <Server className="w-4 h-4 mr-2" />
            Instances
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Posts View */}
      {activeView === 'posts' && (
        <div className="space-y-4">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Hashtag Search */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Search Hashtag</label>
                  <div className="flex space-x-2">
                    <Input
                      placeholder="technology, ai, programming..."
                      value={selectedHashtag}
                      onChange={(e) => setSelectedHashtag(e.target.value)}
                    />
                    <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                      <SelectTrigger className="w-48">
                        <SelectValue placeholder="Instance" />
                      </SelectTrigger>
                      <SelectContent>
                        {instances.map((instance) => (
                          <SelectItem key={instance.domain} value={instance.domain}>
                            {instance.domain}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button 
                      onClick={() => selectedHashtag && selectedInstance && loadHashtagPosts(selectedHashtag, selectedInstance)}
                      disabled={!selectedHashtag || !selectedInstance}
                    >
                      <Hash className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Account Search */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Search Account</label>
                  <div className="flex space-x-2">
                    <Input
                      placeholder="username"
                      value={selectedAccount}
                      onChange={(e) => setSelectedAccount(e.target.value)}
                    />
                    <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                      <SelectTrigger className="w-48">
                        <SelectValue placeholder="Instance" />
                      </SelectTrigger>
                      <SelectContent>
                        {instances.map((instance) => (
                          <SelectItem key={instance.domain} value={instance.domain}>
                            {instance.domain}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button 
                      onClick={() => selectedAccount && selectedInstance && loadAccountPosts(selectedAccount, selectedInstance)}
                      disabled={!selectedAccount || !selectedInstance}
                    >
                      <User className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Public Timeline */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Public Timeline</label>
                  <div className="flex space-x-2">
                    <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select Instance" />
                      </SelectTrigger>
                      <SelectContent>
                        {instances.map((instance) => (
                          <SelectItem key={instance.domain} value={instance.domain}>
                            {instance.domain}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button 
                      onClick={() => selectedInstance && loadPublicTimeline(selectedInstance)}
                      disabled={!selectedInstance}
                    >
                      <Server className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Posts List */}
          <div className="space-y-4">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="w-6 h-6 animate-spin" />
                <span className="ml-2">Loading posts...</span>
              </div>
            )}

            {posts.map((post) => (
              <Card key={post.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <div className="font-medium">{post.author_display_name}</div>
                        <div className="text-sm text-gray-500">
                          @{post.author_username}@{post.instance_domain}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <Calendar className="w-4 h-4" />
                      <span>{formatDate(post.published_at)}</span>
                      <a 
                        href={post.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="hover:text-blue-600"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 mb-3">{post.content_preview}</p>
                  
                  {post.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {post.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          #{tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    <div className="flex items-center space-x-1">
                      <Reply className="w-4 h-4" />
                      <span>{formatNumber(post.replies_count)}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Repeat className="w-4 h-4" />
                      <span>{formatNumber(post.reblogs_count)}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Heart className="w-4 h-4" />
                      <span>{formatNumber(post.favourites_count)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {!loading && posts.length === 0 && (
              <Card>
                <CardContent className="text-center py-8">
                  <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-500">No posts loaded. Search for a hashtag, account, or instance timeline above.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Sources Management View */}
      {activeView === 'sources' && (
        <div className="space-y-6">
          {/* Add New Source */}
          <Card>
            <CardHeader>
              <CardTitle>Add New Fediverse Source</CardTitle>
              <CardDescription>
                Monitor specific accounts, hashtags, or instance timelines
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Source Type</label>
                  <Select value={newSourceType} onValueChange={setNewSourceType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="account">Account</SelectItem>
                      <SelectItem value="hashtag">Hashtag</SelectItem>
                      <SelectItem value="instance">Instance Timeline</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Instance Domain</label>
                  <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select instance" />
                    </SelectTrigger>
                    <SelectContent>
                      {instances.map((instance) => (
                        <SelectItem key={instance.domain} value={instance.domain}>
                          {instance.domain}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    {newSourceType === 'account' ? 'Username' : 
                     newSourceType === 'hashtag' ? 'Hashtag (without #)' : 
                     'Instance Domain'}
                  </label>
                  <Input
                    placeholder={
                      newSourceType === 'account' ? 'username' : 
                      newSourceType === 'hashtag' ? 'technology' : 
                      'mastodon.social'
                    }
                    value={newSourceIdentifier}
                    onChange={(e) => setNewSourceIdentifier(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Description (Optional)</label>
                  <Input
                    placeholder="Brief description of this source"
                    value={newSourceDescription}
                    onChange={(e) => setNewSourceDescription(e.target.value)}
                  />
                </div>
              </div>

              <div className="mt-4">
                <Button onClick={addFediverseSource} className="mr-2">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Source
                </Button>
                <Button onClick={syncFediverseSources} variant="outline" disabled={loading}>
                  <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                  Sync All Sources
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Current Sources */}
          <Card>
            <CardHeader>
              <CardTitle>Current Sources ({sources.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {sources.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No Fediverse sources configured</p>
              ) : (
                <div className="space-y-3">
                  {sources.map((source) => (
                    <div key={source.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          {source.source_type === 'account' && <User className="w-4 h-4 text-blue-600" />}
                          {source.source_type === 'hashtag' && <Hash className="w-4 h-4 text-blue-600" />}
                          {source.source_type === 'instance' && <Server className="w-4 h-4 text-blue-600" />}
                        </div>
                        <div>
                          <div className="font-medium">{source.title}</div>
                          <div className="text-sm text-gray-500">{source.description}</div>
                          <div className="text-xs text-gray-400">
                            {source.source_type} • Added {formatDate(source.created_at)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={source.is_active ? "success" : "secondary"}>
                          {source.is_active ? "Active" : "Inactive"}
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => removeFediverseSource(source.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Instances View */}
      {activeView === 'instances' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Available Mastodon Instances</CardTitle>
              <CardDescription>
                Known Mastodon instances that can be used as sources
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                  <span className="ml-2">Loading instances...</span>
                </div>
              ) : instances.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No instances discovered</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {instances.map((instance) => (
                    <Card key={instance.domain} className="border">
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-lg">{instance.name}</CardTitle>
                          <Badge variant={instance.is_alive ? "success" : "secondary"}>
                            {instance.is_alive ? "Online" : "Offline"}
                          </Badge>
                        </div>
                        <CardDescription>{instance.domain}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-gray-600 mb-3">{instance.description}</p>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="font-medium">Version:</span>
                            <br />
                            {instance.version}
                          </div>
                          <div>
                            <span className="font-medium">Users:</span>
                            <br />
                            {formatNumber(instance.user_count)}
                          </div>
                          <div className="col-span-2">
                            <span className="font-medium">Posts:</span>
                            <br />
                            {formatNumber(instance.status_count)}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export default FediverseTab