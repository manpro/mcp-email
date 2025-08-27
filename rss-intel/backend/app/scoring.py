import re
import math
import yaml
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path
from .config import settings

logger = logging.getLogger(__name__)

class ScoringEngine:
    def __init__(self):
        self.config_dir = Path(settings.config_dir)
        self.scoring_config = self._load_config("scoring.yml")
        self.watchlist_config = self._load_config("watchlist.yml")
        self.sources_config = self._load_config("sources.yml")
        
    def _load_config(self, filename: str) -> Dict:
        """Load YAML configuration file"""
        config_path = self.config_dir / filename
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return self._get_default_config(filename)
    
    def _get_default_config(self, filename: str) -> Dict:
        """Return default configuration if file doesn't exist"""
        defaults = {
            "scoring.yml": {
                "keywords": {
                    "ai": 10,
                    "payments": 12,
                    "visa": 15,
                    "mastercard": 15,
                    "crypto": 10,
                    "regulation": 8,
                    "fintech": 10,
                    "banking": 8,
                    "blockchain": 9,
                    "api": 7,
                    "security": 8
                },
                "source_weights": {
                    "finextra.com": 8,
                    "thepaypers.com": 6,
                    "riksbank.se": 10,
                    "reddit.com": 4,
                    "github.com": 6
                },
                "recency": {
                    "half_life_hours": settings.scoring_half_life_hours
                },
                "thresholds": {
                    "star": settings.scoring_star_threshold,
                    "interesting": settings.scoring_interest_threshold
                }
            },
            "watchlist.yml": {
                "entities": [
                    "Klarna", "Adyen", "Stripe", "Swish", "SEB",
                    "Swedbank", "Nordea", "Handelsbanken", "PayPal",
                    "Square", "Revolut", "Wise", "N26"
                ],
                "weights": {
                    "default": 12
                },
                "labels": {
                    "prefix": "watch:"
                }
            },
            "sources.yml": {
                "rsshub": {
                    "enabled": True,
                    "routes": [
                        "/github/trending/daily/javascript",
                        "/reddit/r/fintech/top/week"
                    ]
                },
                "native_feeds": [
                    "https://finextra.com/rss",
                    "https://www.riksbank.se/sv/press-och-publicerat/nyheter/rss/"
                ]
            }
        }
        return defaults.get(filename, {})
    
    def calculate_score(self, 
                       title: str, 
                       content: str, 
                       source: str, 
                       published_at: datetime,
                       has_image: bool = False) -> Tuple[int, Dict[str, Any], List[str], List[str], Dict[str, Any]]:
        """
        Calculate article score based on multiple signals
        Returns: (total_score, score_breakdown, topics, matched_entities, event_flags)
        """
        scores = {}
        topics = []
        matched_entities = []
        
        # Combine title and content for analysis
        full_text = f"{title} {content}".lower()
        
        # Quality check - identify poor quality content
        quality_penalty = self._calculate_quality_penalty(title, content, source, published_at)
        
        # 1. Keyword scoring
        keyword_score = 0
        matched_keywords = []
        for keyword, weight in self.scoring_config.get("keywords", {}).items():
            # Use word boundaries for more accurate matching
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, full_text))
            if matches > 0:
                # Diminishing returns for multiple matches
                score_contrib = weight * (1 + math.log(matches))
                keyword_score += score_contrib
                matched_keywords.append(keyword)
                topics.append(keyword)
        
        scores["keywords"] = round(keyword_score)
        
        # 2. Watchlist entity scoring
        watchlist_score = 0
        watchlist_config = self.watchlist_config
        default_weight = watchlist_config.get("weights", {}).get("default", 12)
        
        for entity in watchlist_config.get("entities", []):
            pattern = r'\b' + re.escape(entity.lower()) + r'\b'
            if re.search(pattern, full_text):
                entity_weight = watchlist_config.get("weights", {}).get(entity, default_weight)
                watchlist_score += entity_weight
                matched_entities.append(entity)
        
        scores["watchlist"] = round(watchlist_score)
        
        # 3. Source weight
        source_weights = self.scoring_config.get("source_weights", {})
        source_score = 0
        
        # Extract domain from source
        source_domain = source.lower()
        for domain, weight in source_weights.items():
            if domain in source_domain:
                source_score = weight
                break
        
        scores["source"] = source_score
        
        # 4. Image bonus
        image_bonus = 3 if has_image else 0
        scores["image_bonus"] = image_bonus
        
        # 5. Recency decay
        age_hours = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600
        
        # 6. Future penalty - heavily penalize articles with future dates (likely events/webinars)
        future_penalty = 0
        if age_hours < 0:  # Article is in the future
            days_future = abs(age_hours) / 24
            # Heavy penalty: -100 points per day in future
            # A webinar 3 months away gets -9000 points
            future_penalty = -100 * days_future
            
        scores["future_penalty"] = round(future_penalty)
        
        # Clamp age_hours to reasonable bounds to prevent overflow
        # Articles from future get age_hours = 0, articles older than 30 days get heavily penalized
        age_hours = max(0, min(age_hours, 30 * 24))  # Clamp between 0 and 30 days
        
        half_life = self.scoring_config.get("recency", {}).get("half_life_hours", 36)
        recency_factor = math.exp(-age_hours / half_life)
        
        # Apply recency as a multiplier to the base score, then add future penalty and quality penalty
        base_score = sum([v for k, v in scores.items() if k not in ["future_penalty", "quality_penalty"]])
        score_with_recency = round(base_score * recency_factor)
        total_score = score_with_recency + future_penalty + quality_penalty
        
        # Prevent database integer overflow (PostgreSQL integer max is ~2.1 billion)
        total_score = min(total_score, 2_000_000_000)
        
        scores["recency_factor"] = round(recency_factor * 100) / 100
        scores["base_score"] = base_score
        scores["quality_penalty"] = quality_penalty
        
        # Add spam detection flags for debugging and filtering
        spam_flags = {}
        if quality_penalty <= -100:
            spam_flags["spam_risk"] = "SEVERE"
            spam_flags["auto_hidden"] = True
        elif quality_penalty <= -50:
            spam_flags["spam_risk"] = "HIGH" 
        elif quality_penalty <= -25:
            spam_flags["spam_risk"] = "MEDIUM"
        else:
            spam_flags["spam_risk"] = "LOW"
            
        spam_flags["spam_penalty"] = quality_penalty
        
        # 7. Event/webinar detection - add flags
        event_flags = self._detect_event_article(title, content, source, published_at)
        event_flags.update(spam_flags)  # Merge spam flags with event flags
        
        return total_score, scores, list(set(topics)), matched_entities, event_flags
    
    def _detect_event_article(self, title: str, content: str, source: str, published_at: datetime) -> Dict[str, bool]:
        """Detect if article is likely an event/webinar and return relevant flags"""
        flags = {}
        
        full_text = f"{title} {content}".lower()
        
        # Check for event URL patterns
        event_url_patterns = [
            'event-info',
            'webinar',
            'events/',
            'event/',
            '/conference'
        ]
        
        is_event_url = any(pattern in source.lower() for pattern in event_url_patterns)
        flags["is_event_url"] = is_event_url
        
        # Check for event-related keywords
        event_keywords = [
            'webinar', 'register', 'sign up', 'join our', 'panel of experts',
            'hosted in association', 'event', 'conference', 'summit',
            'register for this', 'join this', 'attend', 'speakers include'
        ]
        
        event_keyword_matches = sum(1 for keyword in event_keywords if keyword in full_text)
        flags["event_keyword_count"] = event_keyword_matches
        flags["has_event_keywords"] = event_keyword_matches >= 2
        
        # Check if published date is in future (strong indicator of event)
        now = datetime.now(timezone.utc)
        flags["is_future_dated"] = published_at > now
        
        # Calculate days in future
        if published_at > now:
            flags["days_in_future"] = (published_at - now).days
        else:
            flags["days_in_future"] = 0
            
        # Overall event confidence score
        confidence_score = 0
        if is_event_url:
            confidence_score += 40
        if flags["has_event_keywords"]:
            confidence_score += 30
        if flags["is_future_dated"]:
            confidence_score += 20
        if flags["days_in_future"] > 30:  # Event more than month away
            confidence_score += 10
            
        flags["event_confidence"] = confidence_score
        flags["likely_event"] = confidence_score >= 50
        
        return flags
    
    def get_labels_for_score(self, score: int, matched_entities: List[str]) -> List[str]:
        """Determine which labels should be applied based on score"""
        labels = []
        thresholds = self.scoring_config.get("thresholds", {})
        
        if score >= thresholds.get("star", 80):
            labels.append("hot")
        elif score >= thresholds.get("interesting", 60):
            labels.append("interesting")
        
        # Add watchlist labels
        prefix = self.watchlist_config.get("labels", {}).get("prefix", "watch:")
        for entity in matched_entities:
            labels.append(f"{prefix}{entity.lower().replace(' ', '_')}")
        
        return labels
    
    def should_star(self, score: int) -> bool:
        """Check if article should be starred"""
        return score >= self.scoring_config.get("thresholds", {}).get("star", 80)
    
    def extract_topics(self, text: str) -> List[str]:
        """Simple topic extraction based on keywords and patterns"""
        topics = []
        
        # Technology topics
        tech_patterns = {
            "ai": r'\b(ai|artificial intelligence|machine learning|ml|deep learning)\b',
            "blockchain": r'\b(blockchain|crypto|bitcoin|ethereum|defi)\b',
            "payments": r'\b(payment|transaction|checkout|settlement)\b',
            "security": r'\b(security|fraud|cyber|breach|vulnerability)\b',
            "api": r'\b(api|rest|graphql|webhook|integration)\b',
            "cloud": r'\b(cloud|aws|azure|gcp|kubernetes|docker)\b',
        }
        
        text_lower = text.lower()
        for topic, pattern in tech_patterns.items():
            if re.search(pattern, text_lower):
                topics.append(topic)
        
        return topics
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Simple entity extraction (placeholder for NER)"""
        entities = {
            "companies": [],
            "products": [],
            "people": []
        }
        
        # Check for known companies from watchlist
        for entity in self.watchlist_config.get("entities", []):
            if entity.lower() in text.lower():
                entities["companies"].append(entity)
        
        # Simple pattern matching for common entities
        # This is a placeholder - in production, use proper NER
        
        return entities
    
    def _calculate_quality_penalty(self, title: str, content: str, source: str, published_at: datetime) -> int:
        """
        Calculate penalty for low quality content using advanced spam detection
        Returns negative score for poor quality indicators
        """
        try:
            # Import here to avoid circular imports
            from .intelligence import spam_detector
            
            # Run comprehensive spam detection
            spam_result = spam_detector.detect_spam(title, content, source)
            
            # Calculate penalty based on spam detection results
            penalty = 0
            
            # Base penalty from spam probability (0 to -100)
            penalty -= int(spam_result.spam_probability * 100)
            
            # Additional penalty based on content score (0 to -50)
            content_quality_penalty = int((1.0 - spam_result.content_score) * 50)
            penalty -= content_quality_penalty
            
            # Title coherence penalty (0 to -30)
            coherence_penalty = int((1.0 - spam_result.title_content_coherence) * 30)
            penalty -= coherence_penalty
            
            # Signal-based penalties
            for signal in spam_result.spam_signals:
                signal_penalty = 0
                if signal.type == "promotional_content":
                    signal_penalty = int(signal.confidence * 40)  # Up to -40
                elif signal.type == "future_events_spam":
                    signal_penalty = int(signal.confidence * 30)  # Up to -30
                elif signal.type == "thin_content":
                    signal_penalty = int(signal.confidence * 50)  # Up to -50
                elif signal.type == "title_mismatch":
                    signal_penalty = int(signal.confidence * 60)  # Up to -60
                elif signal.type == "clickbait":
                    signal_penalty = int(signal.confidence * 25)  # Up to -25
                
                penalty -= signal_penalty
            
            # Quality issue penalties
            for issue in spam_result.quality_issues:
                issue_penalty = 0
                if issue.severity == "critical":
                    issue_penalty = int(issue.confidence * 40)
                elif issue.severity == "high":
                    issue_penalty = int(issue.confidence * 30)
                elif issue.severity == "medium":
                    issue_penalty = int(issue.confidence * 20)
                elif issue.severity == "low":
                    issue_penalty = int(issue.confidence * 10)
                
                penalty -= issue_penalty
            
            # Cap the maximum penalty to prevent extreme negative scores
            penalty = max(penalty, -500)  # Maximum penalty of -500
            
            return penalty
            
        except Exception as e:
            logger.error(f"Error in advanced quality penalty calculation: {str(e)}")
            # Fallback to basic quality penalty
            return self._calculate_basic_quality_penalty(title, content, source, published_at)
    
    def _calculate_basic_quality_penalty(self, title: str, content: str, source: str, published_at: datetime) -> int:
        """
        Basic quality penalty as fallback when advanced detection fails
        """
        penalty = 0
        full_text = f"{title} {content}".lower()
        
        # 1. Check for very short content (likely incomplete)
        if content and len(content.strip()) < 50:
            penalty -= 30
            
        # 2. Check for promotional/spam patterns (enhanced)
        promo_patterns = [
            'register now', 'sign up today', 'click here', 'limited time',
            'act now', 'don\'t miss', 'exclusive offer', 'free trial',
            'download whitepaper', 'request demo', 'learn more at',
            'brought to you by', 'sponsored by', 'in partnership with',
            # Additional spam patterns
            'buy now', 'order today', 'special price', 'save money',
            'get started', 'try free', 'no obligation', 'risk free',
            'money back guarantee', 'limited offer', 'hurry up',
            'while supplies last', 'call now', 'visit our website',
            'follow us on', 'like and subscribe', 'share this',
            # Business/PR spam
            'thought leader', 'industry leader', 'market leader',
            'award winning', 'leading provider', 'trusted partner',
            'solutions provider', 'cutting edge', 'innovative solution',
            'next generation', 'revolutionary', 'game changing'
        ]
        promo_matches = sum(1 for pattern in promo_patterns if pattern in full_text)
        if promo_matches >= 4:
            penalty -= 80  # Increased penalty
        elif promo_matches >= 3:
            penalty -= 60
        elif promo_matches >= 2:
            penalty -= 35
            
        # 3. Check for press release patterns
        pr_patterns = [
            'press release', 'announces', 'partnership with', 'today announced',
            'is pleased to announce', 'proud to announce', 'launches new',
            'introduces', 'unveils', 'expands into', 'acquisition of'
        ]
        pr_matches = sum(1 for pattern in pr_patterns if pattern in full_text)
        if pr_matches >= 2:
            penalty -= 20
            
        # 4. Check for repetitive/template content
        if content:
            words = content.split()
            if len(words) > 0 and len(set(words)) / len(words) < 0.5:  # Low unique word ratio
                penalty -= 25
                
        # 5. Check for missing essential content
        if not content or len(content.strip()) == 0:
            penalty -= 40
            
        # 6. Check for excessive capitalization (spam indicator)
        if title:
            caps_ratio = sum(1 for c in title if c.isupper()) / len(title)
            if caps_ratio > 0.3:  # More than 30% caps
                penalty -= 15
                
        # 7. Check for webinar/event content (often promotional)
        webinar_patterns = ['webinar', 'join our panel', 'expert panel', 'virtual event']
        webinar_matches = sum(1 for pattern in webinar_patterns if pattern in full_text)
        if webinar_matches >= 2:
            penalty -= 30
            
        # 8. Check for affiliate/tracking links (usually promotional)
        tracking_patterns = ['utm_', '?ref=', 'affiliate', 'click.', 'goto.']
        if any(pattern in source.lower() for pattern in tracking_patterns):
            penalty -= 20
            
        # 9. ENHANCED: Aggressive advertisement detection
        ad_killer_patterns = [
            # Direct sales language
            'purchase', 'pricing', 'plans starting', 'subscription',
            'upgrade now', 'premium features', 'enterprise solution',
            # Marketing buzzwords
            'transform your business', 'boost productivity', 'increase revenue',
            'streamline operations', 'optimize performance', 'maximize roi',
            # Social media spam
            'follow for more', 'check out our', 'visit our blog',
            'download our app', 'join our community',
            # Event/webinar spam (stricter)
            'register today', 'seats are limited', 'join experts',
            'panel discussion', 'keynote speaker', 'virtual summit',
            # Product placement
            'powered by', 'made possible by', 'in collaboration with',
            'featuring', 'presenting sponsor', 'official partner'
        ]
        
        ad_matches = sum(1 for pattern in ad_killer_patterns if pattern in full_text)
        if ad_matches >= 3:
            penalty -= 100  # Severe penalty for heavy advertising
        elif ad_matches >= 2:
            penalty -= 50
        elif ad_matches >= 1:
            penalty -= 25
            
        # 10. Check for suspicious URL patterns (known ad/affiliate domains)
        suspicious_domains = [
            'bit.ly', 'tinyurl', 'ow.ly', 'buff.ly', 't.co',  # URL shorteners
            'mailchi.mp', 'constantcontact', 'campaignmonitor',  # Email marketing
            'eventbrite', 'meetup.com', 'zoom.us/webinar',  # Event platforms
            'pr.com', 'businesswire', 'prnewswire',  # Press release services
            'linkedin.com/pulse',  # LinkedIn promotional posts
        ]
        if any(domain in source.lower() for domain in suspicious_domains):
            penalty -= 40
            
        # 10.5. Source-based blacklist for known spam sources
        spam_sources = [
            'press release', 'sponsored content', 'advertisement',
            'promoted post', 'affiliate marketing', 'marketing solution',
            'business development', 'sales enablement', 'lead generation'
        ]
        source_lower = source.lower()
        if any(spam_term in source_lower for spam_term in spam_sources):
            penalty -= 60
            
        # 11. Title-based ad detection
        if title:
            title_lower = title.lower()
            # Titles that are clearly promotional
            if any(word in title_lower for word in ['how to', 'guide to', 'tips for', 'best practices']):
                if any(word in title_lower for word in ['your business', 'your team', 'your company']):
                    penalty -= 30  # "How to grow your business" type articles
                    
            # Titles with excessive punctuation (spam indicator)
            punct_count = sum(1 for c in title if c in '!?')
            if punct_count >= 2:
                penalty -= 20
            
        # 12. ML-based spam detection using downvote patterns
        try:
            # Check if this article type has been downvoted frequently
            from .store import Article, Event
            
            # Find similar articles that have been downvoted
            similar_downvoted = self.db.query(Article).join(Event).filter(
                Event.event_type == 'downvote',
                Article.source == source  # Same source
            ).count()
            
            total_from_source = self.db.query(Article).filter(
                Article.source == source
            ).count()
            
            if total_from_source > 10:  # Only apply if we have enough data
                downvote_rate = similar_downvoted / total_from_source
                if downvote_rate > 0.3:  # More than 30% downvoted
                    penalty -= int(100 * downvote_rate)  # Scale penalty by downvote rate
                    
        except Exception:
            pass  # Fail silently if ML analysis fails
            
        # 13. Check for very long URLs (often tracking/referral) 
        if len(source) > 150:
            penalty -= 10
            
        # 14. NUCLEAR option: Auto-hide heavily penalized content
        if penalty <= -150:  # If penalties are severe
            penalty = -999  # Ensure it never shows up
            
        return penalty