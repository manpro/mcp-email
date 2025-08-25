#!/usr/bin/env python3
"""
Test hybrid search functionality with Weaviate
"""

import asyncio
import sys
from sentence_transformers import SentenceTransformer

# Import app modules
sys.path.insert(0, '/app')
from app.vec.weaviate_client import weaviate_manager

async def test_hybrid_search():
    """Test hybrid search functionality"""
    
    print("Testing Weaviate hybrid search functionality...")
    
    # Check collection stats
    stats = weaviate_manager.get_collection_stats()
    print(f"Collection stats: {stats}")
    
    if stats['total_chunks'] == 0:
        print("No chunks in database yet - wait for population to complete")
        return
    
    # Initialize embedding model
    print("Loading sentence transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Test queries
    test_queries = [
        "artificial intelligence machine learning",
        "blockchain cryptocurrency bitcoin",
        "payment systems fintech",
        "cybersecurity data protection",
        "software development programming"
    ]
    
    for query in test_queries:
        print(f"\n=== Testing query: '{query}' ===")
        
        # Generate embedding for query
        query_vector = model.encode(query).astype('float32').tolist()
        
        # Perform hybrid search
        results = weaviate_manager.hybrid_search(
            query=query,
            vector=query_vector,
            limit=5,
            alpha=0.7  # Favor vector search over BM25
        )
        
        print(f"Found {len(results)} results:")
        
        for i, result in enumerate(results):
            print(f"{i+1}. [{result['source']}] {result['title']}")
            print(f"   Search score: {result['search_score']:.4f}")
            print(f"   Published: {result['published_at']}")
            print(f"   Text preview: {result['text'][:200]}...")
            print()
    
    print("Hybrid search test completed!")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())