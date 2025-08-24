import re
import math
import yaml
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path
from .config import settings

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
                       has_image: bool = False) -> Tuple[int, Dict[str, Any], List[str], List[str]]:
        """
        Calculate article score based on multiple signals
        Returns: (total_score, score_breakdown, topics, matched_entities)
        """
        scores = {}
        topics = []
        matched_entities = []
        
        # Combine title and content for analysis
        full_text = f"{title} {content}".lower()
        
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
        
        # Clamp age_hours to reasonable bounds to prevent overflow
        # Articles from future get age_hours = 0, articles older than 30 days get heavily penalized
        age_hours = max(0, min(age_hours, 30 * 24))  # Clamp between 0 and 30 days
        
        half_life = self.scoring_config.get("recency", {}).get("half_life_hours", 36)
        recency_factor = math.exp(-age_hours / half_life)
        
        # Apply recency as a multiplier to the base score
        base_score = sum(scores.values())
        total_score = round(base_score * recency_factor)
        
        # Prevent database integer overflow (PostgreSQL integer max is ~2.1 billion)
        total_score = min(total_score, 2_000_000_000)
        
        scores["recency_factor"] = round(recency_factor * 100) / 100
        scores["base_score"] = base_score
        
        return total_score, scores, list(set(topics)), matched_entities
    
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