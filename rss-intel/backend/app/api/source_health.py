"""
Source Health Monitoring API

API endpoints for monitoring RSS feed health, content extraction success,
and identifying problematic sources that may be blocked by Cloudflare or paywalls.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ..deps import get_db
from ..services.source_health_service import get_source_health_monitor, SourceHealthMetrics
from ..models.source_health import SourceHealthReport, SourceHealthAlert, ContentExtractionResult
from ..store import Article

logger = logging.getLogger(__name__)
router = APIRouter()

class SourceHealthSummary(BaseModel):
    """Summary of source health status"""
    source_name: str
    health_status: str
    extraction_success_rate: float
    content_quality_score: float
    total_articles: int
    last_successful_extraction: Optional[datetime]
    critical_issues: int
    recommendations: List[str]

class HealthIssueModel(BaseModel):
    """Health issue model for API responses"""
    issue_type: str
    severity: str
    description: str
    detection_time: datetime
    confidence: float
    affected_articles: int

class ProblematicSourceDetail(BaseModel):
    """Detailed information about a problematic source"""
    source_name: str
    health_status: str
    metrics: Dict[str, Any]
    issues: List[HealthIssueModel]
    recent_failures: List[Dict[str, Any]]
    recommendations: List[str]

@router.get("/source-health/overview")
async def get_health_overview(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get overall source health overview"""
    try:
        monitor = get_source_health_monitor(db)
        health_report = monitor.generate_health_report(days)
        
        return {
            "overview": health_report,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get health overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source-health/problematic")
async def get_problematic_sources(
    days: int = Query(7, ge=1, le=30),
    min_severity: str = Query("medium", regex="^(low|medium|high|critical)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get sources with health problems"""
    try:
        monitor = get_source_health_monitor(db)
        problematic_sources = monitor.get_problematic_sources(days)
        
        # Filter by severity
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_levels.get(min_severity, 2)
        
        filtered_sources = []
        for source_metrics in problematic_sources:
            max_severity = 0
            for issue in source_metrics.issues:
                issue_level = severity_levels.get(issue.severity, 0)
                max_severity = max(max_severity, issue_level)
            
            if max_severity >= min_level:
                filtered_sources.append(source_metrics)
        
        # Convert to API response format
        response_sources = []
        for metrics in filtered_sources[:limit]:
            issues = []
            for issue in metrics.issues:
                issues.append(HealthIssueModel(
                    issue_type=issue.issue_type,
                    severity=issue.severity,
                    description=issue.description,
                    detection_time=issue.detection_time,
                    confidence=issue.confidence,
                    affected_articles=len(issue.article_urls)
                ))
            
            response_sources.append(SourceHealthSummary(
                source_name=metrics.source_name,
                health_status=metrics.health_status,
                extraction_success_rate=metrics.extraction_success_rate,
                content_quality_score=metrics.content_quality_score,
                total_articles=metrics.total_articles,
                last_successful_extraction=metrics.last_successful_extraction,
                critical_issues=len([i for i in metrics.issues if i.severity == 'critical']),
                recommendations=[]  # Will be added if needed
            ))
        
        return {
            "problematic_sources": response_sources,
            "total_found": len(response_sources),
            "analysis_period_days": days,
            "min_severity": min_severity
        }
        
    except Exception as e:
        logger.error(f"Failed to get problematic sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source-health/{source_name}")
async def get_source_health_detail(
    source_name: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get detailed health information for a specific source"""
    try:
        monitor = get_source_health_monitor(db)
        metrics = await monitor.analyze_source_health(source_name, days)
        
        # Get recent extraction results
        recent_extractions = db.query(ContentExtractionResult).filter(
            and_(
                ContentExtractionResult.source_name == source_name,
                ContentExtractionResult.extraction_attempt_at >= datetime.now() - timedelta(days=days)
            )
        ).order_by(desc(ContentExtractionResult.extraction_attempt_at)).limit(50).all()
        
        # Get failure patterns
        failures = [r for r in recent_extractions if not r.success]
        failure_reasons = {}
        for failure in failures:
            reason = failure.failure_reason or 'unknown'
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # Convert issues to API format
        issues = []
        for issue in metrics.issues:
            issues.append(HealthIssueModel(
                issue_type=issue.issue_type,
                severity=issue.severity,
                description=issue.description,
                detection_time=issue.detection_time,
                confidence=issue.confidence,
                affected_articles=len(issue.article_urls)
            ))
        
        return ProblematicSourceDetail(
            source_name=source_name,
            health_status=metrics.health_status,
            metrics={
                "total_articles": metrics.total_articles,
                "successful_extractions": metrics.successful_extractions,
                "failed_extractions": metrics.failed_extractions,
                "extraction_success_rate": metrics.extraction_success_rate,
                "content_quality_score": metrics.content_quality_score,
                "cloudflare_blocks": metrics.cloudflare_blocks,
                "paywall_hits": metrics.paywall_hits,
                "spam_articles": metrics.spam_articles,
                "last_successful_extraction": metrics.last_successful_extraction.isoformat() if metrics.last_successful_extraction else None
            },
            issues=issues,
            recent_failures=[
                {
                    "url": f.original_url,
                    "failure_reason": f.failure_reason,
                    "http_status": f.http_status_code,
                    "error_message": f.error_message,
                    "attempt_time": f.extraction_attempt_at.isoformat()
                }
                for f in failures[:10]
            ],
            recommendations=[]  # TODO: Generate specific recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get source health detail for {source_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/source-health/analyze")
async def trigger_health_analysis(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(None),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Trigger health analysis for specific sources or all sources"""
    try:
        monitor = get_source_health_monitor(db)
        
        if sources:
            # Analyze specific sources
            background_tasks.add_task(analyze_specific_sources, monitor, sources, days)
            return {
                "message": f"Health analysis started for {len(sources)} sources",
                "sources": sources,
                "analysis_period_days": days
            }
        else:
            # Analyze all sources
            background_tasks.add_task(analyze_all_sources_background, monitor, days)
            return {
                "message": "Health analysis started for all sources",
                "analysis_period_days": days
            }
            
    except Exception as e:
        logger.error(f"Failed to trigger health analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source-health/alerts")
async def get_health_alerts(
    active_only: bool = Query(True),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get health alerts for sources"""
    try:
        query = db.query(SourceHealthAlert)
        
        if active_only:
            query = query.filter(SourceHealthAlert.status == 'active')
        
        if severity:
            query = query.filter(SourceHealthAlert.severity == severity)
        
        alerts = query.order_by(
            desc(SourceHealthAlert.severity == 'critical'),
            desc(SourceHealthAlert.severity == 'high'),
            desc(SourceHealthAlert.created_at)
        ).limit(limit).all()
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                "id": alert.id,
                "source_name": alert.source_name,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "status": alert.status,
                "created_at": alert.created_at.isoformat(),
                "age_hours": alert.age_hours,
                "metric_value": alert.metric_value,
                "threshold_value": alert.threshold_value,
                "recommended_actions": alert.recommended_actions
            })
        
        return {
            "alerts": alert_data,
            "total_count": len(alert_data),
            "filters_applied": {
                "active_only": active_only,
                "severity": severity
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get health alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/source-health/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Acknowledge a health alert"""
    try:
        alert = db.query(SourceHealthAlert).filter(SourceHealthAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert.acknowledge(notes)
        db.commit()
        
        return {
            "message": "Alert acknowledged successfully",
            "alert_id": alert_id,
            "acknowledged_at": alert.acknowledged_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source-health/statistics")
async def get_health_statistics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get comprehensive health statistics across all sources"""
    try:
        since_date = datetime.now() - timedelta(days=days)
        
        # Get extraction statistics
        extraction_stats = db.query(
            func.count(ContentExtractionResult.id).label('total_attempts'),
            func.sum(func.cast(ContentExtractionResult.success, Integer)).label('successful_attempts'),
            func.avg(ContentExtractionResult.content_quality_score).label('avg_quality')
        ).filter(
            ContentExtractionResult.extraction_attempt_at >= since_date
        ).first()
        
        # Get failure reasons breakdown
        failure_reasons = db.query(
            ContentExtractionResult.failure_reason,
            func.count(ContentExtractionResult.id).label('count')
        ).filter(
            and_(
                ContentExtractionResult.extraction_attempt_at >= since_date,
                ContentExtractionResult.success == False
            )
        ).group_by(ContentExtractionResult.failure_reason).all()
        
        # Get source distribution
        source_health_distribution = db.query(
            SourceHealthReport.health_status,
            func.count(SourceHealthReport.id).label('count')
        ).filter(
            SourceHealthReport.analysis_date >= since_date
        ).group_by(SourceHealthReport.health_status).all()
        
        # Active alerts by severity
        active_alerts = db.query(
            SourceHealthAlert.severity,
            func.count(SourceHealthAlert.id).label('count')
        ).filter(
            SourceHealthAlert.status == 'active'
        ).group_by(SourceHealthAlert.severity).all()
        
        return {
            "analysis_period_days": days,
            "extraction_statistics": {
                "total_attempts": extraction_stats.total_attempts or 0,
                "successful_attempts": extraction_stats.successful_attempts or 0,
                "success_rate": (extraction_stats.successful_attempts or 0) / max(extraction_stats.total_attempts or 1, 1),
                "average_quality_score": round(extraction_stats.avg_quality or 0, 3)
            },
            "failure_breakdown": {
                reason: count for reason, count in failure_reasons
            },
            "source_health_distribution": {
                status: count for status, count in source_health_distribution
            },
            "active_alerts_by_severity": {
                severity: count for severity, count in active_alerts
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get health statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/source-health/sources/{source_name}")
async def disable_problematic_source(
    source_name: str,
    reason: str = Query(..., description="Reason for disabling"),
    db: Session = Depends(get_db)
):
    """Disable a problematic source (mark for removal from feeds)"""
    try:
        # Create an alert for the disabled source
        alert = SourceHealthAlert(
            source_name=source_name,
            alert_type='source_disabled',
            severity='high',
            title=f'Source disabled: {source_name}',
            description=f'Source manually disabled due to: {reason}',
            status='resolved',
            resolved_at=datetime.now(),
            admin_notes=f'Disabled by admin: {reason}'
        )
        
        db.add(alert)
        db.commit()
        
        return {
            "message": f"Source {source_name} marked for disabling",
            "reason": reason,
            "alert_id": alert.id
        }
        
    except Exception as e:
        logger.error(f"Failed to disable source {source_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def analyze_specific_sources(monitor, sources: List[str], days: int):
    """Background task to analyze specific sources"""
    try:
        for source in sources:
            await monitor.analyze_source_health(source, days)
        logger.info(f"Completed health analysis for {len(sources)} sources")
    except Exception as e:
        logger.error(f"Failed to analyze specific sources: {e}")

async def analyze_all_sources_background(monitor, days: int):
    """Background task to analyze all sources"""
    try:
        await monitor.analyze_all_sources(days)
        logger.info("Completed health analysis for all sources")
    except Exception as e:
        logger.error(f"Failed to analyze all sources: {e}")