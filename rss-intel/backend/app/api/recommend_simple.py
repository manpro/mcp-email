"""Simple rule-based recommendations API"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..deps import get_db

router = APIRouter()

@router.get("/recommend-simple")
async def get_simple_recommendations(
    limit: int = Query(10, ge=1, le=100),
    user_id: str = Query("owner"),
    db: Session = Depends(get_db)
) -> Dict:
    # Convert Query objects to actual values
    limit = int(limit) if not isinstance(limit, int) else limit
    user_id = str(user_id) if not isinstance(user_id, str) else user_id
    """
    Get simple rule-based recommendations
    Uses score_total, recency, and diversity to recommend articles
    """
    
    # Get recent high-scoring articles with variety
    result = db.execute(text("""
        WITH scored_articles AS (
            SELECT 
                i.id,
                i.title,
                i.url,
                i.source,
                i.published_at,
                i.score_total,
                i.has_image,
                i.topics,
                -- Boost score for recent articles
                CASE 
                    WHEN i.published_at > NOW() - INTERVAL '1 day' THEN i.score_total * 1.5
                    WHEN i.published_at > NOW() - INTERVAL '3 days' THEN i.score_total * 1.2
                    ELSE i.score_total
                END as boosted_score,
                -- Check if user has interacted with this article
                CASE 
                    WHEN EXISTS(
                        SELECT 1 FROM events e 
                        WHERE e.article_id = i.id 
                        AND e.user_id = :user_id 
                        AND e.type IN ('open', 'star', 'external_click')
                    ) THEN 0
                    ELSE 1
                END as is_unseen
            FROM articles i
            WHERE i.published_at > NOW() - INTERVAL '14 days'
            AND i.score_total > 0
        ),
        diverse_articles AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY source 
                    ORDER BY boosted_score DESC, published_at DESC
                ) as source_rank
            FROM scored_articles
            WHERE is_unseen = 1
        )
        SELECT 
            id,
            title,
            url,
            source,
            published_at,
            score_total,
            has_image,
            topics,
            boosted_score
        FROM diverse_articles
        WHERE source_rank <= 3  -- Max 3 articles per source
        ORDER BY boosted_score DESC, published_at DESC
        LIMIT :limit
    """), {
        "user_id": user_id,
        "limit": limit * 2  # Get extra for diversity filtering
    })
    
    articles = []
    sources_seen = set()
    topics_seen = set()
    
    for row in result.fetchall():
        # Simple diversity: avoid too many from same source/topic
        source_count = sum(1 for a in articles if a['source'] == row.source)
        if source_count >= 2:  # Max 2 per source
            continue
            
        # Extract dominant topic
        dominant_topic = row.topics[0] if row.topics else "general"
        topic_count = sum(1 for a in articles if a.get('dominant_topic') == dominant_topic)
        if topic_count >= 3:  # Max 3 per topic
            continue
            
        articles.append({
            'id': row.id,
            'title': row.title,
            'url': row.url,
            'source': row.source,
            'published_at': row.published_at.isoformat() if row.published_at else None,
            'score_total': row.score_total,
            'has_image': row.has_image,
            'topics': row.topics or [],
            'dominant_topic': dominant_topic,
            'p_read': min(1.0, row.boosted_score / 100.0),  # Normalize to 0-1
            'why': generate_why_tags(row)
        })
        
        if len(articles) >= limit:
            break
    
    return {
        "articles": articles,
        "total": len(articles),
        "user_id": user_id,
        "method": "rule_based",
        "timestamp": datetime.utcnow().isoformat()
    }

def generate_why_tags(article) -> List[str]:
    """Generate explanation tags for why article was recommended"""
    tags = []
    
    if article.boosted_score > 50:
        tags.append("High quality")
    
    if article.has_image:
        tags.append("Has image")
        
    # Check recency
    if article.published_at:
        hours_old = (datetime.utcnow() - article.published_at).total_seconds() / 3600
        if hours_old < 24:
            tags.append("Fresh")
        elif hours_old < 72:
            tags.append("Recent")
    
    # Source-based
    if article.source in ['TechCrunch AI', 'OpenAI Blog', 'Nature AI']:
        tags.append("Top source")
        
    # Topic-based
    if article.topics:
        hot_topics = {'ai', 'bitcoin', 'crypto', 'blockchain'}
        if any(topic.lower() in hot_topics for topic in article.topics):
            tags.append("Hot topic")
    
    return tags[:3]  # Limit to 3 tags