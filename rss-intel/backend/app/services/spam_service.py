"""
Spam Detection Service
Handles spam detection, reporting, and statistics
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from ..store import SpamReport
from ..store import SpamDetectionStats
from ..store import Article
from ..intelligence import spam_detector

logger = logging.getLogger(__name__)


class SpamService:
    """Service for managing spam detection and reporting"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_spam_report(
        self,
        article_id: int,
        spam_result,
        report_type: str = "auto_detected",
        reported_by: str = "system"
    ) -> SpamReport:
        """Create a new spam report from detection results"""
        try:
            # Check if report already exists
            existing = self.db.query(SpamReport).filter(
                and_(
                    SpamReport.article_id == article_id,
                    SpamReport.report_type == report_type
                )
            ).first()
            
            if existing:
                # Update existing report
                existing.spam_probability = spam_result.spam_probability
                existing.content_score = spam_result.content_score
                existing.title_coherence = spam_result.title_content_coherence
                existing.recommendation = spam_result.recommendation
                existing.spam_signals = [
                    {
                        'type': signal.type,
                        'confidence': signal.confidence,
                        'reason': signal.reason,
                        'evidence_count': len(signal.evidence)
                    }
                    for signal in spam_result.spam_signals
                ]
                existing.quality_issues = [
                    {
                        'issue_type': issue.issue_type,
                        'severity': issue.severity,
                        'description': issue.description,
                        'confidence': issue.confidence,
                        'affected_sections': issue.affected_sections
                    }
                    for issue in spam_result.quality_issues
                ]
                existing.detection_summary = spam_detector.get_spam_summary(spam_result)
                existing.updated_at = datetime.now()
                
                self.db.commit()
                self.db.refresh(existing)
                return existing
            
            # Create new report
            spam_report = SpamReport(
                article_id=article_id,
                report_type=report_type,
                spam_probability=spam_result.spam_probability,
                content_score=spam_result.content_score,
                title_coherence=spam_result.title_content_coherence,
                recommendation=spam_result.recommendation,
                spam_signals=[
                    {
                        'type': signal.type,
                        'confidence': signal.confidence,
                        'reason': signal.reason,
                        'evidence_count': len(signal.evidence)
                    }
                    for signal in spam_result.spam_signals
                ],
                quality_issues=[
                    {
                        'issue_type': issue.issue_type,
                        'severity': issue.severity,
                        'description': issue.description,
                        'confidence': issue.confidence,
                        'affected_sections': issue.affected_sections
                    }
                    for issue in spam_result.quality_issues
                ],
                detection_summary=spam_detector.get_spam_summary(spam_result),
                reported_by=reported_by,
                review_status="pending" if spam_result.recommendation in ["review", "reject"] else None
            )
            
            self.db.add(spam_report)
            self.db.commit()
            self.db.refresh(spam_report)
            
            return spam_report
            
        except Exception as e:
            logger.error(f"Error creating spam report for article {article_id}: {e}")
            self.db.rollback()
            raise
    
    def update_article_spam_status(self, article_id: int, spam_result) -> None:
        """Update article with spam detection results"""
        try:
            article = self.db.query(Article).filter(Article.id == article_id).first()
            if not article:
                logger.warning(f"Article {article_id} not found for spam status update")
                return
            
            # Update article spam fields
            article.spam_detected = spam_result.is_spam
            article.spam_probability = spam_result.spam_probability
            article.content_quality_score = spam_result.content_score
            article.title_coherence_score = spam_result.title_content_coherence
            article.spam_signals = [signal.type for signal in spam_result.spam_signals]
            article.last_spam_check = datetime.now()
            
            # Update article flags if exists
            if not article.flags:
                article.flags = {}
            
            if spam_result.is_spam:
                article.flags['spam_detected'] = True
                article.flags['spam_probability'] = spam_result.spam_probability
                article.flags['spam_recommendation'] = spam_result.recommendation
            elif spam_result.spam_probability > 0.5 or spam_result.content_score < 0.4:
                article.flags['low_quality'] = True
                article.flags['content_score'] = spam_result.content_score
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating article spam status for {article_id}: {e}")
            self.db.rollback()
            raise
    
    def analyze_article_for_spam(self, article_id: int) -> Optional[SpamReport]:
        """Analyze a single article for spam and create report"""
        try:
            article = self.db.query(Article).filter(Article.id == article_id).first()
            if not article:
                logger.warning(f"Article {article_id} not found for spam analysis")
                return None
            
            # Run spam detection
            spam_result = spam_detector.detect_spam(
                title=article.title,
                content=article.content or "",
                source=article.source
            )
            
            # Create spam report
            spam_report = self.create_spam_report(
                article_id=article_id,
                spam_result=spam_result
            )
            
            # Update article status
            self.update_article_spam_status(article_id, spam_result)
            
            return spam_report
            
        except Exception as e:
            logger.error(f"Error analyzing article {article_id} for spam: {e}")
            raise
    
    def batch_analyze_articles(self, article_ids: List[int]) -> Dict[str, Any]:
        """Analyze multiple articles for spam"""
        results = []
        errors = []
        
        for article_id in article_ids:
            try:
                spam_report = self.analyze_article_for_spam(article_id)
                if spam_report:
                    results.append({
                        'article_id': article_id,
                        'is_spam': spam_report.is_spam,
                        'spam_probability': spam_report.spam_probability,
                        'recommendation': spam_report.recommendation,
                        'content_score': spam_report.content_score,
                        'signal_count': len(spam_report.spam_signals or []),
                        'issue_count': len(spam_report.quality_issues or [])
                    })
            except Exception as e:
                errors.append(f"Error analyzing article {article_id}: {str(e)}")
                continue
        
        # Generate summary
        total_articles = len(results)
        spam_detected = sum(1 for r in results if r['is_spam'])
        avg_spam_prob = sum(r['spam_probability'] for r in results) / total_articles if total_articles > 0 else 0
        avg_content_score = sum(r['content_score'] for r in results) / total_articles if total_articles > 0 else 0
        
        return {
            'results': results,
            'errors': errors,
            'summary': {
                'total_articles': total_articles,
                'spam_detected': spam_detected,
                'spam_rate': spam_detected / total_articles if total_articles > 0 else 0,
                'average_spam_probability': avg_spam_prob,
                'average_content_score': avg_content_score
            }
        }
    
    def get_spam_reports(
        self,
        page: int = 1,
        page_size: int = 20,
        report_type: Optional[str] = None,
        review_status: Optional[str] = None,
        recommendation: Optional[str] = None
    ) -> Tuple[List[SpamReport], int]:
        """Get paginated spam reports with filtering"""
        try:
            query = self.db.query(SpamReport)
            
            # Apply filters
            if report_type:
                query = query.filter(SpamReport.report_type == report_type)
            if review_status:
                query = query.filter(SpamReport.review_status == review_status)
            if recommendation:
                query = query.filter(SpamReport.recommendation == recommendation)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            reports = query.order_by(desc(SpamReport.created_at)).offset(offset).limit(page_size).all()
            
            return reports, total
            
        except Exception as e:
            logger.error(f"Error fetching spam reports: {e}")
            raise
    
    def review_spam_report(
        self,
        report_id: int,
        review_status: str,
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> Optional[SpamReport]:
        """Review a spam report (confirm, mark as false positive, etc.)"""
        try:
            report = self.db.query(SpamReport).filter(SpamReport.id == report_id).first()
            if not report:
                return None
            
            report.review_status = review_status
            report.reviewed_by = reviewed_by
            report.review_notes = review_notes
            report.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error reviewing spam report {report_id}: {e}")
            self.db.rollback()
            raise
    
    def update_daily_stats(self, target_date: Optional[date] = None) -> SpamDetectionStats:
        """Update daily spam detection statistics"""
        if target_date is None:
            target_date = date.today()
        
        try:
            # Get or create stats record for the date
            stats = self.db.query(SpamDetectionStats).filter(
                SpamDetectionStats.date == target_date
            ).first()
            
            if not stats:
                stats = SpamDetectionStats(date=target_date)
                self.db.add(stats)
            
            # Calculate statistics for the day
            start_time = datetime.combine(target_date, datetime.min.time())
            end_time = start_time + timedelta(days=1)
            
            # Get reports for the day
            reports_query = self.db.query(SpamReport).filter(
                and_(
                    SpamReport.created_at >= start_time,
                    SpamReport.created_at < end_time,
                    SpamReport.report_type == 'auto_detected'
                )
            )
            
            daily_reports = reports_query.all()
            
            # Update basic counts
            stats.total_articles_checked = len(daily_reports)
            stats.spam_detected_count = len([r for r in daily_reports if r.is_spam])
            
            # Calculate averages
            if daily_reports:
                stats.avg_spam_probability = sum(r.spam_probability for r in daily_reports) / len(daily_reports)
                stats.avg_content_score = sum(r.content_score for r in daily_reports) / len(daily_reports)
            
            # Count signal types
            signal_counts = {}
            for report in daily_reports:
                if report.spam_signals:
                    for signal in report.spam_signals:
                        signal_type = signal.get('type', 'unknown')
                        signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
            
            stats.signal_type_counts = signal_counts
            stats.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error updating daily stats for {target_date}: {e}")
            self.db.rollback()
            raise
    
    def get_spam_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get spam detection statistics for the last N days"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            stats_records = self.db.query(SpamDetectionStats).filter(
                and_(
                    SpamDetectionStats.date >= start_date,
                    SpamDetectionStats.date <= end_date
                )
            ).order_by(SpamDetectionStats.date).all()
            
            if not stats_records:
                return {
                    'period_days': days,
                    'total_articles': 0,
                    'total_spam': 0,
                    'overall_spam_rate': 0.0,
                    'avg_content_score': 0.0,
                    'daily_stats': [],
                    'signal_trends': {}
                }
            
            # Aggregate statistics
            total_articles = sum(s.total_articles_checked for s in stats_records)
            total_spam = sum(s.spam_detected_count for s in stats_records)
            overall_spam_rate = total_spam / total_articles if total_articles > 0 else 0.0
            
            # Average content score
            content_scores = [s.avg_content_score for s in stats_records if s.avg_content_score is not None]
            avg_content_score = sum(content_scores) / len(content_scores) if content_scores else 0.0
            
            # Signal trends
            signal_trends = {}
            for stats in stats_records:
                if stats.signal_type_counts:
                    for signal_type, count in stats.signal_type_counts.items():
                        if signal_type not in signal_trends:
                            signal_trends[signal_type] = []
                        signal_trends[signal_type].append({
                            'date': stats.date.isoformat(),
                            'count': count
                        })
            
            return {
                'period_days': days,
                'total_articles': total_articles,
                'total_spam': total_spam,
                'overall_spam_rate': overall_spam_rate,
                'avg_content_score': avg_content_score,
                'daily_stats': [s.to_dict() for s in stats_records],
                'signal_trends': signal_trends
            }
            
        except Exception as e:
            logger.error(f"Error getting spam statistics: {e}")
            raise