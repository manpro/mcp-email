"""
Fediverse API Endpoints

API endpoints for managing Fediverse/Mastodon integrations, following accounts,
monitoring hashtags, and fetching posts from across the Fediverse.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..deps import get_db
from ..services.fediverse_service import get_fediverse_service
from ..store import Feed

logger = logging.getLogger(__name__)
router = APIRouter()

class FediverseSourceRequest(BaseModel):
    """Request to add a Fediverse source"""
    source_type: str = Field(..., regex="^(account|hashtag|instance)$")
    identifier: str = Field(..., min_length=1, max_length=200)
    instance_domain: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)

class MastodonInstanceInfo(BaseModel):
    """Mastodon instance information"""
    domain: str
    name: str
    description: str
    version: str
    user_count: int
    status_count: int
    is_alive: bool

class FediverseAccountInfo(BaseModel):
    """Fediverse account information"""
    username: str
    domain: str
    display_name: str
    note: str
    avatar: Optional[str]
    followers_count: int
    following_count: int
    statuses_count: int
    bot: bool
    locked: bool

class FediversePostSummary(BaseModel):
    """Summary of a Fediverse post"""
    id: str
    url: str
    content_preview: str
    author_username: str
    author_display_name: str
    published_at: str
    replies_count: int
    reblogs_count: int
    favourites_count: int
    tags: List[str]
    instance_domain: str

@router.get("/fediverse/instances")
async def discover_instances(
    db: Session = Depends(get_db)
):
    """Discover available Mastodon instances"""
    try:
        service = get_fediverse_service(db)
        instances = await service.discover_mastodon_instances()
        
        return {
            "instances": [
                MastodonInstanceInfo(
                    domain=inst.domain,
                    name=inst.name,
                    description=inst.description,
                    version=inst.version,
                    user_count=inst.user_count,
                    status_count=inst.status_count,
                    is_alive=inst.is_alive
                )
                for inst in instances
            ],
            "total_count": len(instances)
        }
        
    except Exception as e:
        logger.error(f"Failed to discover instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fediverse/account/{username}/posts")
async def get_account_posts(
    username: str,
    domain: str = Query(..., description="Instance domain"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get posts from a specific Mastodon account"""
    try:
        service = get_fediverse_service(db)
        posts = await service.fetch_account_posts(username, domain, limit)
        
        post_summaries = []
        for post in posts:
            post_summaries.append(FediversePostSummary(
                id=post.id,
                url=post.url,
                content_preview=post.content_text[:200] + "..." if len(post.content_text) > 200 else post.content_text,
                author_username=post.author_username,
                author_display_name=post.author_display_name,
                published_at=post.published_at.isoformat(),
                replies_count=post.replies_count,
                reblogs_count=post.reblogs_count,
                favourites_count=post.favourites_count,
                tags=post.tags,
                instance_domain=post.instance_domain
            ))
        
        return {
            "account": f"@{username}@{domain}",
            "posts": post_summaries,
            "total_count": len(post_summaries),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get posts from @{username}@{domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fediverse/hashtag/{hashtag}")
async def get_hashtag_posts(
    hashtag: str,
    instance_domain: str = Query(..., description="Instance to search"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get posts for a specific hashtag"""
    try:
        service = get_fediverse_service(db)
        posts = await service.fetch_hashtag_posts(hashtag, instance_domain, limit)
        
        post_summaries = []
        for post in posts:
            post_summaries.append(FediversePostSummary(
                id=post.id,
                url=post.url,
                content_preview=post.content_text[:200] + "..." if len(post.content_text) > 200 else post.content_text,
                author_username=post.author_username,
                author_display_name=post.author_display_name,
                published_at=post.published_at.isoformat(),
                replies_count=post.replies_count,
                reblogs_count=post.reblogs_count,
                favourites_count=post.favourites_count,
                tags=post.tags,
                instance_domain=post.instance_domain
            ))
        
        return {
            "hashtag": f"#{hashtag}",
            "instance": instance_domain,
            "posts": post_summaries,
            "total_count": len(post_summaries),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get posts for #{hashtag} from {instance_domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fediverse/timeline/public")
async def get_public_timeline(
    instance_domain: str = Query(..., description="Instance domain"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get public timeline from an instance"""
    try:
        service = get_fediverse_service(db)
        posts = await service.fetch_public_timeline(instance_domain, limit)
        
        post_summaries = []
        for post in posts:
            post_summaries.append(FediversePostSummary(
                id=post.id,
                url=post.url,
                content_preview=post.content_text[:200] + "..." if len(post.content_text) > 200 else post.content_text,
                author_username=post.author_username,
                author_display_name=post.author_display_name,
                published_at=post.published_at.isoformat(),
                replies_count=post.replies_count,
                reblogs_count=post.reblogs_count,
                favourites_count=post.favourites_count,
                tags=post.tags,
                instance_domain=post.instance_domain
            ))
        
        return {
            "instance": instance_domain,
            "timeline": "public",
            "posts": post_summaries,
            "total_count": len(post_summaries),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get public timeline from {instance_domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fediverse/sources")
async def add_fediverse_source(
    request: FediverseSourceRequest,
    db: Session = Depends(get_db)
):
    """Add a new Fediverse source to monitor"""
    try:
        service = get_fediverse_service(db)
        
        success = service.add_fediverse_source(
            source_type=request.source_type,
            identifier=request.identifier,
            instance_domain=request.instance_domain,
            description=request.description or ''
        )
        
        if success:
            return {
                "message": "Fediverse source added successfully",
                "source_type": request.source_type,
                "identifier": request.identifier,
                "instance_domain": request.instance_domain
            }
        else:
            raise HTTPException(status_code=409, detail="Source already exists")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add Fediverse source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fediverse/sources")
async def list_fediverse_sources(
    source_type: Optional[str] = Query(None, regex="^(account|hashtag|instance)$"),
    db: Session = Depends(get_db)
):
    """List configured Fediverse sources"""
    try:
        query = db.query(Feed).filter(Feed.feed_type == 'fediverse')
        
        if source_type:
            query = query.filter(Feed.url.contains(f"fediverse://{source_type}/"))
        
        sources = query.all()
        
        source_list = []
        for source in sources:
            # Parse the URL to extract details
            url_parts = source.url.replace('fediverse://', '').split('/')
            if len(url_parts) >= 2:
                parsed_type = url_parts[0]
                parsed_identifier = url_parts[1]
                
                source_list.append({
                    "id": source.id,
                    "source_type": parsed_type,
                    "identifier": parsed_identifier,
                    "title": source.title,
                    "description": source.description,
                    "is_active": source.is_active,
                    "created_at": source.created_at.isoformat() if source.created_at else None
                })
        
        return {
            "sources": source_list,
            "total_count": len(source_list),
            "filter": {"source_type": source_type} if source_type else {}
        }
        
    except Exception as e:
        logger.error(f"Failed to list Fediverse sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/fediverse/sources/{source_id}")
async def remove_fediverse_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    """Remove a Fediverse source"""
    try:
        source = db.query(Feed).filter(
            Feed.id == source_id,
            Feed.feed_type == 'fediverse'
        ).first()
        
        if not source:
            raise HTTPException(status_code=404, detail="Fediverse source not found")
        
        db.delete(source)
        db.commit()
        
        return {
            "message": "Fediverse source removed successfully",
            "source_id": source_id,
            "title": source.title
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove Fediverse source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fediverse/monitor/hashtags")
async def monitor_hashtags_across_instances(
    background_tasks: BackgroundTasks,
    hashtags: List[str] = Query(..., description="Hashtags to monitor"),
    instances: List[str] = Query(..., description="Instance domains"),
    db: Session = Depends(get_db)
):
    """Monitor hashtags across multiple instances (background task)"""
    try:
        service = get_fediverse_service(db)
        
        # Start background monitoring
        background_tasks.add_task(
            monitor_hashtags_task,
            service,
            hashtags,
            instances
        )
        
        return {
            "message": "Hashtag monitoring started",
            "hashtags": hashtags,
            "instances": instances,
            "status": "background_task_started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start hashtag monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fediverse/sync")
async def sync_fediverse_sources(
    background_tasks: BackgroundTasks,
    source_ids: Optional[List[int]] = Query(None, description="Specific source IDs to sync"),
    db: Session = Depends(get_db)
):
    """Sync posts from configured Fediverse sources"""
    try:
        # Get sources to sync
        query = db.query(Feed).filter(Feed.feed_type == 'fediverse', Feed.is_active == True)
        
        if source_ids:
            query = query.filter(Feed.id.in_(source_ids))
        
        sources = query.all()
        
        if not sources:
            return {
                "message": "No active Fediverse sources found",
                "synced_count": 0
            }
        
        # Start background sync
        background_tasks.add_task(
            sync_fediverse_sources_task,
            sources,
            db
        )
        
        return {
            "message": "Fediverse sync started",
            "sources_count": len(sources),
            "status": "background_task_started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start Fediverse sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fediverse/stats")
async def get_fediverse_statistics(
    db: Session = Depends(get_db)
):
    """Get statistics about Fediverse integration"""
    try:
        # Count sources by type
        fedi_sources = db.query(Feed).filter(Feed.feed_type == 'fediverse').all()
        
        stats_by_type = {'account': 0, 'hashtag': 0, 'instance': 0}
        active_sources = 0
        
        for source in fedi_sources:
            if source.is_active:
                active_sources += 1
            
            # Parse source type from URL
            if '/account/' in source.url:
                stats_by_type['account'] += 1
            elif '/hashtag/' in source.url:
                stats_by_type['hashtag'] += 1
            elif '/instance/' in source.url:
                stats_by_type['instance'] += 1
        
        # Get recent Fediverse articles
        from ..store import Article
        from sqlalchemy import desc, and_
        from datetime import datetime, timedelta
        
        recent_articles = db.query(Article).filter(
            and_(
                Article.source.contains('fediverse'),
                Article.published_at >= datetime.now() - timedelta(days=7)
            )
        ).count()
        
        return {
            "total_sources": len(fedi_sources),
            "active_sources": active_sources,
            "sources_by_type": stats_by_type,
            "recent_articles_7days": recent_articles,
            "integration_status": "active" if active_sources > 0 else "inactive"
        }
        
    except Exception as e:
        logger.error(f"Failed to get Fediverse statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def monitor_hashtags_task(service, hashtags: List[str], instances: List[str]):
    """Background task for monitoring hashtags"""
    try:
        articles = await service.monitor_hashtags_across_instances(hashtags, instances)
        logger.info(f"Hashtag monitoring completed: {len(articles)} articles collected")
    except Exception as e:
        logger.error(f"Hashtag monitoring task failed: {e}")

async def sync_fediverse_sources_task(sources: List[Feed], db: Session):
    """Background task for syncing Fediverse sources"""
    try:
        service = get_fediverse_service(db)
        total_articles = 0
        
        for source in sources:
            try:
                # Parse source URL to determine type and fetch accordingly
                url_parts = source.url.replace('fediverse://', '').split('/')
                
                if len(url_parts) >= 2:
                    source_type = url_parts[0]
                    identifier = url_parts[1]
                    
                    articles = []
                    
                    if source_type == 'account' and '@' in identifier:
                        username, domain = identifier.split('@')
                        posts = await service.fetch_account_posts(username, domain, 10)
                        articles = await service.convert_posts_to_articles(posts, f"fediverse_{source.id}")
                    
                    elif source_type == 'hashtag' and '@' in identifier:
                        hashtag, domain = identifier.split('@')
                        posts = await service.fetch_hashtag_posts(hashtag, domain, 15)
                        articles = await service.convert_posts_to_articles(posts, f"fediverse_{source.id}")
                    
                    elif source_type == 'instance':
                        domain = identifier
                        posts = await service.fetch_public_timeline(domain, 10)
                        articles = await service.convert_posts_to_articles(posts, f"fediverse_{source.id}")
                    
                    # Save articles to database
                    for article in articles:
                        # Check if article already exists
                        existing = db.query(Article).filter(
                            Article.content_hash == article.content_hash
                        ).first()
                        
                        if not existing:
                            db.add(article)
                            total_articles += 1
                    
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error syncing Fediverse source {source.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"Fediverse sync completed: {total_articles} new articles added")
        
    except Exception as e:
        logger.error(f"Fediverse sync task failed: {e}")