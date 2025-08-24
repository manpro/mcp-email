"""Upsert article chunks to Weaviate with embeddings"""
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from .weaviate_client import weaviate_manager
from .embedder import get_batch_embedder
from .chunker import chunk_articles_batch

logger = logging.getLogger(__name__)


def upsert_chunks_for_articles(
    db: Session, 
    article_ids: Optional[List[int]] = None,
    limit: int = 50,
    overwrite_existing: bool = False
) -> Dict[str, Any]:
    """
    Process articles into chunks, embed them, and upsert to Weaviate
    
    Args:
        db: Database session
        article_ids: Specific article IDs to process (None for unprocessed)
        limit: Maximum number of articles to process
        overwrite_existing: Whether to reprocess articles that already have chunks
        
    Returns:
        Dict with processing statistics
    """
    logger.info(f"Starting chunk upsert process (limit={limit}, overwrite={overwrite_existing})")
    
    try:
        # Get articles to process
        articles = _get_articles_for_chunking(
            db, article_ids, limit, overwrite_existing
        )
        
        if not articles:
            logger.info("No articles to process")
            return {
                'articles_processed': 0,
                'chunks_created': 0,
                'chunks_upserted': 0,
                'errors': []
            }
        
        logger.info(f"Processing {len(articles)} articles")
        
        # Create chunks
        chunks = chunk_articles_batch(articles)
        
        if not chunks:
            logger.warning("No chunks created")
            return {
                'articles_processed': len(articles),
                'chunks_created': 0,
                'chunks_upserted': 0,
                'errors': ['No chunks created from articles']
            }
        
        # Add embeddings
        embedder = get_batch_embedder()
        chunks_with_embeddings = embedder.embed_chunks(chunks)
        
        # Store chunks in PostgreSQL
        _store_chunks_in_db(db, chunks_with_embeddings)
        
        # Upsert to Weaviate
        weaviate_result = weaviate_manager.upsert_chunks(chunks_with_embeddings)
        
        # Update articles table to mark as processed
        _mark_articles_as_chunked(db, article_ids or [a['id'] for a in articles])
        
        result = {
            'articles_processed': len(articles),
            'chunks_created': len(chunks),
            'chunks_upserted': weaviate_result['inserted'],
            'embedding_model': embedder.model_info,
            'errors': weaviate_result['errors']
        }
        
        logger.info(f"Chunk upsert completed: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Error in chunk upsert process: {e}"
        logger.error(error_msg)
        return {
            'articles_processed': 0,
            'chunks_created': 0,
            'chunks_upserted': 0,
            'errors': [error_msg]
        }


def _get_articles_for_chunking(
    db: Session,
    article_ids: Optional[List[int]],
    limit: int,
    overwrite_existing: bool
) -> List[Dict[str, Any]]:
    """Get articles that need to be chunked"""
    
    if article_ids:
        # Process specific articles
        query = """
            SELECT id, title, url, source, published_at, score_total, lang, near_dup_id,
                   COALESCE(full_content, content, '') as content
            FROM articles 
            WHERE id = ANY(:article_ids)
            ORDER BY score_total DESC, published_at DESC
        """
        result = db.execute(text(query), {'article_ids': article_ids})
        
    elif overwrite_existing:
        # Process all articles (reprocessing)
        query = """
            SELECT id, title, url, source, published_at, score_total, lang, near_dup_id,
                   COALESCE(full_content, content, '') as content
            FROM articles 
            WHERE score_total >= 20
            ORDER BY score_total DESC, published_at DESC
            LIMIT :limit
        """
        result = db.execute(text(query), {'limit': limit})
        
    else:
        # Process only articles without chunks
        query = """
            SELECT a.id, a.title, a.url, a.source, a.published_at, a.score_total, a.lang, a.near_dup_id,
                   COALESCE(a.full_content, a.content, '') as content
            FROM articles a
            LEFT JOIN article_chunks ac ON a.id = ac.article_id
            WHERE ac.article_id IS NULL
            AND a.score_total >= 20
            ORDER BY a.score_total DESC, a.published_at DESC
            LIMIT :limit
        """
        result = db.execute(text(query), {'limit': limit})
    
    # Convert to list of dicts
    articles = []
    for row in result:
        articles.append({
            'id': row.id,
            'title': row.title or '',
            'url': row.url or '',
            'source': row.source or '',
            'published_at': row.published_at,
            'score_total': row.score_total or 0,
            'lang': row.lang,
            'near_dup_id': row.near_dup_id,
            'content': row.content or ''
        })
    
    return articles


def _store_chunks_in_db(db: Session, chunks: List[Dict[str, Any]]):
    """Store chunks in PostgreSQL article_chunks table"""
    try:
        for chunk in chunks:
            # Check if chunk already exists
            existing = db.execute(text("""
                SELECT id FROM article_chunks 
                WHERE article_id = :article_id AND chunk_ix = :chunk_ix
            """), {
                'article_id': chunk['article_id'],
                'chunk_ix': chunk['chunk_ix']
            }).fetchone()
            
            if existing:
                # Update existing chunk
                db.execute(text("""
                    UPDATE article_chunks 
                    SET text = :text, token_count = :token_count
                    WHERE article_id = :article_id AND chunk_ix = :chunk_ix
                """), {
                    'text': chunk['text'],
                    'token_count': chunk['token_count'],
                    'article_id': chunk['article_id'],
                    'chunk_ix': chunk['chunk_ix']
                })
            else:
                # Insert new chunk
                db.execute(text("""
                    INSERT INTO article_chunks (article_id, chunk_ix, text, token_count)
                    VALUES (:article_id, :chunk_ix, :text, :token_count)
                """), {
                    'article_id': chunk['article_id'],
                    'chunk_ix': chunk['chunk_ix'],
                    'text': chunk['text'],
                    'token_count': chunk['token_count']
                })
        
        db.commit()
        logger.info(f"Stored {len(chunks)} chunks in PostgreSQL")
        
    except Exception as e:
        logger.error(f"Error storing chunks in database: {e}")
        db.rollback()
        raise


def _mark_articles_as_chunked(db: Session, article_ids: List[int]):
    """Mark articles as having been processed for chunking"""
    try:
        # Could add a 'chunked_at' timestamp to articles table if needed
        # For now, we can query article_chunks to see which articles are processed
        pass
        
    except Exception as e:
        logger.error(f"Error marking articles as chunked: {e}")


def refresh_chunks_for_article(db: Session, article_id: int) -> Dict[str, Any]:
    """
    Refresh chunks for a specific article (delete and recreate)
    """
    logger.info(f"Refreshing chunks for article {article_id}")
    
    try:
        # Delete existing chunks from Weaviate
        weaviate_manager.delete_chunks_for_article(article_id)
        
        # Delete existing chunks from PostgreSQL
        db.execute(text("DELETE FROM article_chunks WHERE article_id = :article_id"), 
                  {'article_id': article_id})
        db.commit()
        
        # Recreate chunks
        result = upsert_chunks_for_articles(
            db, article_ids=[article_id], limit=1, overwrite_existing=True
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Error refreshing chunks for article {article_id}: {e}"
        logger.error(error_msg)
        return {'errors': [error_msg]}


def get_chunking_stats(db: Session) -> Dict[str, Any]:
    """Get statistics about article chunking progress"""
    try:
        # Count total articles
        total_articles = db.execute(text("SELECT COUNT(*) FROM articles WHERE score_total >= 20")).scalar()
        
        # Count articles with chunks
        chunked_articles = db.execute(text("""
            SELECT COUNT(DISTINCT article_id) FROM article_chunks
        """)).scalar()
        
        # Count total chunks
        total_chunks = db.execute(text("SELECT COUNT(*) FROM article_chunks")).scalar()
        
        # Get Weaviate stats
        weaviate_stats = weaviate_manager.get_collection_stats()
        
        return {
            'total_articles': total_articles,
            'chunked_articles': chunked_articles,
            'unchunked_articles': total_articles - chunked_articles,
            'total_chunks_db': total_chunks,
            'total_chunks_weaviate': weaviate_stats.get('total_chunks', 0),
            'weaviate_collection': weaviate_stats.get('collection_name', 'N/A')
        }
        
    except Exception as e:
        logger.error(f"Error getting chunking stats: {e}")
        return {'error': str(e)}