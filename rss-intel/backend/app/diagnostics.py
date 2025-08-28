#!/usr/bin/env python3
"""
Diagnostics endpoint for tracking article pipeline
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
import logging

from .deps import get_db
from .store import Article, Story, DailyBriefing, BriefingItem
from .briefing_engine import BriefingEngine

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/diagnostics/article-pipeline")
async def article_pipeline_diagnostics(
    hours_back: int = Query(24, description="Hours back to analyze"),
    include_sources: bool = Query(True, description="Include source breakdown"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Comprehensive diagnostics for article pipeline from ingestion to briefing
    """
    
    # Calculate time window
    now = datetime.utcnow()
    start_time = now - timedelta(hours=hours_back)
    
    # 1. INGESTION STATS - All articles ingested
    total_ingested = db.query(Article).filter(
        Article.created_at >= start_time
    ).count()
    
    # Source breakdown for ingestion
    ingestion_by_source = []
    if include_sources:
        source_counts = db.query(
            Article.source,
            func.count(Article.id).label('count')
        ).filter(
            Article.created_at >= start_time
        ).group_by(Article.source).order_by(func.count(Article.id).desc()).all()
        
        ingestion_by_source = [
            {"source": source, "count": count}
            for source, count in source_counts
        ]
    
    # 2. SCORING STATS - Articles after scoring
    articles_with_scores = db.query(Article).filter(
        Article.created_at >= start_time,
        Article.score_total.isnot(None)
    ).all()
    
    # Score distribution
    score_ranges = {
        "negative": len([a for a in articles_with_scores if a.score_total < 0]),
        "0-10": len([a for a in articles_with_scores if 0 <= a.score_total < 10]),
        "10-30": len([a for a in articles_with_scores if 10 <= a.score_total < 30]),
        "30-60": len([a for a in articles_with_scores if 30 <= a.score_total < 60]),
        "60-100": len([a for a in articles_with_scores if 60 <= a.score_total < 100]),
        "100+": len([a for a in articles_with_scores if a.score_total >= 100])
    }
    
    # 3. SPAM FILTERING STATS
    spam_articles = db.query(Article).filter(
        Article.created_at >= start_time,
        Article.score_total < 0
    ).count()
    
    auto_hidden = db.query(Article).filter(
        Article.created_at >= start_time,
        Article.flags.op('->>')('auto_hidden') == 'true'
    ).count()
    
    # 4. CONTENT QUALITY STATS
    articles_with_content = {
        "full_content": db.query(Article).filter(
            Article.created_at >= start_time,
            Article.full_content.isnot(None)
        ).count(),
        "content_summary": db.query(Article).filter(
            Article.created_at >= start_time,
            Article.content_summary.isnot(None)
        ).count(),
        "basic_content": db.query(Article).filter(
            Article.created_at >= start_time,
            Article.content.isnot(None)
        ).count()
    }
    
    # 5. TOPIC CLASSIFICATION
    topic_stats = {}
    all_articles = db.query(Article).filter(
        Article.created_at >= start_time,
        Article.topics.isnot(None)
    ).all()
    
    topic_counts = {}
    for article in all_articles:
        if article.topics:
            for topic in article.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    topic_stats = dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    
    # 6. BRIEFING ELIGIBILITY
    # Simulate what briefing engine would consider
    briefing_eligible = db.query(Article).filter(
        Article.published_at >= start_time,
        Article.score_total >= 0,  # Not spam
        and_(
            Article.full_content.isnot(None) |
            Article.content_summary.isnot(None) |
            (Article.content.isnot(None) & (func.length(Article.content) > 50))
        )
    ).all()
    
    # 7. ACTUAL BRIEFING USAGE
    briefings_today = db.query(DailyBriefing).filter(
        DailyBriefing.briefing_date >= date.today() - timedelta(days=1)
    ).all()
    
    briefing_articles_used = []
    for briefing in briefings_today:
        items = db.query(BriefingItem).filter_by(briefing_id=briefing.id).all()
        for item in items:
            briefing_articles_used.append(item.article_id)
    
    # Find top scoring articles that DIDN'T make it to briefings
    unused_high_scorers = []
    for article in sorted(briefing_eligible, key=lambda x: x.score_total or 0, reverse=True)[:20]:
        if article.id not in briefing_articles_used:
            unused_high_scorers.append({
                "id": article.id,
                "title": article.title,
                "source": article.source,
                "score": article.score_total,
                "topics": article.topics,
                "published_at": article.published_at.isoformat(),
                "has_content": bool(article.full_content or article.content_summary)
            })
    
    return {
        "time_window": {
            "hours_back": hours_back,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat()
        },
        "pipeline_stats": {
            "1_total_ingested": total_ingested,
            "2_scored_articles": len(articles_with_scores),
            "3_spam_filtered": spam_articles,
            "4_auto_hidden": auto_hidden,
            "5_briefing_eligible": len(briefing_eligible),
            "6_used_in_briefings": len(set(briefing_articles_used))
        },
        "score_distribution": score_ranges,
        "content_quality": articles_with_content,
        "topic_distribution": topic_stats,
        "source_breakdown": ingestion_by_source[:20],
        "unused_high_scorers": unused_high_scorers[:10],
        "briefings_created": len(briefings_today)
    }

@router.get("/diagnostics/source-health")
async def source_health_check(
    days_back: int = Query(7, description="Days back to analyze"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check health of RSS sources - which are active, inactive, or broken
    """
    
    start_time = datetime.utcnow() - timedelta(days=days_back)
    
    # Get configured sources from database (we'd need to add a sources table)
    # For now, we'll analyze based on what we've seen
    source_stats = db.query(
        Article.source,
        func.count(Article.id).label('total_articles'),
        func.max(Article.created_at).label('last_article'),
        func.avg(Article.score_total).label('avg_score'),
        func.count(func.nullif(Article.score_total < 0, False)).label('spam_count')
    ).filter(
        Article.created_at >= start_time
    ).group_by(Article.source).all()
    
    source_health = []
    for source, total, last_article, avg_score, spam_count in source_stats:
        hours_since_last = (datetime.utcnow() - last_article).total_seconds() / 3600
        
        # Determine health status
        if hours_since_last > 168:  # 7 days
            status = "DEAD"
        elif hours_since_last > 72:  # 3 days
            status = "STALE"
        elif spam_count and (spam_count / total) > 0.5:
            status = "SPAM"
        elif total < 5:
            status = "LOW_VOLUME"
        else:
            status = "HEALTHY"
            
        source_health.append({
            "source": source,
            "status": status,
            "total_articles": total,
            "hours_since_last": round(hours_since_last, 1),
            "avg_score": round(float(avg_score or 0), 1),
            "spam_ratio": round((spam_count or 0) / total, 2) if total > 0 else 0
        })
    
    return {
        "time_window_days": days_back,
        "sources_analyzed": len(source_health),
        "source_health": sorted(source_health, key=lambda x: x['total_articles'], reverse=True)
    }