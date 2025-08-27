"""
API Integrations Service

Integrates with external APIs to fetch content from:
- GitHub (releases, trending repositories, issues)
- HackerNews (top stories, show HN, ask HN)
- Reddit (subreddit posts, comments)
- YouTube (channel feeds, playlists)
- arXiv (research papers)

Converts API responses to standardized Article objects for the RSS system.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import json
import hashlib
import re
from sqlalchemy.orm import Session

from ..store import Article
from ..intelligence.content_extractor import extract_content

logger = logging.getLogger(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for an API integration"""
    name: str
    base_url: str
    api_key: Optional[str]
    rate_limit_per_hour: int
    enabled: bool
    endpoints: Dict[str, str]
    default_params: Dict[str, Any]

class APIIntegrationsService:
    """Service for managing external API integrations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        self.user_agent = 'RSS Intelligence Bot (+https://example.com/bot)'
        
        # Rate limiting tracking
        self.rate_limits = {}
        
        # Integration configurations
        self.integrations = {
            'github': IntegrationConfig(
                name='GitHub',
                base_url='https://api.github.com',
                api_key=None,  # Set via environment variable
                rate_limit_per_hour=5000,  # GitHub's rate limit
                enabled=True,
                endpoints={
                    'releases': '/repos/{owner}/{repo}/releases',
                    'trending': '/search/repositories',
                    'issues': '/repos/{owner}/{repo}/issues',
                    'user_repos': '/users/{username}/repos'
                },
                default_params={
                    'per_page': 30,
                    'sort': 'updated'
                }
            ),
            'hackernews': IntegrationConfig(
                name='HackerNews',
                base_url='https://hacker-news.firebaseio.com/v0',
                api_key=None,
                rate_limit_per_hour=10000,
                enabled=True,
                endpoints={
                    'top_stories': '/topstories.json',
                    'new_stories': '/newstories.json',
                    'best_stories': '/beststories.json',
                    'ask_stories': '/askstories.json',
                    'show_stories': '/showstories.json',
                    'item': '/item/{id}.json'
                },
                default_params={}
            ),
            'reddit': IntegrationConfig(
                name='Reddit',
                base_url='https://www.reddit.com',
                api_key=None,
                rate_limit_per_hour=3600,
                enabled=True,
                endpoints={
                    'subreddit_hot': '/r/{subreddit}/hot.json',
                    'subreddit_top': '/r/{subreddit}/top.json',
                    'subreddit_new': '/r/{subreddit}/new.json',
                    'all_top': '/r/all/top.json',
                    'post_comments': '/r/{subreddit}/comments/{post_id}.json'
                },
                default_params={
                    'limit': 25
                }
            ),
            'youtube': IntegrationConfig(
                name='YouTube',
                base_url='https://www.googleapis.com/youtube/v3',
                api_key=None,  # Requires YouTube API key
                rate_limit_per_hour=10000,
                enabled=False,  # Disabled by default, needs API key
                endpoints={
                    'channel_videos': '/search',
                    'playlist_items': '/playlistItems',
                    'video_details': '/videos'
                },
                default_params={
                    'part': 'snippet',
                    'maxResults': 25
                }
            )
        }
    
    async def fetch_github_releases(self, owner: str, repo: str, limit: int = 10) -> List[Article]:
        """Fetch GitHub releases as articles"""
        integration = self.integrations['github']
        if not integration.enabled:
            return []
        
        articles = []
        
        try:
            url = integration.base_url + integration.endpoints['releases'].format(owner=owner, repo=repo)
            params = {'per_page': limit}
            
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                headers = {'User-Agent': self.user_agent}
                if integration.api_key:
                    headers['Authorization'] = f'token {integration.api_key}'
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"GitHub API returned {response.status} for {owner}/{repo}")
                        return []
                    
                    releases = await response.json()
                    
                    for release in releases:
                        try:
                            # Create article from release
                            title = f"{owner}/{repo} - {release['name'] or release['tag_name']}"
                            
                            # Use release body as content
                            content = release.get('body', '')
                            if not content:
                                content = f"Release {release['tag_name']} of {owner}/{repo}"
                            
                            # Add release metadata
                            content += f"\n\n**Release Info:**\n"
                            content += f"- Tag: {release['tag_name']}\n"
                            content += f"- Published: {release['published_at']}\n"
                            if release.get('prerelease'):
                                content += "- This is a pre-release\n"
                            if release.get('draft'):
                                content += "- This is a draft release\n"
                            
                            # Add download links
                            if release.get('assets'):
                                content += "\n**Downloads:**\n"
                                for asset in release['assets'][:5]:  # Limit to 5 assets
                                    content += f"- [{asset['name']}]({asset['browser_download_url']}) ({asset['size']} bytes)\n"
                            
                            published_at = datetime.fromisoformat(release['published_at'].replace('Z', '+00:00'))
                            
                            article = Article(
                                title=title,
                                url=release['html_url'],
                                content=content,
                                source=f"GitHub-{owner}-{repo}",
                                published_at=published_at,
                                content_hash=hashlib.sha256(f"{title}{content}".encode()).hexdigest(),
                                external_id=str(release['id']),
                                author=release['author']['login'] if release.get('author') else owner,
                                flags={'type': 'github_release', 'repo': f"{owner}/{repo}"}
                            )
                            
                            articles.append(article)
                            
                        except Exception as e:
                            logger.warning(f"Error processing GitHub release: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Error fetching GitHub releases for {owner}/{repo}: {e}")
        
        return articles
    
    async def fetch_hackernews_stories(self, story_type: str = 'top', limit: int = 30) -> List[Article]:
        """Fetch HackerNews stories as articles"""
        integration = self.integrations['hackernews']
        if not integration.enabled:
            return []
        
        articles = []
        
        try:
            # Get story IDs
            story_endpoint = f"{story_type}_stories"
            if story_endpoint not in integration.endpoints:
                logger.warning(f"Unknown HackerNews story type: {story_type}")
                return []
            
            url = integration.base_url + integration.endpoints[story_endpoint]
            
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                headers = {'User-Agent': self.user_agent}
                
                # Fetch story IDs
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"HackerNews API returned {response.status}")
                        return []
                    
                    story_ids = await response.json()
                    story_ids = story_ids[:limit]  # Limit results
                    
                    # Fetch individual stories
                    tasks = []
                    for story_id in story_ids:
                        task = self._fetch_hn_item(session, story_id, headers)
                        tasks.append(task)
                    
                    # Process stories concurrently (in batches to avoid overwhelming the API)
                    batch_size = 10
                    for i in range(0, len(tasks), batch_size):
                        batch = tasks[i:i + batch_size]
                        results = await asyncio.gather(*batch, return_exceptions=True)
                        
                        for result in results:
                            if isinstance(result, Article):
                                articles.append(result)
                            elif isinstance(result, Exception):
                                logger.debug(f"Error fetching HN story: {result}")
                        
                        # Small delay between batches
                        await asyncio.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"Error fetching HackerNews stories: {e}")
        
        return articles
    
    async def _fetch_hn_item(self, session: aiohttp.ClientSession, item_id: int, headers: Dict[str, str]) -> Optional[Article]:
        """Fetch a single HackerNews item"""
        try:
            integration = self.integrations['hackernews']
            item_url = integration.base_url + integration.endpoints['item'].format(id=item_id)
            
            async with session.get(item_url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                item = await response.json()
                
                if not item or item.get('deleted') or item.get('dead'):
                    return None
                
                # Only process stories, not comments
                if item.get('type') != 'story':
                    return None
                
                title = item.get('title', f"HN Story #{item_id}")
                url = item.get('url', f"https://news.ycombinator.com/item?id={item_id}")
                
                # Build content
                content = ""
                if item.get('text'):
                    content = item['text']
                
                # Add HN metadata
                content += f"\n\n**HackerNews Info:**\n"
                content += f"- Score: {item.get('score', 0)} points\n"
                content += f"- Comments: {item.get('descendants', 0)}\n"
                content += f"- Author: {item.get('by', 'Unknown')}\n"
                content += f"- HN Discussion: https://news.ycombinator.com/item?id={item_id}\n"
                
                # If there's an external URL, try to extract content
                if item.get('url') and item['url'] != f"https://news.ycombinator.com/item?id={item_id}":
                    try:
                        extracted = await extract_content(item['url'])
                        if extracted and extracted.get('content'):
                            content = extracted['content'] + "\n\n" + content
                    except Exception as e:
                        logger.debug(f"Failed to extract content for HN story {item_id}: {e}")
                
                published_at = datetime.fromtimestamp(item.get('time', 0))
                
                article = Article(
                    title=title,
                    url=url,
                    content=content,
                    source="HackerNews",
                    published_at=published_at,
                    content_hash=hashlib.sha256(f"{title}{content}".encode()).hexdigest(),
                    external_id=str(item_id),
                    author=item.get('by'),
                    score=item.get('score', 0),
                    flags={
                        'type': 'hackernews_story',
                        'hn_score': item.get('score', 0),
                        'hn_comments': item.get('descendants', 0)
                    }
                )
                
                return article
                
        except Exception as e:
            logger.debug(f"Error fetching HN item {item_id}: {e}")
            return None
    
    async def fetch_reddit_posts(self, subreddit: str, sort: str = 'hot', limit: int = 25) -> List[Article]:
        """Fetch Reddit posts as articles"""
        integration = self.integrations['reddit']
        if not integration.enabled:
            return []
        
        articles = []
        
        try:
            # Build endpoint
            endpoint_key = f"subreddit_{sort}"
            if endpoint_key not in integration.endpoints:
                logger.warning(f"Unknown Reddit sort type: {sort}")
                return []
            
            url = integration.base_url + integration.endpoints[endpoint_key].format(subreddit=subreddit)
            params = {'limit': limit}
            
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                headers = {'User-Agent': self.user_agent}
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Reddit API returned {response.status} for r/{subreddit}")
                        return []
                    
                    data = await response.json()
                    
                    for post_data in data.get('data', {}).get('children', []):
                        try:
                            post = post_data.get('data', {})
                            
                            if not post:
                                continue
                            
                            title = post.get('title', 'Untitled Reddit Post')
                            url = post.get('url', f"https://reddit.com{post.get('permalink', '')}")
                            
                            # Build content
                            content = post.get('selftext', '')
                            
                            # Add Reddit metadata
                            content += f"\n\n**Reddit Info:**\n"
                            content += f"- Subreddit: r/{subreddit}\n"
                            content += f"- Score: {post.get('score', 0)} points\n"
                            content += f"- Comments: {post.get('num_comments', 0)}\n"
                            content += f"- Author: u/{post.get('author', 'Unknown')}\n"
                            content += f"- Reddit Discussion: https://reddit.com{post.get('permalink', '')}\n"
                            
                            # If it's a link post, try to extract content from the URL
                            if post.get('url') and not post.get('is_self'):
                                try:
                                    extracted = await extract_content(post['url'])
                                    if extracted and extracted.get('content'):
                                        content = extracted['content'] + "\n\n" + content
                                except Exception as e:
                                    logger.debug(f"Failed to extract content for Reddit post: {e}")
                            
                            published_at = datetime.fromtimestamp(post.get('created_utc', 0))
                            
                            article = Article(
                                title=title,
                                url=url,
                                content=content,
                                source=f"Reddit-{subreddit}",
                                published_at=published_at,
                                content_hash=hashlib.sha256(f"{title}{content}".encode()).hexdigest(),
                                external_id=post.get('id'),
                                author=post.get('author'),
                                score=post.get('score', 0),
                                flags={
                                    'type': 'reddit_post',
                                    'subreddit': subreddit,
                                    'reddit_score': post.get('score', 0),
                                    'reddit_comments': post.get('num_comments', 0),
                                    'is_self_post': post.get('is_self', False)
                                }
                            )
                            
                            articles.append(article)
                            
                        except Exception as e:
                            logger.warning(f"Error processing Reddit post: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Error fetching Reddit posts from r/{subreddit}: {e}")
        
        return articles
    
    async def fetch_github_trending(self, language: str = '', time_period: str = 'daily', limit: int = 30) -> List[Article]:
        """Fetch GitHub trending repositories"""
        integration = self.integrations['github']
        if not integration.enabled:
            return []
        
        articles = []
        
        try:
            # Calculate date for trending
            date_map = {
                'daily': datetime.now() - timedelta(days=1),
                'weekly': datetime.now() - timedelta(weeks=1),
                'monthly': datetime.now() - timedelta(days=30)
            }
            created_date = date_map.get(time_period, date_map['daily']).strftime('%Y-%m-%d')
            
            url = integration.base_url + integration.endpoints['trending']
            params = {
                'q': f'created:>{created_date}',
                'sort': 'stars',
                'order': 'desc',
                'per_page': limit
            }
            
            if language:
                params['q'] += f' language:{language}'
            
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                headers = {'User-Agent': self.user_agent}
                if integration.api_key:
                    headers['Authorization'] = f'token {integration.api_key}'
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"GitHub trending API returned {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    for repo in data.get('items', []):
                        try:
                            title = f"🔥 Trending: {repo['full_name']}"
                            
                            content = repo.get('description', '') + "\n\n"
                            content += f"**Repository Info:**\n"
                            content += f"- Language: {repo.get('language', 'N/A')}\n"
                            content += f"- Stars: {repo.get('stargazers_count', 0):,}\n"
                            content += f"- Forks: {repo.get('forks_count', 0):,}\n"
                            content += f"- Issues: {repo.get('open_issues_count', 0)}\n"
                            content += f"- License: {repo.get('license', {}).get('name', 'N/A') if repo.get('license') else 'N/A'}\n"
                            content += f"- Created: {repo['created_at']}\n"
                            content += f"- Updated: {repo['updated_at']}\n"
                            
                            if repo.get('topics'):
                                content += f"- Topics: {', '.join(repo['topics'])}\n"
                            
                            published_at = datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00'))
                            
                            article = Article(
                                title=title,
                                url=repo['html_url'],
                                content=content,
                                source=f"GitHub-Trending-{language or 'All'}",
                                published_at=published_at,
                                content_hash=hashlib.sha256(f"{title}{content}".encode()).hexdigest(),
                                external_id=str(repo['id']),
                                author=repo['owner']['login'],
                                score=repo.get('stargazers_count', 0),
                                flags={
                                    'type': 'github_trending',
                                    'language': repo.get('language'),
                                    'stars': repo.get('stargazers_count', 0),
                                    'forks': repo.get('forks_count', 0)
                                }
                            )
                            
                            articles.append(article)
                            
                        except Exception as e:
                            logger.warning(f"Error processing trending repo: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Error fetching GitHub trending repositories: {e}")
        
        return articles
    
    def get_integration_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all integrations"""
        status = {}
        
        for name, config in self.integrations.items():
            status[name] = {
                'enabled': config.enabled,
                'has_api_key': config.api_key is not None,
                'rate_limit_per_hour': config.rate_limit_per_hour,
                'base_url': config.base_url,
                'endpoints': list(config.endpoints.keys())
            }
        
        return status
    
    async def test_integration(self, integration_name: str) -> Dict[str, Any]:
        """Test an integration to check if it's working"""
        if integration_name not in self.integrations:
            return {'error': f'Integration {integration_name} not found'}
        
        integration = self.integrations[integration_name]
        if not integration.enabled:
            return {'error': f'Integration {integration_name} is disabled'}
        
        try:
            if integration_name == 'github':
                # Test by fetching a simple endpoint
                url = integration.base_url + '/rate_limit'
                headers = {'User-Agent': self.user_agent}
                if integration.api_key:
                    headers['Authorization'] = f'token {integration.api_key}'
                
                async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                'status': 'ok',
                                'rate_limit': data.get('rate'),
                                'authenticated': integration.api_key is not None
                            }
                        else:
                            return {'error': f'HTTP {response.status}'}
            
            elif integration_name == 'hackernews':
                # Test by fetching top stories
                url = integration.base_url + integration.endpoints['top_stories']
                
                async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                'status': 'ok',
                                'sample_story_ids': data[:5] if data else []
                            }
                        else:
                            return {'error': f'HTTP {response.status}'}
            
            elif integration_name == 'reddit':
                # Test by fetching r/programming
                url = integration.base_url + '/r/programming/hot.json'
                params = {'limit': 1}
                
                async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                'status': 'ok',
                                'sample_data': bool(data.get('data', {}).get('children'))
                            }
                        else:
                            return {'error': f'HTTP {response.status}'}
            
            else:
                return {'error': f'Test not implemented for {integration_name}'}
        
        except Exception as e:
            return {'error': str(e)}

# Global instance
api_integrations_service = None

def get_api_integrations_service(db: Session) -> APIIntegrationsService:
    """Get or create API integrations service"""
    return APIIntegrationsService(db)