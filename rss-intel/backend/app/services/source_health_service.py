"""
Source Health Monitoring Service

Monitors RSS feeds and content sources for health issues, content extraction problems,
and access restrictions like Cloudflare blocks.
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import re
import hashlib
from urllib.parse import urlparse
import json

from ..store import Article
from ..models.source_health import SourceHealthReport, ContentExtractionResult
from ..intelligence.spam_detector import AdvancedSpamDetector

logger = logging.getLogger(__name__)

@dataclass
class HealthIssue:
    """A health issue detected for a source"""
    issue_type: str  # 'cloudflare_block', 'paywall', 'extraction_failure', 'low_content', 'duplicate_content'
    severity: str    # 'low', 'medium', 'high', 'critical'
    description: str
    detection_time: datetime
    article_urls: List[str]
    confidence: float

@dataclass
class SourceHealthMetrics:
    """Health metrics for a source"""
    source_name: str
    total_articles: int
    successful_extractions: int
    failed_extractions: int
    cloudflare_blocks: int
    paywall_hits: int
    low_content_articles: int
    duplicate_articles: int
    spam_articles: int
    extraction_success_rate: float
    content_quality_score: float
    last_successful_extraction: Optional[datetime]
    issues: List[HealthIssue]
    health_status: str  # 'healthy', 'degraded', 'unhealthy', 'failing'

class SourceHealthMonitor:
    """Monitor and analyze source health"""
    
    def __init__(self, db: Session):
        self.db = db
        self.spam_detector = AdvancedSpamDetector()
        
        # Health thresholds
        self.thresholds = {
            'extraction_success_rate_warning': 0.7,
            'extraction_success_rate_critical': 0.5,
            'content_quality_warning': 0.4,
            'content_quality_critical': 0.2,
            'cloudflare_rate_warning': 0.3,
            'cloudflare_rate_critical': 0.6,
            'paywall_rate_warning': 0.4,
            'paywall_rate_critical': 0.7
        }
        
        # Detection patterns
        self.detection_patterns = {
            'cloudflare_block': [
                r'checking if the site connection is secure',
                r'cloudflare ray id',
                r'please enable cookies and reload the page',
                r'attention required.*cloudflare',
                r'please wait while we check your browser',
                r'ddos protection by cloudflare'
            ],
            'paywall': [
                r'subscribe to continue reading',
                r'become a member to read',
                r'please sign in to continue',
                r'subscription required',
                r'premium content',
                r'paywall',
                r'register to read'
            ],
            'bot_block': [
                r'access denied.*bot',
                r'please verify you are a human',
                r'robot or spider detected',
                r'automated access not allowed'
            ],
            'rate_limit': [
                r'too many requests',
                r'rate limit exceeded',
                r'please try again later',
                r'temporarily blocked'
            ]
        }
    
    async def analyze_source_health(self, source_name: str, days: int = 7) -> SourceHealthMetrics:
        """Analyze health of a specific source"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Get articles from this source
            articles = self.db.query(Article).filter(
                and_(
                    Article.source == source_name,
                    Article.published_at >= since_date
                )
            ).all()
            
            if not articles:
                return SourceHealthMetrics(
                    source_name=source_name,
                    total_articles=0,
                    successful_extractions=0,
                    failed_extractions=0,
                    cloudflare_blocks=0,
                    paywall_hits=0,
                    low_content_articles=0,
                    duplicate_articles=0,
                    spam_articles=0,
                    extraction_success_rate=0.0,
                    content_quality_score=0.0,
                    last_successful_extraction=None,
                    issues=[],
                    health_status='unknown'
                )
            
            # Analyze each article
            issues = []
            successful_extractions = 0
            cloudflare_blocks = 0
            paywall_hits = 0
            low_content_count = 0
            spam_count = 0
            quality_scores = []
            last_successful = None
            
            for article in articles:
                # Check content extraction success
                if article.content and len(article.content.strip()) > 100:
                    successful_extractions += 1
                    if not last_successful or article.published_at > last_successful:
                        last_successful = article.published_at
                    
                    # Calculate content quality
                    quality_score = self._calculate_content_quality(article)
                    quality_scores.append(quality_score)
                    
                    if quality_score < 0.3:
                        low_content_count += 1
                else:
                    # Analyze why extraction failed
                    issue_type = await self._detect_extraction_failure_reason(article)
                    if issue_type == 'cloudflare_block':
                        cloudflare_blocks += 1
                    elif issue_type == 'paywall':
                        paywall_hits += 1
                
                # Check for spam
                if article.spam_detected:
                    spam_count += 1
            
            # Calculate metrics
            total_articles = len(articles)
            failed_extractions = total_articles - successful_extractions
            extraction_success_rate = successful_extractions / total_articles if total_articles > 0 else 0
            avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            # Generate issues
            if extraction_success_rate < self.thresholds['extraction_success_rate_critical']:
                issues.append(HealthIssue(
                    issue_type='extraction_failure',
                    severity='critical',
                    description=f'Extraction success rate critically low: {extraction_success_rate:.1%}',
                    detection_time=datetime.now(),
                    article_urls=[a.url for a in articles if not a.content][:5],
                    confidence=1.0 - extraction_success_rate
                ))
            elif extraction_success_rate < self.thresholds['extraction_success_rate_warning']:
                issues.append(HealthIssue(
                    issue_type='extraction_failure',
                    severity='medium',
                    description=f'Extraction success rate below threshold: {extraction_success_rate:.1%}',
                    detection_time=datetime.now(),
                    article_urls=[a.url for a in articles if not a.content][:3],
                    confidence=1.0 - extraction_success_rate
                ))
            
            # Cloudflare blocking issues
            cloudflare_rate = cloudflare_blocks / total_articles if total_articles > 0 else 0
            if cloudflare_rate > self.thresholds['cloudflare_rate_critical']:
                issues.append(HealthIssue(
                    issue_type='cloudflare_block',
                    severity='critical',
                    description=f'High rate of Cloudflare blocks: {cloudflare_rate:.1%}',
                    detection_time=datetime.now(),
                    article_urls=[],
                    confidence=cloudflare_rate
                ))
            
            # Paywall issues
            paywall_rate = paywall_hits / total_articles if total_articles > 0 else 0
            if paywall_rate > self.thresholds['paywall_rate_warning']:
                issues.append(HealthIssue(
                    issue_type='paywall',
                    severity='medium' if paywall_rate < self.thresholds['paywall_rate_critical'] else 'high',
                    description=f'High paywall hit rate: {paywall_rate:.1%}',
                    detection_time=datetime.now(),
                    article_urls=[],
                    confidence=paywall_rate
                ))
            
            # Determine overall health status
            health_status = self._determine_health_status(issues, extraction_success_rate, avg_quality_score)
            
            return SourceHealthMetrics(
                source_name=source_name,
                total_articles=total_articles,
                successful_extractions=successful_extractions,
                failed_extractions=failed_extractions,
                cloudflare_blocks=cloudflare_blocks,
                paywall_hits=paywall_hits,
                low_content_articles=low_content_count,
                duplicate_articles=0,  # TODO: Implement duplicate detection
                spam_articles=spam_count,
                extraction_success_rate=extraction_success_rate,
                content_quality_score=avg_quality_score,
                last_successful_extraction=last_successful,
                issues=issues,
                health_status=health_status
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze health for source {source_name}: {e}")
            raise
    
    async def analyze_all_sources(self, days: int = 7) -> Dict[str, SourceHealthMetrics]:
        """Analyze health of all sources"""
        try:
            # Get all unique sources
            sources = self.db.query(Article.source).filter(
                Article.published_at >= datetime.now() - timedelta(days=days)
            ).distinct().all()
            
            source_names = [s[0] for s in sources]
            results = {}
            
            # Analyze each source
            for source_name in source_names:
                try:
                    metrics = await self.analyze_source_health(source_name, days)
                    results[source_name] = metrics
                except Exception as e:
                    logger.warning(f"Failed to analyze source {source_name}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to analyze all sources: {e}")
            return {}
    
    def get_problematic_sources(self, days: int = 7) -> List[SourceHealthMetrics]:
        """Get sources with health issues"""
        try:
            all_metrics = asyncio.run(self.analyze_all_sources(days))
            
            # Filter sources with issues
            problematic = []
            for metrics in all_metrics.values():
                if metrics.health_status in ['degraded', 'unhealthy', 'failing']:
                    problematic.append(metrics)
            
            # Sort by severity (most problematic first)
            problematic.sort(key=lambda x: (
                len([i for i in x.issues if i.severity == 'critical']),
                len([i for i in x.issues if i.severity == 'high']),
                -x.extraction_success_rate
            ), reverse=True)
            
            return problematic
            
        except Exception as e:
            logger.error(f"Failed to get problematic sources: {e}")
            return []
    
    async def _detect_extraction_failure_reason(self, article: Article) -> str:
        """Detect why content extraction failed"""
        try:
            # If we have no content or very little content, try to fetch and analyze
            if not article.content or len(article.content.strip()) < 50:
                # Try to fetch the URL and analyze response
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            article.url, 
                            timeout=aiohttp.ClientTimeout(total=10),
                            headers={'User-Agent': 'RSS Intelligence Bot (+https://example.com/bot)'}
                        ) as response:
                            if response.status != 200:
                                return f'http_error_{response.status}'
                            
                            content = await response.text()
                            content_lower = content.lower()
                            
                            # Check for various blocking patterns
                            for issue_type, patterns in self.detection_patterns.items():
                                for pattern in patterns:
                                    if re.search(pattern, content_lower, re.IGNORECASE):
                                        return issue_type
                            
                            # If content is very short, it might be blocked
                            if len(content.strip()) < 500:
                                return 'minimal_content'
                            
                            return 'unknown_extraction_failure'
                            
                except asyncio.TimeoutError:
                    return 'timeout'
                except Exception as e:
                    return 'network_error'
            
            return 'no_issue'
            
        except Exception as e:
            logger.warning(f"Failed to detect extraction failure reason for {article.url}: {e}")
            return 'analysis_error'
    
    def _calculate_content_quality(self, article: Article) -> float:
        """Calculate content quality score"""
        try:
            if not article.content:
                return 0.0
            
            content = article.content.strip()
            title = article.title or ''
            
            quality_score = 0.0
            
            # Length score (0.3 weight)
            word_count = len(content.split())
            if word_count >= 300:
                length_score = 1.0
            elif word_count >= 150:
                length_score = 0.8
            elif word_count >= 50:
                length_score = 0.5
            else:
                length_score = 0.2
            quality_score += length_score * 0.3
            
            # Coherence score (0.2 weight)
            # Check if content relates to title
            title_words = set(title.lower().split())
            content_words = set(content.lower().split()[:100])  # First 100 words
            overlap = len(title_words & content_words) / max(len(title_words), 1)
            quality_score += min(overlap * 2, 1.0) * 0.2
            
            # Structure score (0.2 weight)
            # Check for proper sentences, paragraphs
            sentences = len(re.findall(r'[.!?]+', content))
            paragraphs = len(content.split('\n\n'))
            if sentences >= 5 and paragraphs >= 2:
                structure_score = 1.0
            elif sentences >= 3:
                structure_score = 0.7
            else:
                structure_score = 0.3
            quality_score += structure_score * 0.2
            
            # Spam/promotional score (0.3 weight)
            spam_result = self.spam_detector.detect_spam(title, content, article.source)
            spam_score = 1.0 - spam_result.spam_probability
            quality_score += spam_score * 0.3
            
            return min(1.0, quality_score)
            
        except Exception as e:
            logger.warning(f"Failed to calculate content quality for article {article.id}: {e}")
            return 0.5
    
    def _determine_health_status(self, issues: List[HealthIssue], extraction_rate: float, quality_score: float) -> str:
        """Determine overall health status"""
        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == 'critical']
        high_issues = [i for i in issues if i.severity == 'high']
        medium_issues = [i for i in issues if i.severity == 'medium']
        
        if critical_issues or extraction_rate < 0.3:
            return 'failing'
        elif high_issues or extraction_rate < 0.5 or quality_score < 0.2:
            return 'unhealthy'
        elif medium_issues or extraction_rate < 0.7 or quality_score < 0.4:
            return 'degraded'
        else:
            return 'healthy'
    
    def generate_health_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        try:
            all_metrics = asyncio.run(self.analyze_all_sources(days))
            
            # Aggregate statistics
            total_sources = len(all_metrics)
            healthy_sources = len([m for m in all_metrics.values() if m.health_status == 'healthy'])
            degraded_sources = len([m for m in all_metrics.values() if m.health_status == 'degraded'])
            unhealthy_sources = len([m for m in all_metrics.values() if m.health_status == 'unhealthy'])
            failing_sources = len([m for m in all_metrics.values() if m.health_status == 'failing'])
            
            # Calculate overall metrics
            total_articles = sum(m.total_articles for m in all_metrics.values())
            total_successful = sum(m.successful_extractions for m in all_metrics.values())
            overall_success_rate = total_successful / max(total_articles, 1)
            
            # Top issues
            all_issues = []
            for metrics in all_metrics.values():
                for issue in metrics.issues:
                    all_issues.append((metrics.source_name, issue))
            
            # Sort by severity and confidence
            severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            all_issues.sort(key=lambda x: (severity_order.get(x[1].severity, 0), x[1].confidence), reverse=True)
            
            return {
                'report_generated': datetime.now().isoformat(),
                'analysis_period_days': days,
                'summary': {
                    'total_sources': total_sources,
                    'healthy_sources': healthy_sources,
                    'degraded_sources': degraded_sources,
                    'unhealthy_sources': unhealthy_sources,
                    'failing_sources': failing_sources,
                    'overall_extraction_success_rate': round(overall_success_rate, 3),
                    'total_articles_analyzed': total_articles
                },
                'health_distribution': {
                    'healthy': round(healthy_sources / max(total_sources, 1), 2),
                    'degraded': round(degraded_sources / max(total_sources, 1), 2),
                    'unhealthy': round(unhealthy_sources / max(total_sources, 1), 2),
                    'failing': round(failing_sources / max(total_sources, 1), 2)
                },
                'top_issues': [
                    {
                        'source': source_name,
                        'issue_type': issue.issue_type,
                        'severity': issue.severity,
                        'description': issue.description,
                        'confidence': round(issue.confidence, 2)
                    }
                    for source_name, issue in all_issues[:20]
                ],
                'problematic_sources': [
                    {
                        'source': metrics.source_name,
                        'health_status': metrics.health_status,
                        'extraction_success_rate': round(metrics.extraction_success_rate, 2),
                        'content_quality_score': round(metrics.content_quality_score, 2),
                        'issue_count': len(metrics.issues),
                        'critical_issues': len([i for i in metrics.issues if i.severity == 'critical'])
                    }
                    for metrics in sorted(all_metrics.values(), 
                                        key=lambda x: (x.health_status == 'failing', 
                                                     x.health_status == 'unhealthy',
                                                     -x.extraction_success_rate))[:15]
                ],
                'recommendations': self._generate_recommendations(all_metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, all_metrics: Dict[str, SourceHealthMetrics]) -> List[str]:
        """Generate actionable recommendations based on health analysis"""
        recommendations = []
        
        failing_sources = [m for m in all_metrics.values() if m.health_status == 'failing']
        cloudflare_issues = [m for m in all_metrics.values() if any(i.issue_type == 'cloudflare_block' for i in m.issues)]
        paywall_sources = [m for m in all_metrics.values() if any(i.issue_type == 'paywall' for i in m.issues)]
        
        if failing_sources:
            recommendations.append(f"Consider removing or fixing {len(failing_sources)} failing sources")
        
        if cloudflare_issues:
            recommendations.append(f"Implement proxy rotation or user-agent rotation for {len(cloudflare_issues)} Cloudflare-blocked sources")
        
        if paywall_sources:
            recommendations.append(f"Review {len(paywall_sources)} paywall-affected sources - consider removing or finding alternative feeds")
        
        low_quality_sources = [m for m in all_metrics.values() if m.content_quality_score < 0.3]
        if low_quality_sources:
            recommendations.append(f"Review content extraction for {len(low_quality_sources)} low-quality sources")
        
        return recommendations

# Global instance
source_health_monitor = None

def get_source_health_monitor(db: Session) -> SourceHealthMonitor:
    """Get or create source health monitor"""
    return SourceHealthMonitor(db)