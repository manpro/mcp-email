"""
Administrative API endpoints for RSS Intelligence
Includes spam management, system statistics, and admin controls
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel

from ..deps import get_db
from ..services.spam_service import SpamService
from ..store import SpamReport
from ..store import SpamDetectionStats
from ..store import Article

router = APIRouter()

# Request/Response Models
class SpamReportResponse(BaseModel):
    id: int
    article_id: int
    article_title: str
    article_url: str
    article_source: str
    report_type: str
    spam_probability: float
    content_score: float
    title_coherence: float
    recommendation: str
    detection_summary: Optional[str]
    review_status: Optional[str]
    signal_types: List[str]
    created_at: str

class ReviewSpamRequest(BaseModel):
    review_status: str
    review_notes: Optional[str] = None

class BatchAnalysisRequest(BaseModel):
    article_ids: List[int]
    force_recheck: bool = False

class SpamStatisticsResponse(BaseModel):
    period_days: int
    total_articles: int
    total_spam: int
    overall_spam_rate: float
    avg_content_score: float
    daily_stats: List[Dict[str, Any]]
    signal_trends: Dict[str, List[Dict[str, Any]]]

# Spam Management Endpoints
@router.get("/spam-reports", response_model=Dict[str, Any])
async def get_spam_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    recommendation: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get paginated spam reports with filtering"""
    try:
        spam_service = SpamService(db)
        reports, total = spam_service.get_spam_reports(
            page=page,
            page_size=page_size,
            report_type=report_type,
            review_status=review_status,
            recommendation=recommendation
        )
        
        # Enrich with article information
        report_responses = []
        for report in reports:
            article = db.query(Article).filter(Article.id == report.article_id).first()
            
            report_response = SpamReportResponse(
                id=report.id,
                article_id=report.article_id,
                article_title=article.title if article else "Article not found",
                article_url=article.url if article else "",
                article_source=article.source if article else "",
                report_type=report.report_type,
                spam_probability=report.spam_probability,
                content_score=report.content_score,
                title_coherence=report.title_coherence,
                recommendation=report.recommendation,
                detection_summary=report.detection_summary,
                review_status=report.review_status,
                signal_types=report.signal_types,
                created_at=report.created_at.isoformat()
            )
            report_responses.append(report_response)
        
        return {
            'reports': report_responses,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': (total + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch spam reports: {str(e)}")

@router.post("/spam-reports/{report_id}/review")
async def review_spam_report(
    report_id: int,
    review_request: ReviewSpamRequest,
    db: Session = Depends(get_db)
):
    """Review a spam report (confirm, mark as false positive, etc.)"""
    try:
        spam_service = SpamService(db)
        
        # For now, use 'admin' as reviewer. In production, get from authentication
        reviewed_report = spam_service.review_spam_report(
            report_id=report_id,
            review_status=review_request.review_status,
            reviewed_by="admin",
            review_notes=review_request.review_notes
        )
        
        if not reviewed_report:
            raise HTTPException(status_code=404, detail="Spam report not found")
        
        return {
            'success': True,
            'report': reviewed_report.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review spam report: {str(e)}")

@router.post("/spam-analysis/batch")
async def run_batch_spam_analysis(
    request: BatchAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Run spam analysis on multiple articles"""
    try:
        if len(request.article_ids) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 articles per batch")
        
        spam_service = SpamService(db)
        results = spam_service.batch_analyze_articles(request.article_ids)
        
        return {
            'success': True,
            'analysis_timestamp': datetime.now().isoformat(),
            **results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run batch analysis: {str(e)}")

@router.post("/spam-analysis/recent")
async def analyze_recent_articles(
    hours: int = Query(24, ge=1, le=168),  # Max 1 week
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Analyze recent articles for spam"""
    try:
        # Get recent articles
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_articles = db.query(Article).filter(
            Article.created_at >= cutoff_time
        ).order_by(Article.created_at.desc()).limit(limit).all()
        
        if not recent_articles:
            return {
                'success': True,
                'message': f'No articles found in the last {hours} hours',
                'summary': {
                    'total_articles': 0,
                    'spam_detected': 0,
                    'spam_rate': 0,
                    'average_spam_probability': 0,
                    'average_content_score': 0
                }
            }
        
        article_ids = [a.id for a in recent_articles]
        
        spam_service = SpamService(db)
        results = spam_service.batch_analyze_articles(article_ids)
        
        return {
            'success': True,
            'analysis_timestamp': datetime.now().isoformat(),
            'time_range_hours': hours,
            **results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze recent articles: {str(e)}")

# Statistics and Monitoring Endpoints
@router.get("/spam-statistics", response_model=SpamStatisticsResponse)
async def get_spam_statistics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get spam detection statistics for the last N days"""
    try:
        spam_service = SpamService(db)
        stats = spam_service.get_spam_statistics(days=days)
        
        return SpamStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.post("/spam-statistics/update")
async def update_spam_statistics(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Update spam detection statistics for a specific date"""
    try:
        spam_service = SpamService(db)
        
        if target_date:
            try:
                parsed_date = date.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            parsed_date = None
        
        updated_stats = spam_service.update_daily_stats(target_date=parsed_date)
        
        return {
            'success': True,
            'updated_date': updated_stats.date.isoformat(),
            'stats': updated_stats.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update statistics: {str(e)}")

@router.get("/system-health")
async def get_system_health(db: Session = Depends(get_db)):
    """Get overall system health including spam detection performance"""
    try:
        # Get recent statistics
        spam_service = SpamService(db)
        recent_stats = spam_service.get_spam_statistics(days=7)
        
        # Get article counts
        total_articles = db.query(Article).count()
        spam_articles = db.query(Article).filter(Article.spam_detected == True).count()
        
        # Get recent spam reports
        recent_reports, _ = spam_service.get_spam_reports(page=1, page_size=10)
        pending_reviews = len([r for r in recent_reports if r.review_status == 'pending'])
        
        return {
            'timestamp': datetime.now().isoformat(),
            'database': {
                'total_articles': total_articles,
                'spam_articles': spam_articles,
                'spam_rate': spam_articles / total_articles if total_articles > 0 else 0
            },
            'spam_detection': {
                'last_7_days': recent_stats,
                'pending_reviews': pending_reviews,
                'system_status': 'healthy' if recent_stats['overall_spam_rate'] < 0.3 else 'warning'
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")

# Article Management Endpoints
@router.post("/articles/{article_id}/restore")
async def restore_spam_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Restore an article marked as spam back to the main feed"""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Clear spam flags
        article.spam_detected = False
        if article.flags:
            article.flags.pop('spam_detected', None)
            article.flags.pop('low_quality', None)
            article.flags.pop('spam_probability', None)
            article.flags.pop('spam_recommendation', None)
        
        # Restore article score if heavily penalized
        if article.score and article.score < -100:
            # Basic score restoration - in practice, you might want to recalculate
            article.score = max(article.score + 200, 0)
        
        db.commit()
        
        # Update any spam reports
        spam_reports = db.query(SpamReport).filter(SpamReport.article_id == article_id).all()
        for report in spam_reports:
            if report.review_status == 'pending':
                report.review_status = 'false_positive'
                report.reviewed_by = 'admin'
                report.review_notes = 'Article restored by admin'
                report.updated_at = datetime.now()
        
        db.commit()
        
        return {
            'success': True,
            'message': 'Article restored successfully',
            'article_id': article_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to restore article: {str(e)}")

@router.delete("/articles/{article_id}")
async def delete_spam_article(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Permanently delete a spam article"""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Delete associated spam reports (will be handled by CASCADE)
        db.delete(article)
        db.commit()
        
        return {
            'success': True,
            'message': 'Article deleted permanently',
            'article_id': article_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete article: {str(e)}")