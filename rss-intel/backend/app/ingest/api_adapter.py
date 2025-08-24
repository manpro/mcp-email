"""API adapter for various third-party APIs (GitHub, HN, Reddit, YouTube)"""
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging
from dateutil.parser import parse as parse_date

from .base import BaseAdapter, RawItem, AdapterFactory

logger = logging.getLogger(__name__)


class APIProvider:
    """Base class for API providers"""
    
    async def fetch_items(self, session: aiohttp.ClientSession, config: Dict[str, Any]) -> List[RawItem]:
        raise NotImplementedError


class GitHubProvider(APIProvider):
    """GitHub API provider - fetches repositories, releases, issues"""
    
    async def fetch_items(self, session: aiohttp.ClientSession, config: Dict[str, Any]) -> List[RawItem]:
        items = []
        github_token = config.get('token')
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'RSSIntelBot/2.0'
        }
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        # Fetch different types based on config
        if 'repositories' in config:
            for repo in config['repositories']:
                repo_items = await self._fetch_repository_activity(session, repo, headers)
                items.extend(repo_items)
        
        if 'topics' in config:
            for topic in config['topics']:
                topic_items = await self._fetch_topic_repositories(session, topic, headers)
                items.extend(topic_items)
        
        return items
    
    async def _fetch_repository_activity(self, session: aiohttp.ClientSession, repo: str, headers: Dict[str, str]) -> List[RawItem]:
        """Fetch recent activity from a GitHub repository"""
        items = []
        
        try:
            # Fetch recent releases
            url = f"https://api.github.com/repos/{repo}/releases"
            async with session.get(url, headers=headers, params={'per_page': 10}) as response:
                if response.status == 200:
                    releases = await response.json()
                    for release in releases:
                        published_at = parse_date(release['published_at']) if release['published_at'] else datetime.now(timezone.utc)
                        
                        # Skip if older than 30 days
                        if (datetime.now(timezone.utc) - published_at).days > 30:
                            continue
                        
                        items.append(RawItem(
                            title=f"Release: {release['name'] or release['tag_name']}",
                            url=release['html_url'],
                            content=release['body'] or f"New release {release['tag_name']} of {repo}",
                            published_at=published_at,
                            source=f"GitHub {repo}",
                            author=release['author']['login'] if release['author'] else None,
                            metadata={
                                'type': 'github_release',
                                'repo': repo,
                                'tag_name': release['tag_name'],
                                'prerelease': release['prerelease']
                            }
                        ))
            
            await asyncio.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error fetching GitHub repo {repo}: {e}")
        
        return items
    
    async def _fetch_topic_repositories(self, session: aiohttp.ClientSession, topic: str, headers: Dict[str, str]) -> List[RawItem]:
        """Fetch recently updated repositories by topic"""
        items = []
        
        try:
            # Search for recently updated repositories
            url = "https://api.github.com/search/repositories"
            params = {
                'q': f'topic:{topic} pushed:>={datetime.now(timezone.utc) - timedelta(days=7):%Y-%m-%d}',
                'sort': 'updated',
                'order': 'desc',
                'per_page': 20
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for repo in data.get('items', []):
                        updated_at = parse_date(repo['updated_at'])
                        
                        items.append(RawItem(
                            title=f"Updated: {repo['full_name']}",
                            url=repo['html_url'],
                            content=repo['description'] or f"Repository {repo['full_name']} was updated",
                            published_at=updated_at,
                            source=f"GitHub Topic: {topic}",
                            metadata={
                                'type': 'github_repo_update',
                                'topic': topic,
                                'stars': repo['stargazers_count'],
                                'language': repo['language']
                            }
                        ))
                        
        except Exception as e:
            logger.error(f"Error fetching GitHub topic {topic}: {e}")
        
        return items


class HackerNewsProvider(APIProvider):
    """Hacker News API provider"""
    
    async def fetch_items(self, session: aiohttp.ClientSession, config: Dict[str, Any]) -> List[RawItem]:
        items = []
        
        try:
            # Fetch top stories
            async with session.get('https://hacker-news.firebaseio.com/v0/topstories.json') as response:
                if response.status != 200:
                    return items
                
                story_ids = await response.json()
                
                # Fetch details for top 50 stories
                for story_id in story_ids[:50]:
                    story_url = f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
                    async with session.get(story_url) as story_response:
                        if story_response.status == 200:
                            story = await story_response.json()
                            
                            # Skip if no URL (Ask HN, etc.) unless configured to include
                            if not story.get('url') and not config.get('include_text_posts'):
                                continue
                            
                            # Skip if older than configured days
                            max_age = config.get('max_age_days', 1)
                            story_time = datetime.fromtimestamp(story['time'], tz=timezone.utc)
                            if (datetime.now(timezone.utc) - story_time).days > max_age:
                                continue
                            
                            content = story.get('text', '') or f"Hacker News post with {story.get('descendants', 0)} comments"
                            
                            items.append(RawItem(
                                title=story['title'],
                                url=story.get('url') or f"https://news.ycombinator.com/item?id={story_id}",
                                content=content,
                                published_at=story_time,
                                source="Hacker News",
                                author=story.get('by'),
                                metadata={
                                    'type': 'hackernews',
                                    'score': story.get('score'),
                                    'comments': story.get('descendants', 0),
                                    'hn_id': story_id
                                }
                            ))
                    
                    await asyncio.sleep(0.01)  # Small delay to be nice to HN API
                    
        except Exception as e:
            logger.error(f"Error fetching Hacker News: {e}")
        
        return items


class RedditProvider(APIProvider):
    """Reddit API provider"""
    
    async def fetch_items(self, session: aiohttp.ClientSession, config: Dict[str, Any]) -> List[RawItem]:
        items = []
        subreddits = config.get('subreddits', [])
        
        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                params = {'limit': 25}
                
                headers = {
                    'User-Agent': 'RSSIntelBot/2.0 by /u/rssintel'
                }
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        continue
                    
                    data = await response.json()
                    
                    for post_data in data.get('data', {}).get('children', []):
                        post = post_data['data']
                        
                        # Skip stickied posts
                        if post.get('stickied'):
                            continue
                        
                        # Check age
                        created_time = datetime.fromtimestamp(post['created_utc'], tz=timezone.utc)
                        max_age = config.get('max_age_days', 3)
                        if (datetime.now(timezone.utc) - created_time).days > max_age:
                            continue
                        
                        # Skip if score too low
                        min_score = config.get('min_score', 10)
                        if post.get('score', 0) < min_score:
                            continue
                        
                        # Use URL if available, otherwise Reddit permalink
                        url = post.get('url')
                        if not url or 'reddit.com' in url:
                            url = f"https://www.reddit.com{post['permalink']}"
                        
                        # Build content from selftext if available
                        content = post.get('selftext', '') or f"Reddit post with {post.get('num_comments', 0)} comments"
                        
                        items.append(RawItem(
                            title=post['title'],
                            url=url,
                            content=content,
                            published_at=created_time,
                            source=f"Reddit r/{subreddit}",
                            author=post.get('author'),
                            metadata={
                                'type': 'reddit',
                                'subreddit': subreddit,
                                'score': post.get('score'),
                                'comments': post.get('num_comments', 0),
                                'reddit_id': post['id']
                            }
                        ))
                        
            except Exception as e:
                logger.error(f"Error fetching Reddit r/{subreddit}: {e}")
                continue
        
        return items


class APIAdapter(BaseAdapter):
    """Generic API adapter that uses provider classes"""
    
    PROVIDERS = {
        'github': GitHubProvider(),
        'hackernews': HackerNewsProvider(),
        'reddit': RedditProvider(),
    }
    
    async def fetch_new(self) -> List[RawItem]:
        """Fetch items from configured API providers"""
        provider_name = self.config.get('provider')
        if not provider_name or provider_name not in self.PROVIDERS:
            logger.error(f"Unknown API provider: {provider_name}")
            return []
        
        provider = self.PROVIDERS[provider_name]
        
        try:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                items = await provider.fetch_items(session, self.config)
                logger.info(f"Fetched {len(items)} items from {provider_name} API")
                return items
                
        except Exception as e:
            logger.error(f"Error fetching from {provider_name} API: {e}")
            return []


# Register the adapter
AdapterFactory.register('api', APIAdapter)