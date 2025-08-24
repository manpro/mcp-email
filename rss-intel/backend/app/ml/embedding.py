"""Text embedding module using sentence-transformers"""
import logging
import os
from typing import Optional, List
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..deps import SessionLocal

logger = logging.getLogger(__name__)

# Global model instance
_model = None

def ensure_model() -> SentenceTransformer:
    """Load all-MiniLM-L6-v2 model, CPU-optimized"""
    global _model
    if _model is None:
        logger.info("Loading sentence transformer model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
    return _model

def embed_text(title: str, summary: Optional[str] = None) -> np.ndarray:
    """
    Embed text to 384-dimensional vector
    
    Args:
        title: Article title
        summary: Optional article summary/content
        
    Returns:
        384-dimensional numpy array
    """
    model = ensure_model()
    
    # Combine title and summary
    text = title
    if summary:
        text = f"{title}. {summary[:500]}"  # Limit summary length
    
    # Encode to vector
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.astype(np.float32)

def batch_embed_articles(db: Session, limit: int = 100) -> int:
    """
    Batch embed articles that don't have embeddings yet
    
    Args:
        db: Database session
        limit: Maximum number of articles to process
        
    Returns:
        Number of articles embedded
    """
    logger.info(f"Starting batch embedding, limit={limit}")
    
    # Get articles without embeddings
    result = db.execute(text("""
        SELECT a.id, a.title, a.content, a.source, a.published_at,
               COALESCE(a.has_image, false) as has_image
        FROM articles a
        LEFT JOIN article_vectors av ON a.id = av.article_id
        WHERE av.article_id IS NULL
        ORDER BY a.created_at DESC
        LIMIT :limit
    """), {"limit": limit})
    
    articles = result.fetchall()
    if not articles:
        logger.info("No articles to embed")
        return 0
    
    logger.info(f"Found {len(articles)} articles to embed")
    
    embedded_count = 0
    model = ensure_model()
    
    for article in articles:
        try:
            # Create embedding
            embedding = embed_text(article.title, article.content)
            
            # Store in database
            db.execute(text("""
                INSERT INTO article_vectors (article_id, emb, title_len, has_image, source, published_at)
                VALUES (:article_id, :emb, :title_len, :has_image, :source, :published_at)
                ON CONFLICT (article_id) DO UPDATE SET
                    emb = EXCLUDED.emb,
                    title_len = EXCLUDED.title_len,
                    has_image = EXCLUDED.has_image,
                    source = EXCLUDED.source,
                    published_at = EXCLUDED.published_at
            """), {
                "article_id": article.id,
                "emb": embedding.tolist(),
                "title_len": len(article.title) if article.title else 0,
                "has_image": bool(article.has_image),
                "source": article.source,
                "published_at": article.published_at
            })
            
            embedded_count += 1
            
            if embedded_count % 10 == 0:
                db.commit()
                logger.info(f"Embedded {embedded_count}/{len(articles)} articles")
                
        except Exception as e:
            logger.error(f"Error embedding article {article.id}: {e}")
            continue
    
    db.commit()
    logger.info(f"Batch embedding completed: {embedded_count} articles")
    return embedded_count

def get_article_embedding(db: Session, article_id: int) -> Optional[np.ndarray]:
    """Get embedding for specific article"""
    result = db.execute(text("""
        SELECT emb FROM article_vectors WHERE article_id = :article_id
    """), {"article_id": article_id})
    
    row = result.fetchone()
    if row and row.emb:
        return np.array(row.emb, dtype=np.float32)
    return None

def compute_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings"""
    # Normalize vectors
    emb1_norm = emb1 / np.linalg.norm(emb1)
    emb2_norm = emb2 / np.linalg.norm(emb2)
    
    # Cosine similarity
    return float(np.dot(emb1_norm, emb2_norm))

if __name__ == "__main__":
    # CLI for batch embedding
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        db = SessionLocal()
        try:
            count = batch_embed_articles(db, limit)
            print(f"Embedded {count} articles")
        finally:
            db.close()