import pytest
from datetime import datetime, timedelta, timezone
from app.scoring import ScoringEngine

class TestScoringEngine:
    
    @pytest.fixture
    def scorer(self, tmp_path):
        """Create a scorer with test configuration"""
        import yaml
        
        # Create test config files
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        scoring_config = {
            "keywords": {
                "payment": 10,
                "visa": 15,
                "ai": 12,
                "security": 8
            },
            "source_weights": {
                "trusted.com": 10,
                "medium.com": 5,
                "unknown.com": 0
            },
            "recency": {
                "half_life_hours": 24
            },
            "thresholds": {
                "star": 80,
                "interesting": 60
            }
        }
        
        watchlist_config = {
            "entities": ["Stripe", "PayPal", "Klarna"],
            "weights": {"default": 15, "Stripe": 20},
            "labels": {"prefix": "watch:"}
        }
        
        with open(config_dir / "scoring.yml", 'w') as f:
            yaml.dump(scoring_config, f)
        
        with open(config_dir / "watchlist.yml", 'w') as f:
            yaml.dump(watchlist_config, f)
        
        with open(config_dir / "sources.yml", 'w') as f:
            yaml.dump({}, f)
        
        # Patch the config directory
        import app.scoring
        original_settings = app.scoring.settings
        app.scoring.settings.config_dir = str(config_dir)
        
        scorer = ScoringEngine()
        
        # Restore original settings
        app.scoring.settings = original_settings
        
        return scorer
    
    def test_keyword_scoring(self, scorer):
        """Test keyword matching and scoring"""
        title = "New Payment System with Visa Integration"
        content = "This payment solution uses AI for security"
        source = "techblog.com"
        published_at = datetime.now(timezone.utc)
        
        score, scores, topics, entities = scorer.calculate_score(
            title, content, source, published_at
        )
        
        # Should match: payment (10), visa (15), ai (12), security (8)
        assert scores["keywords"] >= 45
        assert "payment" in topics
        assert "visa" in topics
        assert "ai" in topics
        assert "security" in topics
    
    def test_entity_watchlist(self, scorer):
        """Test watchlist entity detection and scoring"""
        title = "Stripe Announces New Features"
        content = "Stripe and PayPal compete in the payment space"
        source = "news.com"
        published_at = datetime.now(timezone.utc)
        
        score, scores, topics, entities = scorer.calculate_score(
            title, content, source, published_at
        )
        
        # Should match: Stripe (20) and PayPal (15)
        assert scores["watchlist"] == 35
        assert "Stripe" in entities
        assert "PayPal" in entities
    
    def test_source_weight(self, scorer):
        """Test source-based scoring"""
        title = "Tech News"
        content = "Some content"
        
        # Test trusted source
        score1, scores1, _, _ = scorer.calculate_score(
            title, content, "trusted.com", datetime.now(timezone.utc)
        )
        assert scores1["source"] == 10
        
        # Test medium source
        score2, scores2, _, _ = scorer.calculate_score(
            title, content, "medium.com", datetime.now(timezone.utc)
        )
        assert scores2["source"] == 5
        
        # Test unknown source
        score3, scores3, _, _ = scorer.calculate_score(
            title, content, "random.org", datetime.now(timezone.utc)
        )
        assert scores3["source"] == 0
    
    def test_recency_decay(self, scorer):
        """Test time-based score decay"""
        title = "Payment News with Visa"
        content = "Important payment information"
        source = "trusted.com"
        
        # Fresh article (now)
        now = datetime.now(timezone.utc)
        score_fresh, scores_fresh, _, _ = scorer.calculate_score(
            title, content, source, now
        )
        
        # 24 hours old (half-life)
        day_old = now - timedelta(hours=24)
        score_day, scores_day, _, _ = scorer.calculate_score(
            title, content, source, day_old
        )
        
        # 48 hours old
        two_days = now - timedelta(hours=48)
        score_old, scores_old, _, _ = scorer.calculate_score(
            title, content, source, two_days
        )
        
        # Fresh should have highest score
        assert score_fresh > score_day > score_old
        
        # Day old should be approximately half of fresh (due to half-life)
        assert 0.4 < (score_day / score_fresh) < 0.6
    
    def test_threshold_labels(self, scorer):
        """Test label assignment based on score thresholds"""
        # High score article
        high_score = 85
        entities = ["Stripe"]
        labels_high = scorer.get_labels_for_score(high_score, entities)
        
        assert "hot" in labels_high
        assert "watch:stripe" in labels_high
        assert scorer.should_star(high_score) is True
        
        # Medium score article
        medium_score = 65
        labels_medium = scorer.get_labels_for_score(medium_score, [])
        
        assert "interesting" in labels_medium
        assert "hot" not in labels_medium
        assert scorer.should_star(medium_score) is False
        
        # Low score article
        low_score = 40
        labels_low = scorer.get_labels_for_score(low_score, [])
        
        assert len(labels_low) == 0
        assert scorer.should_star(low_score) is False
    
    def test_complex_scoring(self, scorer):
        """Test complete scoring with all factors"""
        title = "Visa Partners with Stripe for AI-Powered Payment Security"
        content = "PayPal also interested in this payment innovation"
        source = "trusted.com"
        published_at = datetime.now(timezone.utc) - timedelta(hours=12)
        
        score, scores, topics, entities = scorer.calculate_score(
            title, content, source, published_at
        )
        
        # Verify all components are present
        assert "keywords" in scores
        assert "watchlist" in scores
        assert "source" in scores
        assert "recency_factor" in scores
        assert "base_score" in scores
        
        # Should have high score due to multiple matches
        assert score > 60
        
        # Check detected elements
        assert len(topics) > 0
        assert len(entities) > 0
        assert "Stripe" in entities
        
        # Should qualify for star
        labels = scorer.get_labels_for_score(score, entities)
        assert len(labels) > 0
    
    def test_duplicate_keywords(self, scorer):
        """Test diminishing returns for repeated keywords"""
        title = "Payment payment payment payment"
        content = "Payment systems for payment processing"
        source = "blog.com"
        published_at = datetime.now(timezone.utc)
        
        score, scores, topics, entities = scorer.calculate_score(
            title, content, source, published_at
        )
        
        # Should use logarithmic scaling for multiple matches
        # Not linear multiplication
        assert scores["keywords"] < 60  # Would be 60+ if linear