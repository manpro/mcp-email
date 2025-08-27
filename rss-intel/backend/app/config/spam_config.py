"""
Spam Detection Configuration Management
Handles configurable parameters for spam detection and quality thresholds
"""

import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

class SpamDetectionThresholds(BaseModel):
    """Spam detection threshold configuration"""
    spam_probability: float = 0.7  # Above this = spam
    review_probability: float = 0.5  # Above this = needs review
    min_content_score: float = 0.3  # Below this = low quality
    min_title_coherence: float = 0.3  # Below this = title mismatch
    max_promotional_ratio: float = 0.3  # Above this = too promotional
    min_word_count: int = 50  # Below this = thin content
    min_sentence_count: int = 3  # Below this = incomplete

class SpamSignalWeights(BaseModel):
    """Weights for different spam signals"""
    promotional_content: float = 0.8
    future_events_spam: float = 0.7
    thin_content: float = 0.6
    title_mismatch: float = 0.9
    clickbait: float = 0.5

class QualityPenalties(BaseModel):
    """Penalties for quality scoring system"""
    max_spam_penalty: int = 500  # Maximum penalty for spam
    promotional_penalty: int = 40  # Per promotional signal
    event_spam_penalty: int = 30  # Per event spam signal
    thin_content_penalty: int = 50  # Per thin content signal
    title_mismatch_penalty: int = 60  # Per title mismatch signal
    clickbait_penalty: int = 25  # Per clickbait signal

class SpamPatternConfig(BaseModel):
    """Configuration for spam pattern detection"""
    promotional_patterns: List[str] = [
        r'\b(?:buy now|order now|purchase|sale|discount|offer|deal|limited time|act now)\b',
        r'\b(?:free|save \$|[0-9]+% off|coupon|promo code|special offer)\b',
        r'\b(?:click here|visit our|learn more|sign up|register now|join now)\b',
        r'\b(?:sponsored|advertisement|paid content|partner content)\b'
    ]
    
    future_event_patterns: List[str] = [
        r'\b(?:upcoming|coming soon|next week|next month|next year|in [0-9]+ days)\b',
        r'\b(?:will be|is going to be|scheduled for|planned for|set to)\b',
        r'\b(?:save the date|mark your calendar|don\'t miss|early bird|registration open)\b',
        r'\b(?:webinar|conference|summit|event|workshop|seminar|masterclass)\b.*(?:register|sign up|tickets|book now)'
    ]
    
    thin_content_patterns: List[str] = [
        r'\b(?:lorem ipsum|placeholder|sample text|test content)\b',
        r'^\s*\[.*?\]\s*$',  # Just placeholder brackets
        r'\b(?:more information|read more|click here|see more|learn more)\b.*$'
    ]
    
    clickbait_patterns: List[str] = [
        r'\b(?:you won\'t believe|shocking|amazing|incredible|unbelievable)\b',
        r'\b(?:[0-9]+ reasons|[0-9]+ ways|[0-9]+ tips|[0-9]+ secrets)\b',
        r'\b(?:hate|love|secret|trick|hack|revealed|exposed)\b',
        r'[\!\?]{2,}'  # Multiple exclamation/question marks
    ]

class SpamConfig(BaseModel):
    """Complete spam detection configuration"""
    thresholds: SpamDetectionThresholds = SpamDetectionThresholds()
    signal_weights: SpamSignalWeights = SpamSignalWeights()
    quality_penalties: QualityPenalties = QualityPenalties()
    patterns: SpamPatternConfig = SpamPatternConfig()
    
    # System settings
    batch_size: int = 50  # Articles to process in one batch
    cache_ttl: int = 3600  # Cache results for 1 hour
    enabled: bool = True  # Global enable/disable
    auto_penalize: bool = True  # Automatically apply score penalties
    
    # Scheduler settings
    cleanup_interval_hours: int = 6  # Run spam cleanup every 6 hours
    stats_update_hour: int = 1  # Update daily stats at 1 AM
    
    # Monitoring thresholds
    alert_spam_rate: float = 0.3  # Alert if spam rate above 30%
    alert_low_quality_rate: float = 0.5  # Alert if low quality rate above 50%

