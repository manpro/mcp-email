"""Embedding models and batch processing"""
import torch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import numpy as np
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Manages embedding model with fallback options"""
    
    def __init__(self):
        self.model = None
        self.model_name = None
        self.embedding_dim = None
        self._load_model()
    
    def _load_model(self):
        """Load embedding model with fallback options"""
        # Try models in order of preference
        model_options = [
            ('BAAI/bge-m3', 1024),           # Best multilingual model
            ('sentence-transformers/all-MiniLM-L6-v2', 384),  # Fallback
            ('all-MiniLM-L6-v2', 384)        # Alternative name
        ]
        
        for model_name, dim in model_options:
            try:
                logger.info(f"Loading embedding model: {model_name}")
                
                # Set cache directory to avoid downloads in container
                cache_dir = os.getenv('TRANSFORMERS_CACHE', '/tmp/transformers_cache')
                os.makedirs(cache_dir, exist_ok=True)
                
                self.model = SentenceTransformer(
                    model_name, 
                    cache_folder=cache_dir,
                    device='cpu'  # Use CPU for better compatibility
                )
                
                self.model_name = model_name
                self.embedding_dim = dim
                
                logger.info(f"Successfully loaded {model_name} (dim={dim})")
                return
                
            except Exception as e:
                logger.warning(f"Failed to load {model_name}: {e}")
                continue
        
        raise RuntimeError("Could not load any embedding model")
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode texts to embeddings
        
        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            
        Returns:
            NumPy array of embeddings (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        try:
            # Convert to float32 for better compatibility
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True,
                normalize_embeddings=True  # Cosine similarity ready
            )
            
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            # Return zeros as fallback
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
    
    def encode_single(self, text: str) -> List[float]:
        """Encode single text and return as list"""
        if not text:
            return [0.0] * self.embedding_dim
        
        try:
            embedding = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
            return embedding[0].astype(np.float32).tolist()
        except Exception as e:
            logger.error(f"Error encoding single text: {e}")
            return [0.0] * self.embedding_dim
    
    @property
    def info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'device': str(self.model.device) if self.model else None
        }


class BatchEmbedder:
    """Handles batch embedding of article chunks"""
    
    def __init__(self):
        self.embedding_model = EmbeddingModel()
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add embeddings to article chunks
        
        Args:
            chunks: List of chunk dictionaries (must have 'text' key)
            
        Returns:
            Same chunks with 'vector' key added
        """
        if not chunks:
            return []
        
        logger.info(f"Embedding {len(chunks)} chunks")
        
        # Extract texts
        texts = [chunk.get('text', '') for chunk in chunks]
        
        # Get embeddings
        embeddings = self.embedding_model.encode(texts)
        
        # Add vectors to chunks
        for i, chunk in enumerate(chunks):
            chunk['vector'] = embeddings[i].tolist()
        
        logger.info(f"Successfully embedded {len(chunks)} chunks")
        return chunks
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a search query"""
        return self.embedding_model.encode_single(query)
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """Get embedding model information"""
        return self.embedding_model.info


# Global instance
@lru_cache(maxsize=1)
def get_batch_embedder() -> BatchEmbedder:
    """Get global batch embedder instance"""
    return BatchEmbedder()


def embed_text(text: str) -> List[float]:
    """Convenience function to embed single text"""
    embedder = get_batch_embedder()
    return embedder.embed_query(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenience function to embed multiple texts"""
    embedder = get_batch_embedder()
    embeddings = embedder.embedding_model.encode(texts)
    return [emb.tolist() for emb in embeddings]