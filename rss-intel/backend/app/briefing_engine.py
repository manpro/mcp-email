#!/usr/bin/env python3
"""
Daily Briefings Engine for generating morning, lunch, and evening summaries
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, date, time
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json

from .store import (
    Article, Story, DailyBriefing, BriefingItem
)
from .config import settings
from .rag_engine import rag_engine

logger = logging.getLogger(__name__)


class BriefingEngine:
    """Engine for generating daily briefings at different time slots"""
    
    def __init__(self, db: Session):
        self.db = db
        self.time_slots = {
            'morning': {
                'time': time(8, 0),  # 08:00
                'hours_back': 18,    # From 2pm yesterday
                'max_items': 8,
                'description': 'Morning briefing with overnight and early news'
            },
            'lunch': {
                'time': time(12, 0),  # 12:00
                'hours_back': 6,     # From 6am today
                'max_items': 6,
                'description': 'Lunch briefing with morning developments'
            },
            'evening': {
                'time': time(20, 0),  # 20:00
                'hours_back': 10,    # From 10am today
                'max_items': 10,
                'description': 'Evening briefing with full day coverage'
            }
        }
    
    def _calculate_article_relevance(self, article: Article, time_slot: str) -> Tuple[float, List[str]]:
        """Calculate relevance score for article selection in briefings"""
        
        config = self.time_slots[time_slot]
        score = 0.0
        reasons = []
        
        # Base score from article scoring
        if article.score_total and article.score_total > 0:
            base_score = min(article.score_total / 100, 1.0)
            score += base_score * 0.4
            if base_score > 0.6:
                reasons.append("High relevance score")
        
        # Freshness scoring - more important for briefings
        from datetime import timezone
        now = datetime.now(timezone.utc)
        hours_old = (now - article.published_at).total_seconds() / 3600
        target_hours = config['hours_back']
        
        # Peak score at 2-4 hours old, decay after that
        if hours_old <= 2:
            freshness_score = 1.0
            reasons.append("Breaking news")
        elif hours_old <= 4:
            freshness_score = 0.9
            reasons.append("Very recent")
        elif hours_old <= target_hours:
            freshness_score = 0.8 - ((hours_old - 4) / target_hours) * 0.3
        else:
            freshness_score = 0.3  # Still relevant but older
        
        score += freshness_score * 0.3
        
        # Story clustering bonus
        if article.story_id:
            story = self.db.query(Story).filter_by(id=article.story_id).first()
            if story and story.sources:
                source_count = len(story.sources)
                if source_count >= 3:
                    score += 0.2
                    reasons.append(f"Multiple sources ({source_count})")
        
        # Content quality bonus
        content_quality = 0.0
        if article.full_content and len(article.full_content) > 500:
            content_quality += 0.15
            reasons.append("Full content available")
        elif article.content_summary:
            content_quality += 0.1
            reasons.append("Summary available")
        elif article.content and len(article.content) > 100:
            content_quality += 0.05
        
        score += content_quality
        
        # Image bonus for visual appeal
        if article.has_image and article.image_proxy_path:
            score += 0.1
            reasons.append("Has image")
        
        # Time slot specific adjustments
        if time_slot == 'morning':
            # Prefer overnight developments and market news
            morning_keywords = ['market', 'stock', 'trading', 'overnight', 'asian', 'futures']
            title_lower = article.title.lower()
            if any(keyword in title_lower for keyword in morning_keywords):
                score += 0.15
                reasons.append("Morning relevant content")
        
        elif time_slot == 'lunch':
            # Prefer breaking news and quick updates
            if hours_old < 3:
                score += 0.2
                reasons.append("Lunch-time breaking news")
        
        elif time_slot == 'evening':
            # Prefer comprehensive coverage and analysis
            analysis_keywords = ['analysis', 'outlook', 'review', 'summary', 'impact']
            title_lower = article.title.lower()
            if any(keyword in title_lower for keyword in analysis_keywords):
                score += 0.15
                reasons.append("Analysis content")
        
        return score, reasons[:3]  # Return top 3 reasons
    
    def _generate_ai_summary(self, article: Article) -> Optional[str]:
        """Generate AI-powered summary using OpenAI GPT-4o-mini"""
        
        if not settings.openai_api_key or not rag_engine.openai_client:
            return None
        
        try:
            # Prepare content for summarization
            content_for_summary = ""
            if article.full_content:
                content_for_summary = article.full_content[:2000]  # Limit to 2000 chars
            elif article.content_summary:
                content_for_summary = article.content_summary
            elif article.content:
                content_for_summary = article.content
            else:
                content_for_summary = article.title
            
            # Detect language from content
            # Simple heuristic: check for Swedish characters or words
            swedish_indicators = ['å', 'ä', 'ö', 'Å', 'Ä', 'Ö', 'och', 'att', 'det', 'som', 'för']
            content_lower = (article.title + ' ' + content_for_summary[:500]).lower()
            is_swedish = any(indicator in content_lower for indicator in swedish_indicators)
            
            # Determine target language
            if is_swedish:
                language_instruction = "in Swedish"
                system_instruction = "You are a helpful news summarizer. Create concise, factual summaries in Swedish."
            else:
                language_instruction = "in English"
                system_instruction = "You are a helpful news summarizer. Create concise, factual summaries in English."
            
            # Create summarization prompt
            prompt = f"""Please create a concise, factual summary of this news article {language_instruction}. 
