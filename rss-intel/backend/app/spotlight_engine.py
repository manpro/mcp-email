"""
Spotlight Engine for generating daily digests
"""
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json

from .store import (
    Article, Story, SpotlightIssue, SpotlightItem, 
    SpotlightConfig, Prediction
)


class SpotlightEngine:
    """Engine for generating daily spotlight digests"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load spotlight configuration from database"""
        config_items = self.db.query(SpotlightConfig).all()
        config = {}
        for item in config_items:
            config[item.key] = item.value
        return config
    
    def _calculate_article_score(self, article: Article) -> Tuple[float, List[str]]:
        """Calculate weighted score for article selection"""
        
        weights = self.config.get('scoring_weights', {
            'rule_score': 0.3,
            'ml_score': 0.3,
            'trend_score': 0.2,
            'freshness': 0.2
        })
        
        score = 0.0
        reasons = []
        
        # Rule-based score (normalized 0-1)
        if article.score_total:
            rule_score = min(article.score_total / 100, 1.0)
            score += rule_score * weights['rule_score']
            if rule_score > 0.5:
                reasons.append("High relevance score")
        
        # ML prediction score - skip for now since ML tables aren't set up
        prediction = None
        # TODO: Implement ML prediction scoring once ML infrastructure is ready
        
        if prediction:
            score += prediction.score * weights['ml_score']
            if prediction.score > 0.7:
                reasons.append("Personalized for you")
        
        # Trend score (based on story source count if clustered)
        trend_score = 0.0
        if article.story_id:
            story = self.db.query(Story).filter_by(id=article.story_id).first()
            if story and story.sources:
                source_count = len(story.sources)
                trend_score = min(source_count / 10, 1.0)  # Normalize to 0-1
                score += trend_score * weights['trend_score']
                if source_count >= 3:
                    reasons.append(f"Trending ({source_count} sources)")
        
        # Freshness score
        from datetime import timezone
        now = datetime.now(timezone.utc)
        hours_old = (now - article.published_at).total_seconds() / 3600
        freshness_score = max(0, 1 - (hours_old / 48))  # Decay over 48 hours
        score += freshness_score * weights['freshness']
        if hours_old < 6:
            reasons.append("Breaking news")
        
        # Bonus for watchlist items
        if article.entities and article.entities.get('matched'):
            score += 0.1
            reasons.append("Watchlist match")
        
        # Bonus for extracted content
        if article.extraction_status == 'success' and article.full_content:
            score += 0.05
            reasons.append("Full content available")
        
        return score, reasons[:3]  # Return top 3 reasons
    
    def _generate_summary(self, article: Article) -> str:
        """Generate a short summary for the article"""
        
        config = self.config.get('summary_config', {
            'max_length': 220,
            'language': 'en',
            'style': 'factual'
        })
        
        # For now, use a simple heuristic approach
        # Later this will be replaced with GPT-OSS integration
        
        if article.content_summary:
            # Use existing summary if available
            summary = article.content_summary
        elif article.full_content:
            # Extract first meaningful sentences from full content
            sentences = article.full_content.split('.')[:2]
            summary = '. '.join(sentences).strip() + '.'
        elif article.content:
            # Use article content/description
            summary = article.content
        else:
            # Fallback to title
            summary = article.title
        
        # Truncate to max length
        max_length = config['max_length']
        if len(summary) > max_length:
            summary = summary[:max_length-3] + '...'
        
        return summary
    
    def select_articles(self, window_hours: int = 24) -> Tuple[List[Article], List[Article]]:
        """Select articles for must_read and also_worth sections"""
        
        # Get articles from the past window  
        from datetime import timezone
        now = datetime.now(timezone.utc)
        since_date = now - timedelta(hours=window_hours)
        
        # Query articles with scores - filter out articles without readable content
        articles = self.db.query(Article).filter(
            Article.published_at >= since_date
        ).filter(
            # Require at least some form of readable content
            Article.full_content.isnot(None) | 
            Article.content_summary.isnot(None) |
            (Article.content.isnot(None) & (func.length(Article.content) > 50))
        ).all()
        
        # Calculate scores and sort
        scored_articles = []
        for article in articles:
            score, reasons = self._calculate_article_score(article)
            scored_articles.append({
                'article': article,
                'score': score,
                'reasons': reasons
            })
        
        scored_articles.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply diversity rules
        diversity_rules = self.config.get('diversity_rules', {
            'max_per_source': 2,
            'max_per_topic': 3,
            'require_watchlist': True
        })
        
        must_read = []
        also_worth = []
        source_counts = {}
        topic_counts = {}
        has_watchlist = False
        
        sections_config = self.config.get('sections', {
            'must_read': 3,
            'also_worth': 5
        })
        
        for item in scored_articles:
            article = item['article']
            
            # Check diversity constraints
            if article.source in source_counts:
                if source_counts[article.source] >= diversity_rules['max_per_source']:
                    continue
            
            # Check topic constraints
            for topic in article.topics or []:
                if topic in topic_counts:
                    if topic_counts[topic] >= diversity_rules['max_per_topic']:
                        continue
            
            # Add to appropriate section
            if len(must_read) < sections_config['must_read']:
                must_read.append(item)
            elif len(also_worth) < sections_config['also_worth']:
                also_worth.append(item)
            else:
                break  # We have enough articles
            
            # Update counts
            source_counts[article.source] = source_counts.get(article.source, 0) + 1
            for topic in article.topics or []:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Track watchlist
            if article.entities and article.entities.get('matched'):
                has_watchlist = True
        
        # Ensure at least one watchlist item if required
        if diversity_rules['require_watchlist'] and not has_watchlist:
            # Find a watchlist article and swap it in
            for item in scored_articles:
                article = item['article']
                if article.entities and article.entities.get('matched'):
                    if must_read and item not in must_read:
                        must_read[-1] = item  # Replace lowest must_read
                        break
        
        return must_read, also_worth
    
    def generate_digest(self, target_date: Optional[date] = None) -> SpotlightIssue:
        """Generate a spotlight digest for the given date"""
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        if not target_date:
            target_date = date.today()
        
        # Check if digest already exists for this date
        existing = self.db.query(SpotlightIssue).filter_by(
            issue_date=target_date
        ).first()
        
        if existing:
            return existing
        
        # Select articles
        must_read, also_worth = self.select_articles()
        
        # Create issue
        issue = SpotlightIssue(
            issue_date=target_date,
            title=f"Daily Spotlight - {target_date.strftime('%B %d, %Y')}",
            subtitle=f"{len(must_read)} must-read stories and {len(also_worth)} also worth your time",
            generated_at=now,
            published=False,
            metrics={
                'total_articles_considered': self.db.query(Article).filter(
                    Article.published_at >= now - timedelta(hours=24)
                ).count(),
                'must_read_count': len(must_read),
                'also_worth_count': len(also_worth)
            }
        )
        
        self.db.add(issue)
        self.db.flush()  # Get the ID
        
        # Create items
        position = 0
        
        # Add must-read items
        for item in must_read:
            article = item['article']
            summary = self._generate_summary(article)
            
            spotlight_item = SpotlightItem(
                issue_id=issue.id,
                story_id=article.story_id,
                article_id=article.id,
                section='must_read',
                position=position,
                summary=summary,
                summary_language='en',
                recommendation_score=item['score'],
                recommendation_reasons=item['reasons']
            )
            
            self.db.add(spotlight_item)
            position += 1
        
        # Add also-worth items
        position = 0
        for item in also_worth:
            article = item['article']
            summary = self._generate_summary(article)
            
            spotlight_item = SpotlightItem(
                issue_id=issue.id,
                story_id=article.story_id,
                article_id=article.id,
                section='also_worth',
                position=position,
                summary=summary,
                summary_language='en',
                recommendation_score=item['score'],
                recommendation_reasons=item['reasons']
            )
            
            self.db.add(spotlight_item)
            position += 1
        
        self.db.commit()
        return issue
    
    def publish_issue(self, issue_id: int) -> bool:
        """Mark an issue as published"""
        
        issue = self.db.query(SpotlightIssue).filter_by(id=issue_id).first()
        if not issue:
            return False
        
        issue.published = True
        self.db.commit()
        return True
    
    def export_as_json(self, issue: SpotlightIssue) -> Dict[str, Any]:
        """Export spotlight issue as JSON"""
        
        # Use direct JOIN query instead of relationships
        from sqlalchemy import select
        query = select(SpotlightItem, Article).join(
            Article, SpotlightItem.article_id == Article.id
        ).where(
            SpotlightItem.issue_id == issue.id
        ).order_by(SpotlightItem.section, SpotlightItem.position)
        
        results = self.db.execute(query).all()
        
        must_read_items = []
        also_worth_items = []
        
        for item, article in results:
            item_data = {
                'id': article.id,  # Use article.id directly
                'freshrss_entry_id': article.freshrss_entry_id,
                'title': article.title,
                'url': article.url,
                'source': article.source,
                'published_at': article.published_at.isoformat(),
                'summary': item.summary,
                'reasons': item.recommendation_reasons,
                'score': item.recommendation_score,
                'has_image': article.has_image,
                'image_url': article.image_proxy_path
            }
            
            if item.section == 'must_read':
                must_read_items.append(item_data)
            else:
                also_worth_items.append(item_data)
        
        return {
            'issue_date': issue.issue_date.isoformat(),
            'title': issue.title,
            'subtitle': issue.subtitle,
            'generated_at': issue.generated_at.isoformat(),
            'published': issue.published,
            'must_read': must_read_items,
            'also_worth': also_worth_items,
            'metrics': issue.metrics
        }
    
    def export_as_rss(self, issue: SpotlightIssue) -> str:
        """Export spotlight issue as RSS feed"""
        
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Create RSS root
        rss = Element('rss', version='2.0')
        channel = SubElement(rss, 'channel')
        
        # Channel metadata
        SubElement(channel, 'title').text = issue.title
        SubElement(channel, 'description').text = issue.subtitle
        SubElement(channel, 'link').text = f"http://localhost:3001/spotlight/{issue.issue_date}"
        SubElement(channel, 'pubDate').text = issue.generated_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Add items with eager loading of article relationship
        from sqlalchemy.orm import joinedload
        items = self.db.query(SpotlightItem).options(
            joinedload(SpotlightItem.article)
        ).filter_by(
            issue_id=issue.id
        ).order_by(SpotlightItem.section, SpotlightItem.position).all()
        
        for spotlight_item in items:
            article = spotlight_item.article
            
            item = SubElement(channel, 'item')
            SubElement(item, 'title').text = f"[{spotlight_item.section.replace('_', ' ').title()}] {article.title}"
            SubElement(item, 'description').text = spotlight_item.summary
            SubElement(item, 'link').text = article.url
            SubElement(item, 'guid').text = f"spotlight-{issue.id}-{spotlight_item.id}"
            SubElement(item, 'pubDate').text = article.published_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
            SubElement(item, 'source', url=article.url).text = article.source
            
            # Add categories for reasons
            for reason in spotlight_item.recommendation_reasons or []:
                SubElement(item, 'category').text = reason
        
        # Pretty print
        rough_string = tostring(rss, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


def generate_daily_spotlight(db: Session) -> Dict[str, Any]:
    """Helper function for scheduler to generate daily spotlight"""
    
    engine = SpotlightEngine(db)
    issue = engine.generate_digest()
    
    return {
        'success': True,
        'issue_id': issue.id,
        'issue_date': issue.issue_date.isoformat(),
        'must_read_count': len([i for i in issue.items if i.section == 'must_read']),
        'also_worth_count': len([i for i in issue.items if i.section == 'also_worth'])
    }