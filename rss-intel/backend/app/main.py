from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pathlib import Path
import os

from .deps import get_db
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
from .ml.api_recommend import router as recommend_router
# from .ml.api_events import router as ml_events_router  # Events have issues, keep disabled
# from .api.events import router as events_router  # Events have issues, keep disabled
from .api.personalization import router as personalization_router
from .api.search import router as search_router
from .api.stories import router as stories_router
from .api.spotlight import router as spotlight_router
from .api.recommend_simple import router as recommend_simple_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting RSS Intelligence Backend...")
    scheduler.start()
    yield
    # Shutdown
    print("Shutting down...")
    scheduler.stop()

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
# app.include_router(ml_events_router, prefix="/api/ml", tags=["ml-events"])  # Events have issues, keep disabled
# app.include_router(events_router, prefix="/api", tags=["events"])  # Events have issues, keep disabled  
app.include_router(personalization_router, prefix="/api", tags=["personalization"])
app.include_router(search_router, tags=["search"])
app.include_router(stories_router, tags=["stories"])
app.include_router(spotlight_router, prefix="/api/spotlight", tags=["spotlight"])

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
    
    return HealthResponse(
        status="healthy" if all(v in ["healthy", "running"] for v in services.values()) else "degraded",
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
    articles, total = store.get_articles(
        min_score=min_score,
        label=label,
        source=source,
        query=q,
        has_image=has_image,
        page=page,
        page_size=page_size
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
            
        elif request.action == "label_add" and request.label:
            success = client.add_label(entry_id, request.label)
            if success:
                article.flags = article.flags or {}
                article.flags[request.label] = True
                db.commit()
            message = f"Label '{request.label}' added"
            
        elif request.action == "label_remove" and request.label:
            success = client.remove_label(entry_id, request.label)
            if success:
                article.flags = article.flags or {}
                article.flags.pop(request.label, None)
                db.commit()
            message = f"Label '{request.label}' removed"
    
    finally:
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