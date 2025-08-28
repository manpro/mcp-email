from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path
import os
import asyncio

from .deps import get_db, get_db_pool_stats
from .schemas import (
    Article, ArticleList, DecideRequest, 
    HealthResponse, RefreshResponse, ConfigResponse
)
from .store import ArticleStore
from .freshrss_client import FreshRSSClient
from .scoring import ScoringEngine
from .scheduler import scheduler
from .config import settings
from .extraction_worker import extraction_worker
from .content_service import ContentExtractionService
from .learning_scheduler import start_learning_scheduler, stop_learning_scheduler
from .ml.api_recommend import router as recommend_router
# from .ml.api_events import router as ml_events_router  # Events have issues, keep disabled
# from .api.events import router as events_router  # Events have issues, keep disabled
from .api.personalization import router as personalization_router
from .api.search import router as search_router
from .api.search_options import router as search_options_router
from .api.stories import router as stories_router
from .api.spotlight import router as spotlight_router
from .api.recommend_simple import router as recommend_simple_router
from .api.user_profile import router as user_profile_router
from .api.auth import router as auth_router
from .api.learning import router as learning_router
from .api.ab_testing import router as ab_testing_router
from .api.intelligence import router as intelligence_router
from .api.cache import router as cache_router
from .websocket_hub import connection_manager, event_broadcaster
from .events import event_stream, cleanup_events
from .notifications import (
    notification_manager, start_notification_event_consumer, 
    periodic_notification_cleanup, NotificationType, NotificationPriority
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting RSS Intelligence Backend...")
    scheduler.start()
    await start_learning_scheduler()
    
    # Start event stream and WebSocket broadcaster
    print("Starting real-time event system...")
    await event_stream.connect()
    
    # Start event broadcaster in background
    asyncio.create_task(event_broadcaster.start())
    
    # Start notification system (temporarily disabled)
    # print("Starting notification system...")
    # asyncio.create_task(start_notification_event_consumer())
    # asyncio.create_task(periodic_notification_cleanup())
    
    yield
    
    # Shutdown
    print("Shutting down...")
    scheduler.stop()
    await stop_learning_scheduler()
    
    # Cleanup event system
    print("Cleaning up event system...")
    event_broadcaster.stop()
    await cleanup_events()

app = FastAPI(
    title="RSS Intelligence Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(recommend_router, prefix="/api/ml", tags=["recommendations"])
app.include_router(recommend_simple_router, prefix="/api", tags=["recommendations"])
app.include_router(user_profile_router, tags=["user_profile"])
# app.include_router(ml_events_router, prefix="/api/ml", tags=["ml-events"])  # Events have issues, keep disabled
# app.include_router(events_router, prefix="/api", tags=["events"])  # Events have issues, keep disabled  
app.include_router(personalization_router, prefix="/api", tags=["personalization"])
app.include_router(search_router, tags=["search"])
app.include_router(search_options_router, tags=["search"])
app.include_router(stories_router, tags=["stories"])
app.include_router(spotlight_router, prefix="/api/spotlight", tags=["spotlight"])
app.include_router(auth_router, tags=["authentication"])
app.include_router(learning_router, tags=["learning"])
app.include_router(ab_testing_router, tags=["ab_testing"])
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(cache_router, tags=["cache"])

# Admin router temporarily disabled due to spam detection conflicts
# from .api.admin import router as admin_router
# app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

# Import and include source health monitoring router
from .api.source_health import router as source_health_router
app.include_router(source_health_router, prefix="/api", tags=["source_health"])

# Import and include recommendations router  
from .api.recommendations import router as recommendations_router
app.include_router(recommendations_router, prefix="/api", tags=["recommendations"])

# Import and include Fediverse router
from .api.fediverse import router as fediverse_router
app.include_router(fediverse_router, prefix="/api", tags=["fediverse"])

# Import and include Vector Search router
from .api.vector_search import router as vector_search_router
app.include_router(vector_search_router, prefix="/api", tags=["vector_search"])

# Import and include Trending Analysis router
from .api.trending import router as trending_router
app.include_router(trending_router, prefix="/api", tags=["trending"])

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = {}
    
    # Check database
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        services["database"] = "healthy"
    except:
        services["database"] = "unhealthy"
    finally:
        db.close()
    
    # Check FreshRSS
    try:
        client = FreshRSSClient()
        if client.login():
            services["freshrss"] = "healthy"
        else:
            services["freshrss"] = "unhealthy"
        client.client.close()
    except:
        services["freshrss"] = "unhealthy"
    
    # Check scheduler
    services["scheduler"] = "running" if scheduler.is_running else "stopped"
    
    # Check Redis cache
    try:
        from .cache_service import cache_service
        cache_stats = cache_service.get_cache_stats()
        services["redis_cache"] = "active" if cache_stats.get("status") == "active" else "inactive"
    except:
        services["redis_cache"] = "inactive"
    
    return HealthResponse(
        status="healthy" if all(v in ["healthy", "running", "active"] for v in services.values()) else "degraded",
        timestamp=datetime.utcnow(),
        services=services
    )

@app.get("/items", response_model=ArticleList)
async def get_items(
    min_score: Optional[int] = Query(None, description="Minimum score filter"),
    label: Optional[str] = Query(None, description="Label filter"),
    source: Optional[str] = Query(None, description="Source filter"),
    q: Optional[str] = Query(None, description="Search query"),
    has_image: Optional[bool] = Query(None, description="Filter by image presence"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get filtered list of articles"""
    store = ArticleStore(db)
    
    # Always filter out spam articles (score < 0) unless min_score is explicitly lower
    effective_min_score = max(0, min_score) if min_score is not None else 0
    
    articles, total = store.get_articles(
        min_score=effective_min_score,
        label=label,
        source=source,
        query=q,
        has_image=has_image,
        page=page,
        page_size=page_size,
        include_spam=False  # Always exclude spam from main feed
    )
    
    return ArticleList(
        items=articles,
        total=total,
        page=page,
        page_size=page_size
    )

@app.get("/items/{entry_id}", response_model=Article)
async def get_item(entry_id: str, db: Session = Depends(get_db)):
    """Get single article by entry ID"""
    store = ArticleStore(db)
    article = store.get_article_by_entry_id(entry_id)
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article

@app.post("/items/{entry_id}/decide")
async def decide_action(
    entry_id: str,
    request: DecideRequest,
    db: Session = Depends(get_db)
):
    """Apply action to an article"""
    store = ArticleStore(db)
    article = store.get_article_by_entry_id(entry_id)
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Actions that don't require FreshRSS connection
    local_only_actions = {"downvote", "undownvote", "label_add", "label_remove"}
    
    client = None
    if request.action not in local_only_actions:
        client = FreshRSSClient()
        if not client.login():
            raise HTTPException(status_code=503, detail="FreshRSS connection failed")
    
    success = False
    message = ""
    
    try:
        if request.action == "star":
            success = client.star_entry(entry_id)
            if success:
                article.flags = article.flags or {}
                article.flags["starred"] = True
                db.commit()
            message = "Entry starred"
            
        elif request.action == "unstar":
            success = client.unstar_entry(entry_id)
            if success:
                article.flags = article.flags or {}
                article.flags["starred"] = False
                db.commit()
            message = "Entry unstarred"
            
        elif request.action == "mark_read":
            success = client.mark_as_read(entry_id)
            if success:
                article.flags = article.flags or {}
                article.flags["read"] = True
                db.commit()
            message = "Entry marked as read"
            
        elif request.action == "archive":
            success = client.mark_as_read(entry_id)
            if success:
                article.flags = article.flags or {}
                article.flags["archived"] = True
                db.commit()
            message = "Entry archived"
            
        elif request.action == "downvote":
            # Downvote doesn't interact with FreshRSS, just local flag
            success = True
            article.flags = article.flags or {}
            article.flags["downvoted"] = True
            # Add event tracking - use 'dismiss' as closest equivalent to downvote
            from .store import Event
            event = Event(
                article_id=article.id,
                user_id='owner',  # Default user for now
                type='dismiss'
            )
            db.add(event)
            db.commit()
            message = "Article downvoted"
            
        elif request.action == "undownvote":
            # Remove downvote
            success = True
            article.flags = article.flags or {}
            article.flags.pop("downvoted", None)
            # Skip event tracking for undownvote to avoid DB constraint issues
            # from .store import Event
            # event = Event(
            #     article_id=article.id,
            #     user_id='owner',  # Default user for now
            #     type='undownvote'  # Not allowed by DB constraint
            # )
            # db.add(event)
            db.commit()
            message = "Downvote removed"
            
        elif request.action == "label_add" and request.label:
            # Add label locally (don't sync with FreshRSS)
            success = True
            article.flags = article.flags or {}
            article.flags[request.label] = True
            # Add event tracking
            from .store import Event
            event = Event(
                article_id=article.id,
                user_id='owner',
                type='label_add'
            )
            db.add(event)
            db.commit()
            message = f"Label '{request.label}' added locally"
            
        elif request.action == "label_remove" and request.label:
            # Remove label locally (don't sync with FreshRSS)
            success = True
            article.flags = article.flags or {}
            article.flags.pop(request.label, None)
            # Skip event tracking for label_remove to avoid DB constraint issues
            # Event type 'label_remove' not allowed by database constraint
            db.commit()
            message = f"Label '{request.label}' removed locally"
    
    finally:
        # Only close client if it was created
        if client is not None:
            client.client.close()
    
    if not success:
        raise HTTPException(status_code=500, detail="Action failed")
    
    return {"success": success, "message": message}

@app.post("/refresh", response_model=RefreshResponse)
async def trigger_refresh():
    """Manually trigger poll and score"""
    result = await scheduler.poll_and_score()
    
    return RefreshResponse(
        status="completed",
        new_entries=result["new_entries"],
        scored=result["scored"],
        timestamp=datetime.utcnow()
    )

@app.get("/admin/downvoted")
async def get_downvoted_articles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get articles that have been downvoted for admin review"""
    from sqlalchemy import and_
    from .store import Article as ArticleModel  # SpamReport disabled
    
    # Query articles with downvoted flag (spam filtering disabled)
    query = db.query(ArticleModel).filter(
        ArticleModel.flags.op('->>')('downvoted') == 'true'
    ).order_by(ArticleModel.created_at.desc())
    
    total = query.count()
    articles = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Convert to response format
    article_data = []
    for article in articles:
        article_data.append({
            "id": article.id,
            "freshrss_entry_id": article.freshrss_entry_id,
            "title": article.title,
            "url": article.url,
            "content": article.content,
            "source": article.source,
            "published_at": article.published_at,
            "score_total": article.score_total,
            "scores": article.scores,
            "flags": article.flags,
            "created_at": article.created_at,
            "extraction_status": article.extraction_status,
            "full_content": article.full_content
        })
    
    return {
        "items": article_data,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@app.get("/trending")
async def get_trending_articles(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back for trending"),
    min_score: int = Query(50, description="Minimum score threshold"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles to return"),
    db: Session = Depends(get_db)
):
    """Get trending articles based on recent engagement and high scores"""
    from sqlalchemy import and_, func
    from .store import Article as ArticleModel, Event  # SpamReport disabled
    from datetime import datetime, timezone, timedelta
    
    # Calculate cutoff time
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get articles with engagement in the last N hours
    trending_query = db.query(
        ArticleModel,
        func.count(Event.id).label('engagement_count'),
        func.count(func.nullif(Event.event_type, 'impression')).label('active_engagement'),
        func.coalesce(func.sum(
            func.case(
                [(Event.event_type == 'star', 5),
                 (Event.event_type == 'external_click', 3),
                 (Event.event_type == 'open', 2),
                 (Event.event_type == 'downvote', -3)],
                else_=1
            )
        ), 0).label('weighted_engagement')
    ).outerjoin(
        Event, 
        and_(Event.article_id == ArticleModel.id, Event.created_at >= cutoff)
    ).filter(
        ArticleModel.score_total >= min_score,
        ArticleModel.published_at >= cutoff  # Only recent articles (spam filtering disabled)
    ).group_by(ArticleModel.id).order_by(
        func.coalesce(func.sum(
            func.case(
                [(Event.event_type == 'star', 5),
                 (Event.event_type == 'external_click', 3),
                 (Event.event_type == 'open', 2),
                 (Event.event_type == 'downvote', -3)],
                else_=1
            )
        ), 0).desc(),
        ArticleModel.score_total.desc()
    ).limit(limit)
    
    results = trending_query.all()
    
    # Format response
    trending_articles = []
    for article, engagement_count, active_engagement, weighted_engagement in results:
        trending_articles.append({
            "id": article.id,
            "freshrss_entry_id": article.freshrss_entry_id,
            "title": article.title,
            "url": article.url,
            "content": article.content,
            "source": article.source,
            "published_at": article.published_at,
            "score_total": article.score_total,
            "scores": article.scores,
            "flags": article.flags,
            "topics": article.topics,
            "has_image": article.has_image,
            "image_proxy_path": article.image_proxy_path,
            "image_blurhash": article.image_blurhash,
            "engagement_count": engagement_count or 0,
            "active_engagement": active_engagement or 0,
            "weighted_engagement": float(weighted_engagement or 0),
            "trend_score": float(weighted_engagement or 0) + (article.score_total * 0.1),
            "created_at": article.created_at
        })
    
    return {
        "items": trending_articles,
        "total": len(trending_articles),
        "hours_back": hours,
        "min_score": min_score
    }

@app.get("/config", response_model=ConfigResponse)
async def get_config(db: Session = Depends(get_db)):
    """Get current scoring configuration"""
    scorer = ScoringEngine()
    store = ArticleStore(db)
    
    return ConfigResponse(
        scoring={
            "keywords": scorer.scoring_config.get("keywords", {}),
            "source_weights": scorer.scoring_config.get("source_weights", {}),
            "recency": scorer.scoring_config.get("recency", {})
        },
        thresholds=scorer.scoring_config.get("thresholds", {}),
        sources=store.get_unique_sources(),
        imageEnabled=True,
        imageProxyBase="/img"
    )

@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status"""
    return scheduler.get_status()

@app.get("/system/metrics")
async def get_system_metrics():
    """Get comprehensive system performance metrics"""
    try:
        # Database pool stats
        db_pool_stats = get_db_pool_stats()
        
        # Cache stats
        from .cache_service import cache_service
        cache_stats = cache_service.get_cache_stats()
        
        # Scheduler status
        scheduler_status = scheduler.get_status()
        
        return {
            "database_pool": db_pool_stats,
            "redis_cache": cache_stats,
            "scheduler": scheduler_status,
            "system_timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.get("/img/{h1}/{h2}/{filename}")
async def serve_image(h1: str, h2: str, filename: str):
    """Serve cached images from proxy cache"""
    cache_dir = Path(os.getenv('IMAGE_PROXY_CACHE_DIR', '/data/image-cache'))
    image_path = cache_dir / h1 / h2 / filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Determine content type from filename
    content_type = "image/jpeg"
    if filename.lower().endswith('.png'):
        content_type = "image/png"
    elif filename.lower().endswith('.webp'):
        content_type = "image/webp"
    
    return FileResponse(
        path=image_path,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{h1}{h2}{filename}"'
        }
    )

# Content extraction endpoints
@app.get("/articles/by-url")
async def get_article_by_url(url: str, db: Session = Depends(get_db)):
    """Find article by URL"""
    from .store import Article
    import sys
    print(f"DEBUG: Searching for URL: {repr(url)}", file=sys.stderr)
    
    article = db.query(Article).filter(Article.url == url).first()
    print(f"DEBUG: Article found: {article is not None}", file=sys.stderr)
    
    if not article:
        # Try to find any article with similar URL
        similar = db.query(Article).filter(Article.url.contains('genai-and-data-management')).first()
        print(f"DEBUG: Similar article: {similar is not None}", file=sys.stderr)
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {
        "id": article.id,
        "freshrss_entry_id": article.freshrss_entry_id,
        "title": article.title,
        "url": article.url,
        "source": article.source,
        "published_at": article.published_at.isoformat(),
        "score_total": article.score_total
    }

@app.get("/articles/{article_id}/content")
async def get_article_content(article_id: int, db: Session = Depends(get_db)):
    """Get full extracted content for an article"""
    from .store import Article
    article = db.query(Article).filter_by(id=article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Return content if already extracted
    if article.extraction_status == 'success' and article.full_content:
        return {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "full_content": article.full_content,
            "content_html": article.content_html,
            "content_summary": article.content_summary,
            "content_keywords": article.content_keywords,
            "authors": article.authors,
            "top_image_url": article.top_image_url,
            "extracted_at": article.extracted_at,
            "extraction_status": article.extraction_status
        }
    
    # If not extracted, return status
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "extraction_status": article.extraction_status,
        "extraction_error": article.extraction_error
    }

@app.post("/articles/{article_id}/extract")
async def trigger_article_extraction(
    article_id: int,
    force: bool = Query(False, description="Force re-extraction even if already extracted"),
    db: Session = Depends(get_db)
):
    """Trigger content extraction for a specific article"""
    from .store import Article
    article = db.query(Article).filter_by(id=article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Check if already extracted
    if not force and article.extraction_status == 'success':
        return {
            "status": "already_extracted",
            "message": "Article content already extracted. Use force=true to re-extract."
        }
    
    # Trigger extraction
    extraction_service = ContentExtractionService(
        db=db,
        max_concurrent=1,
        rate_limit=settings.content_extraction_rate_limit
    )
    
    try:
        result = await extraction_service.extract_article_content(article, force=force)
        
        if result:
            return {
                "status": "success",
                "message": "Content extracted successfully",
                "data": result
            }
        else:
            return {
                "status": "failed",
                "message": "Content extraction failed",
                "error": article.extraction_error
            }
    finally:
        await extraction_service.close()

@app.post("/extraction/batch")
async def trigger_batch_extraction(
    article_ids: list[int],
    force: bool = Query(False, description="Force re-extraction"),
    db: Session = Depends(get_db)
):
    """Trigger content extraction for multiple articles"""
    stats = await extraction_worker.process_specific_articles(article_ids, force=force)
    return stats

@app.post("/extraction/process-pending")
async def process_pending_extractions(
    limit: Optional[int] = Query(None, description="Maximum number of articles to process"),
    min_score: Optional[int] = Query(None, description="Minimum score required")
):
    """Process pending content extractions"""
    stats = await extraction_worker.process_extraction_queue()
    return stats

@app.get("/extraction/status")
async def get_extraction_status():
    """Get extraction worker status"""
    return extraction_worker.get_status()

@app.get("/extraction/stats", response_model=dict)
async def get_extraction_stats(db: Session = Depends(get_db)):
    """Get extraction statistics"""
    from sqlalchemy import func
    from .store import Article
    
    # Count articles by extraction status
    status_counts = db.query(
        Article.extraction_status,
        func.count(Article.id)
    ).group_by(Article.extraction_status).all()
    
    # Count articles with content
    with_content = db.query(Article).filter(
        Article.full_content.isnot(None)
    ).count()
    
    # Total articles
    total = db.query(Article).count()
    
    return {
        "total_articles": total,
        "with_content": with_content,
        "status_breakdown": dict(status_counts),
        "extraction_rate": (with_content / total * 100) if total > 0 else 0
    }

# Image diagnostics endpoints
@app.get("/diagnostics/images")
async def get_image_diagnostics(
    days: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get image extraction diagnostics"""
    from sqlalchemy import func, text
    from datetime import timedelta
    from .store import ImageDiagnostic, Article
    
    # Calculate date threshold
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Domain statistics
    domain_stats = db.query(
        ImageDiagnostic.domain,
        ImageDiagnostic.reason,
        func.count(ImageDiagnostic.id).label('count')
    ).filter(
        ImageDiagnostic.created_at >= since_date
    ).group_by(
        ImageDiagnostic.domain, ImageDiagnostic.reason
    ).order_by(
        func.count(ImageDiagnostic.id).desc()
    ).limit(50).all()
    
    # Success rate by domain
    success_by_domain = db.execute(text("""
        SELECT 
            SUBSTRING(a.url FROM 'https?://([^/]+)') as domain,
            COUNT(*) as total_articles,
            SUM(CASE WHEN a.has_image THEN 1 ELSE 0 END) as with_images,
            ROUND(100.0 * SUM(CASE WHEN a.has_image THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
        FROM articles a
        WHERE a.created_at >= :since_date
        GROUP BY SUBSTRING(a.url FROM 'https?://([^/]+)')
        HAVING COUNT(*) >= 5
        ORDER BY COUNT(*) DESC
        LIMIT 20
    """), {"since_date": since_date}).fetchall()
    
    # Image stages distribution
    stage_stats = db.query(
        Article.image_stage,
        func.count(Article.id).label('count')
    ).filter(
        Article.created_at >= since_date,
        Article.image_stage.isnot(None)
    ).group_by(Article.image_stage).all()
    
    # Overall stats
    total_recent = db.query(Article).filter(Article.created_at >= since_date).count()
    with_images = db.query(Article).filter(
        Article.created_at >= since_date,
        Article.has_image == True
    ).count()
    
    return {
        "period_days": days,
        "total_articles": total_recent,
        "articles_with_images": with_images,
        "overall_success_rate": round(100.0 * with_images / total_recent, 2) if total_recent > 0 else 0,
        "domain_failures": [
            {"domain": row[0], "reason": row[1], "count": row[2]}
            for row in domain_stats
        ],
        "domain_success_rates": [
            {"domain": row[0], "total": row[1], "with_images": row[2], "success_rate": row[3]}
            for row in success_by_domain
        ],
        "extraction_stages": [
            {"stage": row[0] or "unknown", "count": row[1]}
            for row in stage_stats
        ]
    }

@app.post("/images/recache")
async def recache_images(
    hours: int = Query(24, description="Recache images from last N hours"),
    force: bool = Query(False, description="Force recache even if fresh"),
    db: Session = Depends(get_db)
):
    """Trigger recaching of recent images"""
    from datetime import timedelta
    from .content_service_v2 import ContentExtractionServiceV2
    from .store import Article
    
    since_date = datetime.utcnow() - timedelta(hours=hours)
    
    # Get articles to reprocess
    query = db.query(Article).filter(Article.created_at >= since_date)
    
    if not force:
        # Only reprocess failed or missing images
        query = query.filter(
            (Article.has_image == False) | (Article.image_stage.is_(None))
        )
    
    articles = query.limit(100).all()  # Limit to avoid overload
    
    if not articles:
        return {"message": "No articles to reprocess", "count": 0}
    
    # Process with enhanced service
    service = ContentExtractionServiceV2(db)
    print(f"INFO: About to process {len(articles)} articles with ContentExtractionServiceV2")
    try:
        stats = await service.process_articles_batch(articles, force=force)
        return {
            "message": f"Reprocessed {len(articles)} articles",
            "stats": stats
        }
    finally:
        await service.close()


# WebSocket Endpoints
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await connection_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await connection_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@app.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return connection_manager.get_stats()


# Notification Endpoints
@app.post("/api/notifications/send")
async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None,
    priority: str = "normal",
    channels: list[str] = None
):
    """Send notification to user"""
    try:
        notif_type = NotificationType(notification_type)
        notif_priority = NotificationPriority(priority)
        channel_set = set(channels) if channels else {"websocket"}
        
        notification_id = await notification_manager.send_notification(
            user_id=user_id,
            notification_type=notif_type,
            title=title,
            message=message,
            data=data or {},
            priority=notif_priority,
            channels=channel_set
        )
        
        return {"status": "success", "notification_id": notification_id}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {e}")


@app.get("/api/notifications/{user_id}")
async def get_user_notifications(
    user_id: str,
    limit: int = Query(50, le=100),
    unread_only: bool = Query(False)
):
    """Get notifications for user"""
    notifications = notification_manager.get_user_notifications(
        user_id=user_id,
        limit=limit,
        unread_only=unread_only
    )
    return {"notifications": notifications}


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str):
    """Mark notification as read"""
    success = await notification_manager.mark_read(notification_id, user_id)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Notification not found")


@app.post("/api/notifications/{user_id}/preferences")
async def set_notification_preferences(user_id: str, preferences: dict):
    """Set user notification preferences"""
    notification_manager.set_user_preferences(user_id, preferences)
    return {"status": "success"}


@app.get("/api/notifications/stats")
async def get_notification_stats():
    """Get notification system statistics"""
    return notification_manager.get_stats()


# Test notification endpoints for development
@app.post("/api/notifications/test/breaking-news")
async def test_breaking_news(user_id: str = "test-user"):
    """Send test breaking news notification"""
    from .notifications import send_breaking_news_alert
    await send_breaking_news_alert(user_id, {
        "title": "Test Breaking News Alert",
        "url": "https://example.com/test-article",
        "score": 9.2,
        "source": "Test Source"
    })
    return {"status": "Test breaking news sent"}


@app.post("/api/notifications/test/high-score")
async def test_high_score(user_id: str = "test-user"):
    """Send test high score notification"""
    from .notifications import send_high_score_alert
    await send_high_score_alert(user_id, {
        "title": "Test High Score Article",
        "url": "https://example.com/high-score-article", 
        "score": 8.7,
        "source": "Test Source"
    })
    return {"status": "Test high score notification sent"}


@app.post("/api/notifications/test/trend")
async def test_trend_alert(user_id: str = "test-user"):
    """Send test trend notification"""
    from .notifications import send_trend_alert
    await send_trend_alert(user_id, {
        "trend_name": "AI Breakthrough",
        "article_count": 15,
        "confidence": 0.87
    })
    return {"status": "Test trend alert sent"}