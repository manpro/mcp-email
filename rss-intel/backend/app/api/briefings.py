#!/usr/bin/env python3
"""
Daily Briefings API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import date, datetime, timedelta
import logging

from ..deps import get_db
from ..briefing_engine import BriefingEngine, generate_daily_briefings
from ..store import DailyBriefing

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/briefings/status")
async def get_briefings_status(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get status of briefings system"""
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Count briefings for today and yesterday
    today_briefings = db.query(DailyBriefing).filter_by(briefing_date=today).count()
    yesterday_briefings = db.query(DailyBriefing).filter_by(briefing_date=yesterday).count()
    
    # Get latest briefing
    latest_briefing = db.query(DailyBriefing).order_by(
        DailyBriefing.generated_at.desc()
    ).first()
    
    return {
        'today': {
            'date': today.isoformat(),
            'briefings_count': today_briefings,
            'expected_count': 3
        },
        'yesterday': {
            'date': yesterday.isoformat(),
            'briefings_count': yesterday_briefings
        },
        'latest_briefing': {
            'date': latest_briefing.briefing_date.isoformat() if latest_briefing else None,
            'time_slot': latest_briefing.time_slot if latest_briefing else None,
            'generated_at': latest_briefing.generated_at.isoformat() if latest_briefing else None
        } if latest_briefing else None,
        'time_slots': ['morning', 'lunch', 'evening']
    }


@router.get("/briefings/recent")
async def get_recent_briefings(
    days_back: int = Query(3, ge=1, le=7, description="Number of days to look back (1-7)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get recent briefings for the last N days"""
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back-1)
    
    briefings = db.query(DailyBriefing).filter(
        DailyBriefing.briefing_date >= start_date,
        DailyBriefing.briefing_date <= end_date
    ).order_by(
        DailyBriefing.briefing_date.desc(),
        DailyBriefing.time_slot
    ).all()
    
    # Group by date
    engine = BriefingEngine(db)
    briefings_by_date = {}
    
    for briefing in briefings:
        date_str = briefing.briefing_date.isoformat()
        if date_str not in briefings_by_date:
            briefings_by_date[date_str] = {}
        
        briefings_by_date[date_str][briefing.time_slot] = engine.export_briefing_as_json(briefing)
    
    return {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'briefings_by_date': briefings_by_date,
        'total_briefings': len(briefings)
    }


@router.get("/briefings/{briefing_date}")
async def get_briefings_for_date(
    briefing_date: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get all briefings (morning, lunch, evening) for a specific date"""
    
    try:
        target_date = datetime.strptime(briefing_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    engine = BriefingEngine(db)
    briefings = engine.get_briefings_for_date(target_date)
    
    result = {}
    for time_slot, briefing in briefings.items():
        if briefing:
            result[time_slot] = engine.export_briefing_as_json(briefing)
        else:
            result[time_slot] = None
    
    return {
        'date': briefing_date,
        'briefings': result
    }


@router.get("/briefings/{briefing_date}/{time_slot}")
async def get_briefing_by_slot(
    briefing_date: str,
    time_slot: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific briefing by date and time slot"""
    
    try:
        target_date = datetime.strptime(briefing_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if time_slot not in ['morning', 'lunch', 'evening']:
        raise HTTPException(status_code=400, detail="Invalid time slot. Use 'morning', 'lunch', or 'evening'")
    
    briefing = db.query(DailyBriefing).filter_by(
        briefing_date=target_date,
        time_slot=time_slot
    ).first()
    
    if not briefing:
        raise HTTPException(status_code=404, detail=f"No {time_slot} briefing found for {briefing_date}")
    
    engine = BriefingEngine(db)
    return engine.export_briefing_as_json(briefing)


@router.post("/briefings/{briefing_date}/{time_slot}/generate")
async def generate_briefing(
    briefing_date: str,
    time_slot: str,
    regenerate: bool = Query(False, description="Force regeneration if briefing already exists"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Generate a briefing for a specific date and time slot"""
    
    try:
        target_date = datetime.strptime(briefing_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if time_slot not in ['morning', 'lunch', 'evening']:
        raise HTTPException(status_code=400, detail="Invalid time slot. Use 'morning', 'lunch', or 'evening'")
    
    engine = BriefingEngine(db)
    
    # Check if already exists and handle regeneration
    if regenerate:
        existing = db.query(DailyBriefing).filter_by(
            briefing_date=target_date,
            time_slot=time_slot
        ).first()
        if existing:
            # Delete existing briefing and its items
            db.delete(existing)
            db.commit()
            logger.info(f"Deleted existing {time_slot} briefing for {briefing_date}")
    
    try:
        briefing = engine.generate_briefing(time_slot, target_date)
        return {
            'success': True,
            'briefing_id': briefing.id,
            'date': briefing_date,
            'time_slot': time_slot,
            'items_count': len(briefing.items) if briefing.items else 0,
            'generated_at': briefing.generated_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to generate {time_slot} briefing for {briefing_date}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate briefing: {str(e)}")


@router.post("/briefings/{briefing_date}/generate-all")
async def generate_all_briefings_for_date(
    briefing_date: str,
    regenerate: bool = Query(False, description="Force regeneration if briefings already exist"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Generate all briefings (morning, lunch, evening) for a specific date"""
    
    try:
        target_date = datetime.strptime(briefing_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    engine = BriefingEngine(db)
    
    # Handle regeneration if requested
    if regenerate:
        existing_briefings = db.query(DailyBriefing).filter_by(
            briefing_date=target_date
        ).all()
        for briefing in existing_briefings:
            db.delete(briefing)
        if existing_briefings:
            db.commit()
            logger.info(f"Deleted {len(existing_briefings)} existing briefings for {briefing_date}")
    
    results = generate_daily_briefings(db, target_date)
    
    return {
        'date': briefing_date,
        'results': results,
        'success_count': results['total_success']
    }