"""
Personalization service for integrating ML recommendations with search and Ask AI
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .ml.advanced_ranker import AdvancedArticleRanker
from .ml.bandit import BanditRecommender
from .ab_testing import ABTestingFramework

logger = logging.getLogger(__name__)

class PersonalizationService:
    """Service for adding personalization to search and Q&A results"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ranker = AdvancedArticleRanker(db)
        self.bandit = BanditRecommender(db)
        self.ab_framework = ABTestingFramework(db)
    
    def personalize_search_results(
        self,
        search_results: List[Dict[str, Any]],
        user_id: str = "owner",
        boost_factor: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Add personalization scores to search results and re-rank them
        
        Args:
            search_results: Original search results with relevance scores
            user_id: User identifier
            boost_factor: How much to boost personalized scores (0.0-1.0)
            
        Returns:
            Re-ranked search results with personalization scores
        """
        if not search_results:
            return search_results
        
        try:
            # Get A/B testing parameters for this user
            ab_params = self._get_ab_testing_params(user_id)
            if ab_params:
                boost_factor = ab_params.get('boost_factor', boost_factor)
                logger.debug(f"Using A/B testing boost_factor: {boost_factor} for user {user_id}")
            
            # Extract article IDs from search results
            article_ids = [result['article_id'] for result in search_results]
            
            # Get ML personalization scores
            scored_articles = self.ranker.score_articles(article_ids, user_id)
            
            # Create lookup dictionary
            p_read_lookup = {
                item['article_id']: item['p_read'] 
                for item in scored_articles
            }
            
            # Add personalization scores to search results
            for result in search_results:
                article_id = result['article_id']
                p_read = p_read_lookup.get(article_id, 0.5)  # Default neutral score
                
                # Calculate combined score: search relevance + personalization
                original_score = result.get('relevance_score', 0.5)
                combined_score = (1 - boost_factor) * original_score + boost_factor * p_read
                
                # Add personalization metadata
                result['p_read'] = round(p_read, 3)
                result['personalized_score'] = round(combined_score, 3)
                result['personalization_boost'] = boost_factor
                
                # Update why_chips for personalized results
                if 'why_chips' not in result:
                    result['why_chips'] = []
                
                if p_read > 0.8:
                    result['why_chips'].insert(0, 'personalized_high')
                elif p_read > 0.6:
                    result['why_chips'].insert(0, 'personalized_match')
            
            # Re-rank by combined score
            search_results.sort(key=lambda x: x.get('personalized_score', 0), reverse=True)
            
            logger.info(f"Personalized {len(search_results)} search results for user {user_id}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error personalizing search results: {e}")
            # Return original results on error
            return search_results
    
    def get_personalized_context_for_qa(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        user_id: str = "owner",
        max_chunks: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Re-rank retrieved chunks for Q&A based on personalization
        
        Args:
            question: User's question
            retrieved_chunks: Chunks from semantic search
            user_id: User identifier
            max_chunks: Maximum chunks to return
            
        Returns:
            Personalized and re-ranked chunks
        """
        if not retrieved_chunks:
            return retrieved_chunks
        
        try:
            # Extract unique article IDs
            article_ids = list(set(chunk['article_id'] for chunk in retrieved_chunks))
            
            # Get personalization scores
            scored_articles = self.ranker.score_articles(article_ids, user_id)
            
            # Create lookup
            p_read_lookup = {
                item['article_id']: item['p_read']
                for item in scored_articles
            }
            
            # Add personalization scores to chunks
            for chunk in retrieved_chunks:
                article_id = chunk['article_id']
                p_read = p_read_lookup.get(article_id, 0.5)
                
                # Combine search relevance with personalization
                search_score = chunk.get('search_score', 0.5)
                combined_score = 0.7 * search_score + 0.3 * p_read  # Favor search relevance more for Q&A
                
                chunk['p_read'] = p_read
                chunk['combined_qa_score'] = combined_score
            
            # Re-rank chunks by combined score
            retrieved_chunks.sort(key=lambda x: x.get('combined_qa_score', 0), reverse=True)
            
            # Return top chunks
            result = retrieved_chunks[:max_chunks]
            
            logger.info(f"Personalized {len(result)} Q&A context chunks for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error personalizing Q&A context: {e}")
            return retrieved_chunks[:max_chunks]
    
    def get_user_interests_summary(self, user_id: str = "owner") -> Dict[str, Any]:
        """Get a summary of user interests for debugging"""
        try:
            # Get recent user interactions
            from sqlalchemy import text
            from datetime import datetime, timedelta, timezone
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            
            result = self.db.execute(text("""
                SELECT 
                    a.source,
                    COUNT(*) as interactions,
                    COUNT(CASE WHEN e.type = 'star' THEN 1 END) as stars,
                    COUNT(CASE WHEN e.type = 'external_click' THEN 1 END) as clicks,
                    AVG(a.score_total) as avg_score
                FROM events e
                JOIN articles a ON e.article_id = a.id
                WHERE e.user_id = :user_id 
                AND e.created_at > :cutoff
                AND e.type IN ('star', 'external_click', 'open')
                GROUP BY a.source
                ORDER BY interactions DESC
                LIMIT 10
            """), {"user_id": user_id, "cutoff": cutoff})
            
            interests = []
            for row in result:
                interests.append({
                    'source': row.source,
                    'interactions': row.interactions,
                    'stars': row.stars or 0,
                    'clicks': row.clicks or 0,
                    'avg_score': round(float(row.avg_score or 0), 1)
                })
            
            return {
                'user_id': user_id,
                'top_sources': interests,
                'ml_model_available': self.ranker.model is not None,
                'total_interactions': sum(i['interactions'] for i in interests)
            }
            
        except Exception as e:
            logger.error(f"Error getting user interests: {e}")
            return {'user_id': user_id, 'error': str(e)}
    
    def _get_ab_testing_params(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get A/B testing parameters for a user"""
        try:
            active_experiments = self.ab_framework.get_active_experiments()
            user_params = {}
            
            for experiment in active_experiments:
                assignment = self.ab_framework.get_user_assignment(experiment['id'], user_id)
                if assignment and 'params' in assignment:
                    # Merge experiment parameters
                    user_params.update(assignment['params'])
            
            return user_params if user_params else None
            
        except Exception as e:
            logger.error(f"Error getting A/B testing params for {user_id}: {e}")
            return None
    
    def record_ab_metric(self, user_id: str, metric_name: str, metric_value: float):
        """Record metrics for active A/B tests"""
        try:
            active_experiments = self.ab_framework.get_active_experiments()
            
            for experiment in active_experiments:
                # Check if user is in this experiment
                assignment = self.ab_framework.get_user_assignment(experiment['id'], user_id)
                if assignment:
                    self.ab_framework.record_metric(
                        experiment['id'], user_id, metric_name, metric_value
                    )
                    
        except Exception as e:
            logger.error(f"Error recording A/B metrics: {e}")

# Global service instance
_personalization_service = None

def get_personalization_service(db: Session) -> PersonalizationService:
    """Get or create personalization service instance"""
    global _personalization_service
    if _personalization_service is None:
        _personalization_service = PersonalizationService(db)
    return _personalization_service