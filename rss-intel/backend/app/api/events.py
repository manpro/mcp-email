"""
Events API for tracking user interactions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from ..deps import get_db
from ..store import Event, Article

router = APIRouter()


class EventCreate(BaseModel):
    """Event creation model"""
    article_id: int
    event_type: str = Field(..., pattern="^(impression|open|external_click|star|dismiss|mark_read|label_add|label_remove)$")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration in milliseconds")
    visible_ms: Optional[int] = Field(None, ge=0, description="Time visible on screen in milliseconds") 
    scroll_pct: Optional[float] = Field(None, ge=0, le=100, description="Scroll percentage (0-100)")


class EventResponse(BaseModel):
    """Event response model"""
    id: int
    article_id: int
    event_type: str
    duration_ms: Optional[int]
    visible_ms: Optional[int]
    scroll_pct: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventsStats(BaseModel):
    """Events statistics"""
    total_events: int
    events_by_type: dict
    avg_duration_ms: Optional[float]
    avg_visible_ms: Optional[float]
    avg_scroll_pct: Optional[float]


@router.post("/events", response_model=EventResponse)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new user event"""
    
    # Verify article exists
    article = db.query(Article).filter_by(id=event.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Create event
    db_event = Event(
        article_id=event.article_id,
        event_type=event.event_type,
        duration_ms=event.duration_ms,
        visible_ms=event.visible_ms,
        scroll_pct=event.scroll_pct
    )
    
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return db_event


@router.post("/events/batch")
async def create_events_batch(events: List[EventCreate], db: Session = Depends(get_db)):
    """Create multiple events in batch"""
    
    created_events = []
    for event_data in events:
        # Verify article exists
        article = db.query(Article).filter_by(id=event_data.article_id).first()
        if not article:
            continue  # Skip invalid articles in batch
        
        db_event = Event(
            article_id=event_data.article_id,
            event_type=event_data.event_type,
            duration_ms=event_data.duration_ms,
            visible_ms=event_data.visible_ms,
            scroll_pct=event_data.scroll_pct
        )
        
        db.add(db_event)
        created_events.append(db_event)
    
    db.commit()
    
    return {
        "created": len(created_events),
        "total_requested": len(events)
    }


@router.get("/events/stats", response_model=EventsStats)
async def get_events_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get events statistics"""
    
    from datetime import timedelta
    from sqlalchemy import func
    
    # Calculate date range
    since_date = datetime.utcnow() - timedelta(days=days)
    
    # Total events
    total_events = db.query(Event).filter(Event.created_at >= since_date).count()
    
    # Events by type
    events_by_type = dict(
        db.query(Event.event_type, func.count(Event.id))
        .filter(Event.created_at >= since_date)
        .group_by(Event.event_type)
        .all()
    )
    
    # Average metrics
    duration_avg = db.query(func.avg(Event.duration_ms)).filter(
        Event.created_at >= since_date,
        Event.duration_ms.isnot(None)
    ).scalar()
    
    visible_avg = db.query(func.avg(Event.visible_ms)).filter(
        Event.created_at >= since_date,
        Event.visible_ms.isnot(None)
    ).scalar()
    
    scroll_avg = db.query(func.avg(Event.scroll_pct)).filter(
        Event.created_at >= since_date,
        Event.scroll_pct.isnot(None)
    ).scalar()
    
    return EventsStats(
        total_events=total_events,
        events_by_type=events_by_type,
        avg_duration_ms=float(duration_avg) if duration_avg else None,
        avg_visible_ms=float(visible_avg) if visible_avg else None,
        avg_scroll_pct=float(scroll_avg) if scroll_avg else None
    )


@router.get("/events/{article_id}")
async def get_article_events(
    article_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get events for a specific article"""
    
    # Verify article exists
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    events = db.query(Event)\
        .filter_by(article_id=article_id)\
        .order_by(Event.created_at.desc())\
        .limit(limit)\
        .all()
    
    return {
        "article_id": article_id,
        "events": events,
        "total": len(events)
    }