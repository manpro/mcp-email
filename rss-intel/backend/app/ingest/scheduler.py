"""Ingest scheduler for running adapters periodically"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from .base import AdapterFactory, NormalizedItem
from ..deps import SessionLocal
from ..store import ArticleStore
from ..scoring import ScoringEngine

# Import all adapters to register them
from . import jsonfeed_adapter, sitemap_adapter, api_adapter, email_adapter, activitypub_adapter

logger = logging.getLogger(__name__)


class IngestScheduler:
    """Manages scheduled ingestion from multiple sources"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
    
    async def run_single_source(self, source_id: int, db: Session) -> Dict[str, Any]:
        """
        Run ingestion for a single source
        
        Args:
            source_id: ID of source to ingest
            db: Database session
            
        Returns:
            Dict with ingestion results
        """
        # Get source configuration
        source = self._get_source(db, source_id)
        if not source:
            return {'error': f'Source {source_id} not found'}
        
        if not source['enabled']:
            return {'skipped': f'Source {source_id} disabled'}
        
        # Create ingest job record
        job_id = self._create_ingest_job(db, source_id)
        
        try:
            logger.info(f"Starting ingestion for source {source_id}: {source['name']}")
            
            # Create adapter
            adapter = AdapterFactory.create(source['type'], source['config'])
            
            # Fetch new items
            raw_items = await adapter.fetch_new()
            
            if not raw_items:
                logger.info(f"No new items from source {source_id}")
                self._finish_ingest_job(db, job_id, 0, None)
                return {'items_processed': 0, 'new_articles': 0}
            
            # Normalize items
            normalized_items = []
            for raw_item in raw_items:
                try:
                    normalized = adapter.normalize_item(raw_item)
                    normalized_items.append(normalized)
                except Exception as e:
                    logger.error(f"Error normalizing item from source {source_id}: {e}")
                    continue
            
            # Process and store articles
            result = self._process_normalized_items(db, normalized_items, source['name'])
            
            # Finish job
            self._finish_ingest_job(db, job_id, len(normalized_items), None)
            
            logger.info(f"Completed ingestion for source {source_id}: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Error in ingestion for source {source_id}: {e}"
            logger.error(error_msg)
            self._finish_ingest_job(db, job_id, 0, error_msg)
            return {'error': error_msg}
    
    async def run_all_sources(self) -> Dict[str, Any]:
        """Run ingestion for all enabled sources"""
        db = SessionLocal()
        
        try:
            # Get all enabled sources
            sources = self._get_enabled_sources(db)
            
            if not sources:
                logger.info("No enabled sources found")
                return {'sources_processed': 0, 'total_new_articles': 0}
            
            logger.info(f"Running ingestion for {len(sources)} sources")
            
            total_new_articles = 0
            results = {}
            
            # Process sources sequentially to avoid overwhelming targets
            for source in sources:
                source_id = source['id']
                
                try:
                    result = await self.run_single_source(source_id, db)
                    results[source_id] = result
                    
                    if 'new_articles' in result:
                        total_new_articles += result['new_articles']
                    
                    # Small delay between sources
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing source {source_id}: {e}")
                    results[source_id] = {'error': str(e)}
            
            summary = {
                'sources_processed': len(sources),
                'total_new_articles': total_new_articles,
                'source_results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Ingestion batch completed: {summary}")
            return summary
            
        finally:
            db.close()
    
    def _get_source(self, db: Session, source_id: int) -> Optional[Dict[str, Any]]:
        """Get source configuration by ID"""
        result = db.execute(text("""
            SELECT id, type, name, config, enabled 
            FROM sources 
            WHERE id = :source_id
        """), {'source_id': source_id})
        
        row = result.fetchone()
        if not row:
            return None
        
        return {
            'id': row.id,
            'type': row.type,
            'name': row.name,
            'config': row.config,
            'enabled': row.enabled
        }
    
    def _get_enabled_sources(self, db: Session) -> List[Dict[str, Any]]:
        """Get all enabled sources"""
        result = db.execute(text("""
            SELECT id, type, name, config, enabled 
            FROM sources 
            WHERE enabled = true
            ORDER BY id
        """))
        
        sources = []
        for row in result:
            sources.append({
                'id': row.id,
                'type': row.type,
                'name': row.name,
                'config': row.config,
                'enabled': row.enabled
            })
        
        return sources
    
    def _create_ingest_job(self, db: Session, source_id: int) -> int:
        """Create ingest job record"""
        result = db.execute(text("""
            INSERT INTO ingest_jobs (source_id, status, started_at)
            VALUES (:source_id, 'running', :started_at)
            RETURNING id
        """), {
            'source_id': source_id,
            'started_at': datetime.utcnow()
        })
        
        job_id = result.fetchone()[0]
        db.commit()
        return job_id
    
    def _finish_ingest_job(self, db: Session, job_id: int, items_found: int, error: Optional[str]):
        """Finish ingest job record"""
        status = 'failed' if error else 'completed'
        
        db.execute(text("""
            UPDATE ingest_jobs 
            SET status = :status, finished_at = :finished_at, items_found = :items_found, error = :error
            WHERE id = :job_id
        """), {
            'job_id': job_id,
            'status': status,
            'finished_at': datetime.utcnow(),
            'items_found': items_found,
            'error': error
        })
        db.commit()
    
    def _process_normalized_items(self, db: Session, items: List[NormalizedItem], source_name: str) -> Dict[str, Any]:
        """Process normalized items into articles"""
        store = ArticleStore(db)
        scorer = ScoringEngine()
        
        new_articles = 0
        updated_articles = 0
        
        for item in items:
            try:
                # Check for existing article by URL hash
                existing = store.get_article_by_url_hash(item.url_hash)
                
                # Calculate score
                score_total, scores, topics, entities = scorer.calculate_score(
                    title=item.title,
                    content=item.content,
                    source=item.source,
                    published_at=item.published_at
                )
                
                # Prepare article data
                article_data = {
                    'freshrss_entry_id': item.url_hash,  # Use URL hash as entry ID
                    'title': item.title,
                    'url': item.url,
                    'source': item.source,
                    'published_at': item.published_at,
                    'score_total': score_total,
                    'scores': scores,
                    'topics': topics,
                    'entities': {'matched': entities},
                    'flags': {},
                    'lang': item.lang,
                    'content': item.content,  # Store full content
                    'image_url': item.image_url,
                    'author': item.author
                }
                
                if existing:
                    # Update existing article
                    updated_articles += 1
                else:
                    # New article
                    new_articles += 1
                    
                    # Check for near-duplicates
                    near_dup = self._find_near_duplicate(db, item)
                    if near_dup:
                        article_data['near_dup_id'] = near_dup
                
                # Upsert article
                store.upsert_article(article_data)
                
            except Exception as e:
                logger.error(f"Error processing item '{item.title}': {e}")
                continue
        
        return {
            'items_processed': len(items),
            'new_articles': new_articles,
            'updated_articles': updated_articles,
            'source': source_name
        }
    
    def _find_near_duplicate(self, db: Session, item: NormalizedItem) -> Optional[int]:
        """Find near-duplicate articles using content hash"""
        # Simple approach: look for articles with same content hash
        result = db.execute(text("""
            SELECT id FROM articles 
            WHERE content ILIKE :content_prefix
            AND published_at > :min_date
            LIMIT 1
        """), {
            'content_prefix': item.content[:100] + '%',  # Simple prefix match
            'min_date': datetime.now(timezone.utc).replace(day=datetime.now().day - 30)  # Last 30 days
        })
        
        row = result.fetchone()
        return row.id if row else None


# Global instance
ingest_scheduler = IngestScheduler()