"""
Spotlight API endpoints for daily digests
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import date
import json

from ..deps import get_db
from ..store import SpotlightIssue, SpotlightItem, Article, Story
from ..spotlight_engine import SpotlightEngine

router = APIRouter()


@router.get("/today")
async def get_today_spotlight(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get today's spotlight digest"""
    
    engine = SpotlightEngine(db)
    today = date.today()
    
    # Try to get existing issue
    issue = db.query(SpotlightIssue).filter_by(issue_date=today).first()
    
    if not issue:
        # Generate new issue
        issue = engine.generate_digest(today)
    
    return engine.export_as_json(issue)


@router.get("/config")
async def get_spotlight_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get current spotlight configuration"""
    
    engine = SpotlightEngine(db)
    return engine.config


@router.get("/stats")
async def get_spotlight_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get spotlight generation statistics"""
    
    total_issues = db.query(SpotlightIssue).count()
    published_issues = db.query(SpotlightIssue).filter_by(published=True).count()
    
    # Get latest issue metrics
    latest_issue = db.query(SpotlightIssue).order_by(
        SpotlightIssue.issue_date.desc()
    ).first()
    
    return {
        "total_issues": total_issues,
        "published_issues": published_issues,
        "unpublished_issues": total_issues - published_issues,
        "latest_issue": {
            "date": latest_issue.issue_date.isoformat() if latest_issue else None,
            "title": latest_issue.title if latest_issue else None,
            "published": latest_issue.published if latest_issue else None,
            "metrics": latest_issue.metrics if latest_issue else None
        } if latest_issue else None
    }


@router.get("/{issue_date}")
async def get_spotlight_by_date(issue_date: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get spotlight digest for specific date (YYYY-MM-DD)"""
    
    try:
        target_date = date.fromisoformat(issue_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    issue = db.query(SpotlightIssue).filter_by(issue_date=target_date).first()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Spotlight digest not found for this date")
    
    engine = SpotlightEngine(db)
    return engine.export_as_json(issue)


@router.post("/generate")
async def generate_spotlight(
    target_date: Optional[str] = None,
    force: bool = False,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Manually generate a spotlight digest"""
    
    if target_date:
        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        parsed_date = date.today()
    
    # Check if issue already exists
    existing = db.query(SpotlightIssue).filter_by(issue_date=parsed_date).first()
    
    if existing and not force:
        raise HTTPException(
            status_code=409, 
            detail=f"Spotlight digest already exists for {parsed_date}. Use force=true to regenerate."
        )
    
    # Delete existing if force regeneration
    if existing and force:
        db.delete(existing)
        db.commit()
    
    engine = SpotlightEngine(db)
    issue = engine.generate_digest(parsed_date)
    
    return {
        "success": True,
        "issue_id": issue.id,
        "issue_date": issue.issue_date.isoformat(),
        "title": issue.title,
        "must_read_count": len([i for i in issue.items if i.section == 'must_read']),
        "also_worth_count": len([i for i in issue.items if i.section == 'also_worth']),
        "metrics": issue.metrics
    }


@router.post("/{issue_id}/publish")
async def publish_spotlight(issue_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Mark a spotlight issue as published"""
    
    engine = SpotlightEngine(db)
    success = engine.publish_issue(issue_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Spotlight issue not found")
    
    return {"success": True, "message": "Issue published successfully"}


@router.get("/rss/feed")
async def get_spotlight_rss_feed(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get RSS feed of published spotlight issues"""
    
    # Get recent published issues
    issues = db.query(SpotlightIssue).filter_by(
        published=True
    ).order_by(SpotlightIssue.issue_date.desc()).limit(limit).all()
    
    if not issues:
        raise HTTPException(status_code=404, detail="No published spotlight issues found")
    
    # Use the most recent issue for RSS generation
    engine = SpotlightEngine(db)
    rss_content = engine.export_as_rss(issues[0])
    
    return Response(
        content=rss_content,
        media_type="application/rss+xml",
        headers={"Content-Disposition": "attachment; filename=spotlight-feed.xml"}
    )