class SpamConfigManager:
    """Manager for spam detection configuration"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/spam_detection.yml"
        self.config_path = Path(self.config_file)
        self._config: Optional[SpamConfig] = None
        self._last_loaded: Optional[datetime] = None
        
    def load_config(self) -> SpamConfig:
        """Load configuration from file or create default"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    
                # Handle nested structure
                config = SpamConfig(**config_data)
                self._config = config
                self._last_loaded = datetime.now()
                logger.info(f"Loaded spam detection config from {self.config_path}")
                return config
            else:
                # Create default config
                logger.info(f"Config file {self.config_path} not found, using defaults")
                return self._create_default_config()
                
        except Exception as e:
            logger.error(f"Error loading spam config from {self.config_path}: {e}")
            logger.info("Using default spam detection configuration")
            return self._create_default_config()
    
    def _create_default_config(self) -> SpamConfig:
        """Create and save default configuration"""
        config = SpamConfig()
        self.save_config(config)
        return config
    
    def save_config(self, config: SpamConfig) -> bool:
        """Save configuration to file"""
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict for YAML serialization
            config_dict = config.dict()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    config_dict, 
                    f, 
                    default_flow_style=False, 
                    allow_unicode=True,
                    sort_keys=False
                )
            
            self._config = config
            self._last_loaded = datetime.now()
            logger.info(f"Saved spam detection config to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving spam config to {self.config_path}: {e}")
            return False
    
    def get_config(self, refresh: bool = False) -> SpamConfig:
        """Get current configuration, optionally refreshing from file"""
        if refresh or self._config is None:
            return self.load_config()
        
        # Auto-refresh if file is newer
        if self.config_path.exists() and self._last_loaded:
            file_mtime = datetime.fromtimestamp(self.config_path.stat().st_mtime)
            if file_mtime > self._last_loaded:
                logger.info("Config file updated, reloading...")
                return self.load_config()
        
        return self._config
    
    def update_thresholds(self, **kwargs) -> bool:
        """Update spam detection thresholds"""
        try:
            config = self.get_config()
            
            for key, value in kwargs.items():
                if hasattr(config.thresholds, key):
                    setattr(config.thresholds, key, value)
                    logger.info(f"Updated threshold {key} = {value}")
            
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Error updating thresholds: {e}")
            return False
    
    def update_signal_weights(self, **kwargs) -> bool:
        """Update spam signal weights"""
        try:
            config = self.get_config()
            
            for key, value in kwargs.items():
                if hasattr(config.signal_weights, key):
                    setattr(config.signal_weights, key, value)
                    logger.info(f"Updated signal weight {key} = {value}")
            
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Error updating signal weights: {e}")
            return False
    
    def add_custom_pattern(self, pattern_type: str, pattern: str) -> bool:
        """Add a custom spam detection pattern"""
        try:
            config = self.get_config()
            patterns = config.patterns
            
            if pattern_type == "promotional":
                patterns.promotional_patterns.append(pattern)
            elif pattern_type == "future_event":
                patterns.future_event_patterns.append(pattern)
            elif pattern_type == "thin_content":
                patterns.thin_content_patterns.append(pattern)
            elif pattern_type == "clickbait":
                patterns.clickbait_patterns.append(pattern)
            else:
                logger.error(f"Unknown pattern type: {pattern_type}")
                return False
            
            logger.info(f"Added custom {pattern_type} pattern: {pattern}")
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Error adding custom pattern: {e}")
            return False
    
    def get_effective_thresholds(self) -> Dict[str, float]:
        """Get current effective thresholds for external use"""
        config = self.get_config()
        return {
            'spam_probability': config.thresholds.spam_probability,
            'review_probability': config.thresholds.review_probability,
            'min_content_score': config.thresholds.min_content_score,
            'min_title_coherence': config.thresholds.min_title_coherence,
            'max_promotional_ratio': config.thresholds.max_promotional_ratio,
            'min_word_count': config.thresholds.min_word_count,
            'min_sentence_count': config.thresholds.min_sentence_count
        }
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return any issues"""
        issues = []
        try:
            config = self.get_config()
            
            # Check threshold ranges
            if not 0 <= config.thresholds.spam_probability <= 1:
                issues.append("spam_probability must be between 0 and 1")
            
            if not 0 <= config.thresholds.review_probability <= 1:
                issues.append("review_probability must be between 0 and 1")
            
            if config.thresholds.review_probability >= config.thresholds.spam_probability:
                issues.append("review_probability should be less than spam_probability")
            
            if config.thresholds.min_word_count < 0:
                issues.append("min_word_count must be positive")
            
            # Check signal weights
            for field_name, field_value in config.signal_weights.dict().items():
                if not 0 <= field_value <= 1:
                    issues.append(f"signal weight {field_name} must be between 0 and 1")
            
            # Check patterns (basic regex validation)
            import re
            for pattern_list_name, patterns in config.patterns.dict().items():
                for i, pattern in enumerate(patterns):
                    try:
                        re.compile(pattern, re.IGNORECASE)
                    except re.error as e:
                        issues.append(f"Invalid regex in {pattern_list_name}[{i}]: {e}")
            
            logger.info(f"Config validation completed: {len(issues)} issues found")
            
        except Exception as e:
            issues.append(f"Config validation error: {e}")
        
        return issues

# Global instance
spam_config_manager = SpamConfigManager()

# Convenience function for getting current config
def get_spam_config() -> SpamConfig:
    """Get current spam detection configuration"""
    return spam_config_manager.get_config()