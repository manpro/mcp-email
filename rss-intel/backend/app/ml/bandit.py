"""Bandit algorithms and MMR diversification"""
import logging
import random
from typing import List, Dict, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text

from .embedding import compute_similarity, get_article_embedding
from .uservec import get_user_embedding

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_EPSILON = 0.1
DEFAULT_MMR_LAMBDA = 0.25

class BanditRecommender:
    """ε-greedy bandit with MMR diversification"""
    
    def __init__(self, db: Session, epsilon: float = DEFAULT_EPSILON, mmr_lambda: float = DEFAULT_MMR_LAMBDA):
        self.db = db
        self.epsilon = epsilon
        self.mmr_lambda = mmr_lambda
        self._load_config()
    
    def _load_config(self):
        """Load A/B test configuration from database"""
        try:
            result = self.db.execute(text("""
                SELECT key, value FROM ab_config 
                WHERE key IN ('epsilon', 'mmr_lambda', 'enabled')
            """))
            
            config = {row.key: row.value for row in result.fetchall()}
            
            if 'epsilon' in config:
                self.epsilon = float(config['epsilon'])
            if 'mmr_lambda' in config:
                self.mmr_lambda = float(config['mmr_lambda'])
            
            self.enabled = config.get('enabled', 'true').lower() == 'true'
            
        except Exception as e:
            logger.warning(f"Could not load bandit config: {e}")
            self.enabled = True
    
    def apply_bandit(
        self,
        scored_articles: List[Dict],
        user_id: str = "owner",
        exploration_pool_size: int = 20
    ) -> List[Dict]:
        """
        Apply ε-greedy bandit algorithm
        
        Args:
            scored_articles: List of articles with p_read scores
            user_id: User identifier
            exploration_pool_size: Size of exploration pool for ε-greedy
            
        Returns:
            List of articles with bandit-adjusted ordering
        """
        if not self.enabled or not scored_articles:
            return scored_articles
        
        logger.info(f"Applying ε-greedy bandit (ε={self.epsilon}) to {len(scored_articles)} articles")
        
        # Sort by p_read (exploitation order)
        articles_sorted = sorted(scored_articles, key=lambda x: x['p_read'], reverse=True)
        
        final_ranking = []
        used_articles = set()
        
        for i in range(len(articles_sorted)):
            if articles_sorted[i]['article_id'] in used_articles:
                continue
                
            # ε-greedy decision
            if random.random() < self.epsilon and i < len(articles_sorted) - exploration_pool_size:
                # Exploration: pick from high rule-score but potentially low p_read
                exploration_candidate = self._select_exploration_candidate(
                    articles_sorted[i:i+exploration_pool_size], used_articles
                )
                if exploration_candidate:
                    final_ranking.append(exploration_candidate)
                    used_articles.add(exploration_candidate['article_id'])
                    continue
            
            # Exploitation: pick highest p_read
            if articles_sorted[i]['article_id'] not in used_articles:
                final_ranking.append(articles_sorted[i])
                used_articles.add(articles_sorted[i]['article_id'])
        
        exploration_count = sum(1 for a in final_ranking if a.get('exploration', False))
        logger.info(f"Bandit applied: {exploration_count}/{len(final_ranking)} exploration picks")
        
        return final_ranking
    
    def _select_exploration_candidate(
        self,
        candidates: List[Dict],
        used_articles: set
    ) -> Optional[Dict]:
        """Select exploration candidate based on rule score and uncertainty"""
        available = [c for c in candidates if c['article_id'] not in used_articles]
        if not available:
            return None
        
        # Prefer high rule score (potential high-quality but unmodeled articles)
        exploration_candidate = max(available, key=lambda x: x.get('rule_score', 0))
        exploration_candidate['exploration'] = True
        
        return exploration_candidate
    
    def apply_mmr_diversification(
        self,
        articles: List[Dict],
        user_id: str = "owner",
        final_count: int = 50
    ) -> List[Dict]:
        """
        Apply Maximal Marginal Relevance (MMR) diversification
        
        Balances relevance (p_read) with diversity (distance from user vector and selected items)
        """
        if not self.enabled or len(articles) <= final_count:
            return articles[:final_count]
        
        logger.info(f"Applying MMR diversification (λ={self.mmr_lambda})")
        
        # Get user embedding
        user_embedding = get_user_embedding(self.db, user_id, lookback_days=30)
        if user_embedding is None:
            logger.warning("No user embedding available, skipping MMR")
            return articles[:final_count]
        
        # Get article embeddings
        article_embeddings = {}
        for article in articles:
            emb = get_article_embedding(self.db, article['article_id'])
            if emb is not None:
                article_embeddings[article['article_id']] = emb
        
        if not article_embeddings:
            logger.warning("No article embeddings available, skipping MMR")
            return articles[:final_count]
        
        # MMR algorithm
        selected = []
        remaining = [a for a in articles if a['article_id'] in article_embeddings]
        
        for _ in range(min(final_count, len(remaining))):
            if not remaining:
                break
            
            best_score = -float('inf')
            best_article = None
            best_idx = None
            
            for idx, article in enumerate(remaining):
                article_id = article['article_id']
                article_emb = article_embeddings[article_id]
                
                # Relevance: p_read score
                relevance = article['p_read']
                
                # Diversity: distance from user preference and selected items
                diversity_score = self._compute_diversity(
                    article_emb, user_embedding, selected, article_embeddings
                )
                
                # MMR score: λ * relevance + (1-λ) * diversity
                mmr_score = self.mmr_lambda * relevance + (1 - self.mmr_lambda) * diversity_score
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_article = article
                    best_idx = idx
            
            if best_article:
                selected.append(best_article)
                remaining.pop(best_idx)
        
        # Add remaining articles if needed
        selected.extend(remaining[:final_count - len(selected)])
        
        logger.info(f"MMR diversification applied: selected {len(selected)} articles")
        return selected[:final_count]
    
    def _compute_diversity(
        self,
        article_emb: np.ndarray,
        user_emb: np.ndarray,
        selected_articles: List[Dict],
        article_embeddings: Dict[int, np.ndarray]
    ) -> float:
        """Compute diversity score for an article"""
        if not selected_articles:
            # First article: just use distance from user preference
            user_similarity = compute_similarity(article_emb, user_emb)
            return 1.0 - user_similarity  # Distance = 1 - similarity
        
        # Distance from selected articles
        min_distance_to_selected = float('inf')
        
        for selected in selected_articles:
            selected_emb = article_embeddings.get(selected['article_id'])
            if selected_emb is not None:
                similarity = compute_similarity(article_emb, selected_emb)
                distance = 1.0 - similarity
                min_distance_to_selected = min(min_distance_to_selected, distance)
        
        return min_distance_to_selected

def get_ab_config(db: Session) -> Dict:
    """Get A/B test configuration"""
    result = db.execute(text("SELECT key, value FROM ab_config"))
    return {row.key: row.value for row in result.fetchall()}

def set_ab_config(db: Session, key: str, value) -> bool:
    """Set A/B test configuration"""
    try:
        db.execute(text("""
            INSERT INTO ab_config (key, value) 
            VALUES (:key, :value)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """), {"key": key, "value": value})
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error setting A/B config {key}={value}: {e}")
        db.rollback()
        return False

def set_on():
    """CLI helper to enable A/B testing"""
    from ..deps import SessionLocal
    db = SessionLocal()
    try:
        set_ab_config(db, 'enabled', 'true')
        print("A/B testing enabled")
    finally:
        db.close()

def set_off():
    """CLI helper to disable A/B testing"""
    from ..deps import SessionLocal
    db = SessionLocal()
    try:
        set_ab_config(db, 'enabled', 'false')
        print("A/B testing disabled")
    finally:
        db.close()