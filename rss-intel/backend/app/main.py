from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

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
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get filtered list of articles"""
    store = ArticleStore(db)
    articles, total = store.get_articles(
        min_score=min_score,
        label=label,
        source=source,
        query=q,
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
        sources=store.get_unique_sources()
    )

@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status"""
    return scheduler.get_status()