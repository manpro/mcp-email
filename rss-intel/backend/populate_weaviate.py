#!/usr/bin/env python3
"""
Populate Weaviate vector database with article chunks
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('populate_weaviate.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import app modules
import os
sys.path.insert(0, '/app')
from app.store import Article
from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.vec.weaviate_client import weaviate_manager

# Database setup
DATABASE_URL = settings.database_url
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ArticleChunker:
    """Split articles into chunks for vector search"""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.model = None
    
    def ensure_model(self) -> SentenceTransformer:
        """Load sentence transformer model"""
        if self.model is None:
            logger.info("Loading sentence-transformers model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully")
        return self.model
    
    def split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if not text or len(text) < self.chunk_size:
            return [text] if text else []
        
        chunks = []
        words = text.split()
        
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            
            if end == len(words):
                break
                
            start = end - self.overlap
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """Approximate token count"""
        return len(text.split())
    
    def chunk_article(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert article to chunks with embeddings"""
        
        # Prepare content for chunking
        content = article.get('full_content') or article.get('content') or ''
        title = article.get('title', '')
        
        if not content:
            logger.warning(f"Article {article['id']} has no content to chunk")
            return []
        
        # Split into chunks
        chunks = self.split_text(content)
        if not chunks:
            return []
        
        # Generate embeddings
        model = self.ensure_model()
        result_chunks = []
        
        for i, chunk_text in enumerate(chunks):
            try:
                # Create combined text for embedding (title + chunk)
                embed_text = f"{title}. {chunk_text}"
                
                # Generate embedding
                embedding = model.encode(embed_text, convert_to_numpy=True)
                
                # Prepare chunk data
                chunk_data = {
                    'article_id': article['id'],
                    'chunk_ix': i,
                    'text': chunk_text,
                    'vector': embedding.astype(np.float32).tolist(),
                    'title': title,
                    'url': article['url'],
                    'source': article['source'],
                    'lang': 'en',  # Default language
                    'published_at': article['published_at'],
                    'score': article.get('score_total', 0),
                    'near_dup_id': None,  # Not implemented yet
                    'token_count': self.count_tokens(chunk_text)
                }
                
                result_chunks.append(chunk_data)
                
            except Exception as e:
                logger.error(f"Error processing chunk {i} for article {article['id']}: {e}")
                continue
        
        logger.info(f"Article {article['id']} split into {len(result_chunks)} chunks")
        return result_chunks

async def get_articles_for_chunking(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get articles that need to be chunked"""
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT 
                a.id,
                a.title,
                a.url,
                a.content,
                a.full_content,
                a.source,
                a.published_at,
                a.score_total,
                a.has_image,
                a.content_type
            FROM articles a
            WHERE a.full_content IS NOT NULL 
                AND LENGTH(a.full_content) > 100
                AND a.content_type = 'article'  -- Only process articles, not events
            ORDER BY a.id ASC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        
        articles = []
        for row in result:
            articles.append({
                'id': row.id,
                'title': row.title,
                'url': row.url,
                'content': row.content,
                'full_content': row.full_content,
                'source': row.source,
                'published_at': row.published_at,
                'score_total': row.score_total,
                'has_image': row.has_image,
                'content_type': row.content_type
            })
        
        logger.info(f"Found {len(articles)} articles ready for chunking")
        return articles

async def populate_weaviate_chunks(batch_size: int = 50):
    """Main function to populate Weaviate with article chunks"""
    
    logger.info("Starting Weaviate population process...")
    
    # Initialize chunker
    chunker = ArticleChunker(chunk_size=400, overlap=50)
    
    # Check Weaviate connection
    try:
        stats = weaviate_manager.get_collection_stats()
        logger.info(f"Weaviate stats: {stats}")
    except Exception as e:
        logger.error(f"Weaviate connection error: {e}")
        return
    
    # Process articles in batches
    offset = 0
    total_processed = 0
    total_chunks = 0
    
    while True:
        # Get batch of articles
        articles = await get_articles_for_chunking(batch_size, offset)
        if not articles:
            break
        
        logger.info(f"Processing batch of {len(articles)} articles (offset: {offset})")
        
        # Process each article
        batch_chunks = []
        for article in articles:
            try:
                chunks = chunker.chunk_article(article)
                batch_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Error chunking article {article['id']}: {e}")
                continue
        
        # Upload chunks to Weaviate
        if batch_chunks:
            logger.info(f"Upserting {len(batch_chunks)} chunks to Weaviate...")
            
            try:
                result = weaviate_manager.upsert_chunks(batch_chunks)
                logger.info(f"Upsert result: {result}")
                
                total_chunks += result.get('inserted', 0)
                if result.get('errors'):
                    for error in result['errors'][:5]:  # Log first 5 errors
                        logger.error(f"Upsert error: {error}")
                
            except Exception as e:
                logger.error(f"Error upserting chunks: {e}")
        
        total_processed += len(articles)
        offset += batch_size
        
        # Progress update
        logger.info(f"Progress: {total_processed} articles processed, {total_chunks} chunks created")
        
        # Break if we processed fewer articles than requested (end of data)
        if len(articles) < batch_size:
            break
    
    # Final stats
    final_stats = weaviate_manager.get_collection_stats()
    logger.info(f"Population completed! Final stats: {final_stats}")
    logger.info(f"Total articles processed: {total_processed}")
    logger.info(f"Total chunks created: {total_chunks}")

async def main():
    """CLI entry point"""
    
    batch_size = 50
    if len(sys.argv) > 1:
        batch_size = int(sys.argv[1])
    
    logger.info(f"Starting Weaviate population with batch size: {batch_size}")
    
    try:
        await populate_weaviate_chunks(batch_size)
        logger.info("Weaviate population completed successfully!")
        
    except Exception as e:
        logger.error(f"Population failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))