The summary should be 2-3 sentences and capture the key information without editorializing.
Keep the summary in the same language as the original article, or use English if the language is not Swedish or English.

Article Title: {article.title}
Source: {article.source}
Content: {content_for_summary}

Summary:"""
            
            # Call OpenAI API
            response = rag_engine.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.2,
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated AI summary for article {article.id} in {'Swedish' if is_swedish else 'English'}")
            return summary
            
        except Exception as e:
            logger.error(f"AI summary generation failed for article {article.id}: {e}")
            return None
    
    def select_articles_for_briefing(self, time_slot: str, target_date: date) -> List[Dict[str, Any]]:
        """Select articles for a specific briefing time slot"""
        
        if time_slot not in self.time_slots:
            raise ValueError(f"Invalid time slot: {time_slot}")
        
        config = self.time_slots[time_slot]
        
        # Calculate time window
        from datetime import timezone, datetime as dt
        target_datetime = dt.combine(target_date, config['time'])
        start_time = target_datetime - timedelta(hours=config['hours_back'])
        end_time = target_datetime + timedelta(hours=2)  # Small buffer for late content
        
        # Query articles in time window with readable content
        articles = self.db.query(Article).filter(
            Article.published_at >= start_time,
            Article.published_at <= end_time,
            Article.score_total >= 0  # Exclude spam
        ).filter(
            # Require readable content
            Article.full_content.isnot(None) | 
            Article.content_summary.isnot(None) |
            (Article.content.isnot(None) & (func.length(Article.content) > 50))
        ).all()
        
        # Score and rank articles
        scored_articles = []
        for article in articles:
            score, reasons = self._calculate_article_relevance(article, time_slot)
            scored_articles.append({
                'article': article,
                'score': score,
                'reasons': reasons
            })
        
        # Sort by score
        scored_articles.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply diversity rules to avoid source/topic clustering
        # First, categorize articles by content type
        categories = {
            'ai': [],
            'crypto': [], 
            'payments': [],
            'other': []
        }
        
        for item in scored_articles:
            article = item['article']
            title_lower = article.title.lower()
            content_lower = (article.content or '').lower()
            combined_text = title_lower + ' ' + content_lower
            
            # Categorize based on keywords
            if any(keyword in combined_text for keyword in ['ai', 'artificial intelligence', 'machine learning', 'neural', 'llm', 'gpt', 'arxiv', 'research']):
                categories['ai'].append(item)
            elif any(keyword in combined_text for keyword in ['crypto', 'bitcoin', 'ethereum', 'blockchain', 'defi']):
                categories['crypto'].append(item)
            elif any(keyword in combined_text for keyword in ['payment', 'fintech', 'banking', 'visa', 'mastercard', 'stripe']):
                categories['payments'].append(item)
            else:
                categories['other'].append(item)
        
        # Ensure diversity by selecting from each category
        selected_articles = []
        source_count = {}
        max_per_source = 2
        
        # Priority allocation per category based on max_items
        max_items = config['max_items']
        if max_items >= 6:
            # For larger briefings, ensure representation from each category
            category_targets = {'ai': max(2, max_items // 4), 'crypto': max(1, max_items // 5), 'payments': max(1, max_items // 5), 'other': max_items}
        else:
            # For smaller briefings, still try to get at least one from each if available
            category_targets = {'ai': max(1, max_items // 3), 'crypto': 1, 'payments': 1, 'other': max_items}
        
        # Select articles ensuring diversity
        for category in ['ai', 'crypto', 'payments', 'other']:
            target = category_targets.get(category, 1)
            selected_from_category = 0
            
            for item in categories[category]:
                if len(selected_articles) >= max_items:
                    break
                if selected_from_category >= target:
                    break
                    
                article = item['article']
                
                # Source diversity check
                source_articles = source_count.get(article.source, 0)
                if source_articles >= max_per_source:
                    continue
                
                # Add to selection
                selected_articles.append(item)
                source_count[article.source] = source_articles + 1
                selected_from_category += 1
            
            if len(selected_articles) >= max_items:
                break
        
        # Fill remaining slots with highest scoring articles if we haven't reached max_items
        for item in scored_articles:
            if len(selected_articles) >= max_items:
                break
            
            # Skip if already selected
            if item in selected_articles:
                continue
                
            article = item['article']
            
            # Source diversity check
            source_articles = source_count.get(article.source, 0)
            if source_articles >= max_per_source:
                continue
            
            # Add to selection
            selected_articles.append(item)
            source_count[article.source] = source_articles + 1
        
        logger.info(f"Selected {len(selected_articles)} articles for {time_slot} briefing on {target_date}")
        return selected_articles
    
    def generate_briefing(self, time_slot: str, target_date: Optional[date] = None) -> DailyBriefing:
        """Generate a daily briefing for the given time slot and date"""
        
        if time_slot not in self.time_slots:
            raise ValueError(f"Invalid time slot: {time_slot}")
        
        if not target_date:
            target_date = date.today()
        
        # Check if briefing already exists
        existing = self.db.query(DailyBriefing).filter_by(
            briefing_date=target_date,
            time_slot=time_slot
        ).first()
        
        if existing:
            logger.info(f"Briefing already exists for {time_slot} on {target_date}")
            return existing
        
        # Select articles
        selected_articles = self.select_articles_for_briefing(time_slot, target_date)
        
        if not selected_articles:
            logger.warning(f"No articles found for {time_slot} briefing on {target_date}")
        
        # Create briefing
        config = self.time_slots[time_slot]
        
        # Generate titles based on time slot
        time_slot_titles = {
            'morning': f"Morgonöversikt - {target_date.strftime('%d %B %Y')}",
            'lunch': f"Lunchuppdatering - {target_date.strftime('%d %B %Y')}",
            'evening': f"Kvällssammanfattning - {target_date.strftime('%d %B %Y')}"
        }
        
        briefing = DailyBriefing(
            briefing_date=target_date,
            time_slot=time_slot,
            title=time_slot_titles[time_slot],
            subtitle=f"{len(selected_articles)} viktigaste nyheterna från {config['description']}",
            published=False,
            metrics={
                'total_articles_considered': len(self.db.query(Article).filter(
                    Article.published_at >= datetime.now() - timedelta(hours=config['hours_back'])
                ).all()),
                'articles_selected': len(selected_articles),
                'ai_summaries_generated': 0
            }
        )
        
        self.db.add(briefing)
        self.db.flush()  # Get the ID
        
        # Create briefing items
        ai_summary_count = 0
        for position, item_data in enumerate(selected_articles):
            article = item_data['article']
            
            # Generate AI summary if possible
            ai_summary = self._generate_ai_summary(article)
            if ai_summary:
                ai_summary_count += 1
            
            # Use existing summary or fallback
            display_summary = ai_summary or article.content_summary or article.content or article.title
            if len(display_summary) > 300:
                display_summary = display_summary[:297] + "..."
            
            briefing_item = BriefingItem(
                briefing_id=briefing.id,
                story_id=article.story_id,
                article_id=article.id,
                position=position,
                title=article.title,
                summary=display_summary,
                ai_summary=ai_summary,
                recommendation_score=item_data['score'],
                recommendation_reasons=item_data['reasons']
            )
            
            self.db.add(briefing_item)
        
        # Update metrics
        briefing.metrics['ai_summaries_generated'] = ai_summary_count
        
        self.db.commit()
        logger.info(f"Generated {time_slot} briefing for {target_date} with {len(selected_articles)} items")
        return briefing
    
    def get_briefings_for_date(self, target_date: date) -> Dict[str, Optional[DailyBriefing]]:
        """Get all briefings for a specific date"""
        
        briefings = {}
        for time_slot in self.time_slots.keys():
            briefing = self.db.query(DailyBriefing).filter_by(
                briefing_date=target_date,
                time_slot=time_slot
            ).first()
            briefings[time_slot] = briefing
        
        return briefings
    
    def export_briefing_as_json(self, briefing: DailyBriefing) -> Dict[str, Any]:
        """Export briefing as JSON"""
        
        # Get briefing items with article data
        from sqlalchemy import select
        query = select(BriefingItem, Article).join(
            Article, BriefingItem.article_id == Article.id
        ).where(
            BriefingItem.briefing_id == briefing.id
        ).order_by(BriefingItem.position)
        
        results = self.db.execute(query).all()
        
        items_data = []
        for item, article in results:
            item_data = {
                'id': article.id,
                'title': item.title,
                'summary': item.summary,
                'ai_summary': item.ai_summary,
                'url': article.url,
                'source': article.source,
                'published_at': article.published_at.isoformat(),
                'reasons': item.recommendation_reasons,
                'score': item.recommendation_score,
                'has_image': article.has_image,
                'image_url': article.image_proxy_path,
                'position': item.position
            }
            items_data.append(item_data)
        
        return {
            'briefing_date': briefing.briefing_date.isoformat(),
            'time_slot': briefing.time_slot,
            'title': briefing.title,
            'subtitle': briefing.subtitle,
            'generated_at': briefing.generated_at.isoformat(),
            'published': briefing.published,
            'items': items_data,
            'metrics': briefing.metrics
        }


def generate_daily_briefings(db: Session, target_date: Optional[date] = None) -> Dict[str, Any]:
    """Helper function for scheduler to generate all daily briefings"""
    
    if not target_date:
        target_date = date.today()
    
    engine = BriefingEngine(db)
    results = {}
    
    for time_slot in ['morning', 'lunch', 'evening']:
        try:
            briefing = engine.generate_briefing(time_slot, target_date)
            results[time_slot] = {
                'success': True,
                'briefing_id': briefing.id,
                'items_count': len(briefing.items) if briefing.items else 0
            }
        except Exception as e:
            logger.error(f"Failed to generate {time_slot} briefing: {e}")
            results[time_slot] = {
                'success': False,
                'error': str(e)
            }
    
    return {
        'date': target_date.isoformat(),
        'briefings': results,
        'total_success': sum(1 for r in results.values() if r['success'])
    }