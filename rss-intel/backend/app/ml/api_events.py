"""Event tracking API endpoints"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Event models
class EventData(BaseModel):
    article_id: int
    type: str = Field(..., pattern="^(impression|open|external_click|star|label_add|dismiss|mark_read|downvote|undownvote)$")
    duration_ms: Optional[int] = None
    visible_ms: Optional[int] = None
    scroll_pct: Optional[int] = Field(None, ge=0, le=100)
    ts: Optional[datetime] = None

class EventsBatchRequest(BaseModel):
    events: List[EventData]
    user_id: str = "owner"

class EventResponse(BaseModel):
    success: bool
    events_processed: int
    errors: Optional[List[str]] = None

@router.post("/events", response_model=EventResponse)
async def track_events(
    request: EventsBatchRequest,
    db: Session = Depends(get_db)
) -> EventResponse:
    """
    Track user interaction events in batch
    
    Events are used for:
    - Training labels (positive/negative feedback)
    - User preference modeling
    - A/B testing metrics
    """
    logger.info(f"Tracking {len(request.events)} events for user {request.user_id}")
    
    if not request.events:
        return EventResponse(success=True, events_processed=0)
    
    processed_count = 0
    errors = []
    
    try:
        for event_data in request.events:
            try:
                # Validate article exists
                article_check = db.execute(text("""
                    SELECT id FROM articles WHERE id = :article_id
                """), {"article_id": event_data.article_id})
                
                if not article_check.fetchone():
                    errors.append(f"Article {event_data.article_id} not found")
                    continue
                
                # Insert event
                event_time = event_data.ts or datetime.utcnow()
                
                db.execute(text("""
                    INSERT INTO events (article_id, user_id, type, duration_ms, visible_ms, scroll_pct, created_at)
                    VALUES (:article_id, :user_id, :type, :duration_ms, :visible_ms, :scroll_pct, :created_at)
                """), {
                    "article_id": event_data.article_id,
                    "user_id": request.user_id,
                    "type": event_data.type,
                    "duration_ms": event_data.duration_ms,
                    "visible_ms": event_data.visible_ms,
                    "scroll_pct": event_data.scroll_pct,
                    "created_at": event_time
                })
                
                processed_count += 1
                
                # Commit in batches for performance
                if processed_count % 10 == 0:
                    db.commit()
                    
            except Exception as e:
                errors.append(f"Event {event_data.article_id}:{event_data.type} - {str(e)}")
                logger.error(f"Error processing event: {e}")
                continue
        
        # Final commit
        db.commit()
        
        logger.info(f"Successfully processed {processed_count}/{len(request.events)} events")
        
        return EventResponse(
            success=True,
            events_processed=processed_count,
            errors=errors if errors else None
        )
        
    except Exception as e:
        logger.error(f"Batch event processing error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/stats")
async def get_event_stats(
    user_id: str = "owner",
    days_back: int = 7,
    db: Session = Depends(get_db)
) -> Dict:
    """Get event statistics for user"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    result = db.execute(text("""
        SELECT 
            type,
            COUNT(*) as count,
            AVG(duration_ms) FILTER (WHERE duration_ms > 0) as avg_duration
        FROM events 
        WHERE user_id = :user_id 
        AND created_at > :cutoff_date
        GROUP BY type
        ORDER BY count DESC
    """), {"user_id": user_id, "cutoff_date": cutoff_date})
    
    stats = {}
    total_events = 0
    
    for row in result:
        stats[row.type] = {
            "count": row.count,
            "avg_duration_ms": int(row.avg_duration) if row.avg_duration else None
        }
        total_events += row.count
    
    return {
        "user_id": user_id,
        "days_back": days_back,
        "total_events": total_events,
        "by_type": stats,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/events/impression")
async def track_impression(
    article_ids: List[int],
    user_id: str = "owner",
    db: Session = Depends(get_db)
) -> Dict:
    """Quick impression tracking for article views"""
    
    events = [
        EventData(article_id=aid, type="impression")
        for aid in article_ids
    ]
    
    request = EventsBatchRequest(events=events, user_id=user_id)
    response = await track_events(request, db)
    
    return {
        "success": response.success,
        "impressions_tracked": response.events_processed
    }

@router.post("/events/interaction")
async def track_single_interaction(
    article_id: int,
    event_type: str,
    duration_ms: Optional[int] = None,
    user_id: str = "owner",
    db: Session = Depends(get_db)
) -> Dict:
    """Track single interaction event"""
    
    if event_type not in ["open", "external_click", "star", "dismiss", "mark_read", "downvote", "undownvote"]:
        raise HTTPException(status_code=400, detail="Invalid event type")
    
    event = EventData(
        article_id=article_id,
        type=event_type,
        duration_ms=duration_ms
    )
    
    request = EventsBatchRequest(events=[event], user_id=user_id)
    response = await track_events(request, db)
    
    return {
        "success": response.success,
        "event_type": event_type,
        "article_id": article_id
    }