"""
Story clustering API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..deps import get_db
from ..schemas import StoryResponse, StoryList, ClusteringStats
from ..store import Story, Article
from ..clustering import cluster_articles_batch, StoryClustering

router = APIRouter()


@router.get("/stories", response_model=StoryList)
async def get_stories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    min_articles: int = Query(None, description="Minimum number of articles in story"),
    days_back: int = Query(None, description="Only stories from last N days"),
    db: Session = Depends(get_db)
):
    """Get list of stories with clustering information"""
    
    query = db.query(Story)
    
    # Filter by minimum article count
    if min_articles:
        from sqlalchemy import func
        query = query.join(Article).group_by(Story.id).having(
            func.count(Article.id) >= min_articles
        )
    
    # Filter by date
    if days_back:
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(Story.last_seen >= since)
    
    # Pagination
    total = query.count()
    stories = query.order_by(Story.last_seen.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # Add article count for each story
    story_responses = []
    for story in stories:
        article_count = db.query(Article).filter(Article.story_id == story.id).count()
        story_dict = {
            "id": story.id,
            "canonical_title": story.canonical_title,
            "best_image": story.best_image,
            "sources": story.sources or [],
            "first_seen": story.first_seen,
            "last_seen": story.last_seen,
            "confidence": story.confidence,
            "article_count": article_count,
            "created_at": story.created_at,
            "updated_at": story.updated_at
        }
        story_responses.append(story_dict)
    
    return {
        "items": story_responses,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stories/{story_id}", response_model=StoryResponse)
async def get_story(story_id: int, db: Session = Depends(get_db)):
    """Get specific story with all its articles"""
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get all articles in this story
    articles = db.query(Article).filter(Article.story_id == story_id).order_by(
        Article.published_at.desc()
    ).all()
    
    return {
        "id": story.id,
        "canonical_title": story.canonical_title,
        "best_image": story.best_image,
        "sources": story.sources or [],
        "first_seen": story.first_seen,
        "last_seen": story.last_seen,
        "confidence": story.confidence,
        "article_count": len(articles),
        "articles": articles,
        "created_at": story.created_at,
        "updated_at": story.updated_at
    }


@router.post("/clustering/run")
async def run_clustering(
    limit: int = Query(100, ge=1, le=1000, description="Max articles to cluster"),
    db: Session = Depends(get_db)
):
    """Manually trigger clustering for unclustered articles"""
    
    try:
        # Get unclustered articles using the same approach as individual clustering
        from sqlalchemy import text
        
        unclustered_articles = db.execute(text("""
            SELECT id FROM articles 
            WHERE story_id IS NULL 
            ORDER BY published_at DESC 
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        clustered = 0
        new_stories = 0
        errors = 0
        
        # Process each article individually with separate database connections
        # to avoid transaction issues
        for row in unclustered_articles:
            try:
                article_id = row.id
                print(f"Processing article {article_id}")
                
                # Use raw SQL to avoid ORM transaction issues
                from sqlalchemy import text
                
                # Check if article exists and is unclustered using raw SQL
                article_check = db.execute(text("""
                    SELECT id, title, url, source, published_at, image_proxy_path
                    FROM articles 
                    WHERE id = :article_id AND story_id IS NULL
                """), {"article_id": article_id}).fetchone()
                
                if not article_check:
                    print(f"Article {article_id} not found or already clustered")
                    continue
                
                # Create new story using raw SQL with proper JSON handling
                import json
                sources_json = json.dumps([{"url": article_check.url, "site": article_check.source or "unknown", "ts": article_check.published_at.isoformat()}])
                
                story_result = db.execute(text("""
                    INSERT INTO stories (canonical_title, best_image, sources, first_seen, last_seen, confidence)
                    VALUES (:title, :image, CAST(:sources AS jsonb), :published_at, :published_at, 0.8)
                    RETURNING id
                """), {
                    "title": article_check.title or f"Story for article {article_id}",
                    "image": article_check.image_proxy_path,
                    "sources": sources_json,
                    "published_at": article_check.published_at
                })
                
                story_id = story_result.scalar()
                
                # Assign article to story using raw SQL
                db.execute(text("""
                    UPDATE articles SET story_id = :story_id WHERE id = :article_id
                """), {"story_id": story_id, "article_id": article_id})
                
                db.commit()
                print(f"Successfully clustered article {article_id} into story {story_id}")
                
                clustered += 1
                new_stories += 1
                
            except Exception as e:
                print(f"Error clustering article {row.id}: {e}")
                db.rollback()
                errors += 1
        
        stats = {
            "processed": len(unclustered_articles),
            "clustered": clustered,
            "new_stories": new_stories,
            "errors": errors
        }
        
        return {
            "status": "success",
            "stats": stats,
            "message": f"Processed {stats['processed']} articles, created {stats['new_stories']} new stories"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@router.post("/clustering/article/{article_id}")
async def cluster_article(article_id: int, db: Session = Depends(get_db)):
    """Cluster a specific article"""
    
    # Check article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.story_id:
        return {
            "status": "already_clustered",
            "story_id": article.story_id,
            "message": f"Article already belongs to story {article.story_id}"
        }
    
    try:
        clustering = StoryClustering(db)
        story_id = clustering.cluster_article(article_id)
        
        if story_id:
            return {
                "status": "success",
                "story_id": story_id,
                "message": f"Article clustered into story {story_id}"
            }
        else:
            return {
                "status": "failed",
                "message": "Could not cluster article"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@router.get("/clustering/stats")
async def get_clustering_stats(db: Session = Depends(get_db)):
    """Get clustering statistics"""
    
    from sqlalchemy import func, text
    
    # Basic counts
    total_articles = db.query(Article).count()
    clustered_articles = db.query(Article).filter(Article.story_id.isnot(None)).count()
    total_stories = db.query(Story).count()
    
    # Articles per story distribution
    story_sizes = db.execute(text("""
        SELECT 
            CASE 
                WHEN article_count = 1 THEN '1 article'
                WHEN article_count BETWEEN 2 AND 5 THEN '2-5 articles'
                WHEN article_count BETWEEN 6 AND 10 THEN '6-10 articles'
                ELSE '10+ articles'
            END as size_category,
            COUNT(*) as story_count
        FROM (
            SELECT story_id, COUNT(*) as article_count
            FROM articles 
            WHERE story_id IS NOT NULL
            GROUP BY story_id
        ) story_counts
        GROUP BY size_category
        ORDER BY MIN(article_count)
    """)).fetchall()
    
    # Recent clustering activity
    recent_stories = db.query(func.count(Story.id)).filter(
        Story.created_at >= datetime.utcnow().date()
    ).scalar()
    
    return {
        "total_articles": total_articles,
        "clustered_articles": clustered_articles,
        "unclustered_articles": total_articles - clustered_articles,
        "clustering_rate": (clustered_articles / total_articles * 100) if total_articles > 0 else 0,
        "total_stories": total_stories,
        "stories_created_today": recent_stories,
        "story_size_distribution": [
            {"category": row[0], "count": row[1]} for row in story_sizes
        ]
    }


@router.post("/stories/{story_id}/split")
async def split_story(
    story_id: int,
    article_ids: List[int],
    new_title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Split a story by moving specified articles to a new story"""
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Validate article IDs belong to this story
    articles = db.query(Article).filter(
        Article.id.in_(article_ids),
        Article.story_id == story_id
    ).all()
    
    if len(articles) != len(article_ids):
        raise HTTPException(status_code=400, detail="Some articles don't belong to this story")
    
    if len(articles) == 0:
        raise HTTPException(status_code=400, detail="No articles to split")
    
    # Don't split if it would leave the original story with no articles
    remaining_count = db.query(Article).filter(
        Article.story_id == story_id,
        ~Article.id.in_(article_ids)
    ).count()
    
    if remaining_count == 0:
        raise HTTPException(status_code=400, detail="Cannot split all articles from story")
    
    # Create new story
    first_article = min(articles, key=lambda a: a.published_at)
    last_article = max(articles, key=lambda a: a.published_at)
    
    new_story = Story(
        canonical_title=new_title or first_article.title,
        best_image=first_article.image_proxy_path,
        sources=[{"url": a.url, "site": a.source, "ts": a.published_at.isoformat()} for a in articles],
        first_seen=first_article.published_at,
        last_seen=last_article.published_at,
        confidence=0.8  # Lower confidence for manually split story
    )
    
    db.add(new_story)
    db.flush()  # Get the new story ID
    
    # Move articles to new story
    for article in articles:
        article.story_id = new_story.id
    
    db.commit()
    
    return {
        "status": "success",
        "original_story_id": story_id,
        "new_story_id": new_story.id,
        "moved_articles": len(articles),
        "message": f"Split {len(articles)} articles into new story {new_story.id}"
    }


@router.post("/stories/{story_id}/merge/{target_story_id}")
async def merge_stories(
    story_id: int,
    target_story_id: int,
    db: Session = Depends(get_db)
):
    """Merge one story into another"""
    
    if story_id == target_story_id:
        raise HTTPException(status_code=400, detail="Cannot merge story with itself")
    
    source_story = db.query(Story).filter(Story.id == story_id).first()
    target_story = db.query(Story).filter(Story.id == target_story_id).first()
    
    if not source_story:
        raise HTTPException(status_code=404, detail="Source story not found")
    if not target_story:
        raise HTTPException(status_code=404, detail="Target story not found")
    
    # Move all articles from source to target story
    articles_moved = db.query(Article).filter(Article.story_id == story_id).update(
        {"story_id": target_story_id}
    )
    
    # Update target story metadata
    target_story.last_seen = max(target_story.last_seen, source_story.last_seen)
    target_story.first_seen = min(target_story.first_seen, source_story.first_seen)
    
    # Combine sources
    existing_sources = target_story.sources or []
    new_sources = source_story.sources or []
    target_story.sources = existing_sources + new_sources
    
    # Remove source story
    db.delete(source_story)
    db.commit()
    
    return {
        "status": "success",
        "target_story_id": target_story_id,
        "articles_moved": articles_moved,
        "message": f"Merged story {story_id} into story {target_story_id}, moved {articles_moved} articles"
    }


@router.post("/articles/{article_id}/report-spam")
async def report_spam(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Report an article as spam/advertisement"""
    
    # Check article exists
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    try:
        from sqlalchemy import text
        
        # Insert spam report
        db.execute(text("""
            INSERT INTO spam_reports (article_id, reported_at, source, reason)
            VALUES (:article_id, NOW(), 'user_feedback', 'promotional_content')
            ON CONFLICT (article_id) DO UPDATE SET
            reported_at = NOW(),
            report_count = spam_reports.report_count + 1
        """), {"article_id": article_id})
        
        # Apply heavy penalty to quality score
        if article.score_total is None:
            article.score_total = -999  # Auto-hide
        else:
            article.score_total = min(article.score_total - 500, -999)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Article reported as spam and hidden from feed",
            "article_id": article_id,
            "new_quality_score": article.score_total
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to report spam: {str(e)}")


@router.get("/admin/spam-reports")
async def get_spam_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get spam reports for admin review"""
    
    try:
        from sqlalchemy import text
        
        # Get spam reports with article details
        reports = db.execute(text("""
            SELECT 
                sr.article_id,
                sr.reported_at,
                sr.report_count,
                sr.source,
                sr.reason,
                a.title,
                a.url,
                a.source as article_source,
                a.score_total,
                0.8 as spam_score
            FROM spam_reports sr
            JOIN articles a ON sr.article_id = a.id
            ORDER BY sr.reported_at DESC
            LIMIT :limit OFFSET :offset
        """), {
            "limit": page_size,
            "offset": (page - 1) * page_size
        }).fetchall()
        
        # Get total count
        total_result = db.execute(text("SELECT COUNT(*) FROM spam_reports"))
        total = total_result.scalar()
        
        report_list = []
        for row in reports:
            report_list.append({
                "article_id": row.article_id,
                "title": row.title,
                "url": row.url,
                "source": row.article_source,
                "reported_at": row.reported_at.isoformat() if row.reported_at else None,
                "report_count": row.report_count,
                "report_source": row.source,
                "reason": row.reason,
                "quality_score": row.score_total,
                "spam_score": row.spam_score,
                "ml_metadata": {}
            })
        
        return {
            "reports": report_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get spam reports: {str(e)}")


@router.post("/articles/{article_id}/restore")
async def restore_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Restore an article from spam back to normal feed"""
    
    try:
        # Check article exists
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Reset quality score to neutral if it was heavily penalized
        if article.score_total is not None and article.score_total < -500:
            article.score_total = 0
        
        # Remove from spam reports
        from sqlalchemy import text
        db.execute(text("""
            DELETE FROM spam_reports WHERE article_id = :article_id
        """), {"article_id": article_id})
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Article restored to main feed",
            "article_id": article_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to restore article: {str(e)}")


@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Permanently delete an article"""
    
    try:
        # Check article exists
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Delete spam reports first (cascade should handle this, but be explicit)
        from sqlalchemy import text
        db.execute(text("""
            DELETE FROM spam_reports WHERE article_id = :article_id
        """), {"article_id": article_id})
        
        # Delete the article
        db.delete(article)
        db.commit()
        
        return {
            "status": "success",
            "message": "Article permanently deleted",
            "article_id": article_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete article: {str(e)}")