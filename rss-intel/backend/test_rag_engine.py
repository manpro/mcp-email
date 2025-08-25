#!/usr/bin/env python3
"""
Test RAG engine functionality
"""

import sys
import json

# Import app modules
sys.path.insert(0, '/app')
from app.rag_engine import rag_engine

def test_rag_engine():
    """Test Q&A functionality with RAG engine"""
    
    print("Testing RAG Engine Q&A functionality...")
    
    # Test questions
    test_questions = [
        "What are the latest developments in artificial intelligence?",
        "How is blockchain technology being used in payments?",
        "What are the current cybersecurity threats?",
        "What programming languages are trending?",
        "How does machine learning work in fintech?"
    ]
    
    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        # Ask the question
        result = rag_engine.ask_question(
            question=question,
            max_chunks=10,
            alpha=0.7  # Favor vector search
        )
        
        # Display results
        print(f"\nAnswer (Confidence: {result['confidence']}):")
        print(f"{result['answer']}")
        
        print(f"\nMetadata:")
        print(f"- Total chunks retrieved: {result['total_chunks_retrieved']}")
        print(f"- Chunks used in answer: {result['chunks_used']}")
        print(f"- Retrieval method: {result['retrieval_method']}")
        
        if result['sources']:
            print(f"\nSources ({len(result['sources'])}):")
            for i, source in enumerate(result['sources']):
                print(f"{i+1}. [{source['source']}] {source['title']}")
                print(f"   Published: {source['published_at']}")
                print(f"   Relevance: {source['relevance_score']:.3f}")
                print(f"   URL: {source['url'][:80]}...")
                print()
        
        # JSON output for debugging
        print(f"\nFull Result JSON:")
        result_copy = result.copy()
        # Truncate long fields for readability
        if 'answer' in result_copy and len(result_copy['answer']) > 200:
            result_copy['answer'] = result_copy['answer'][:200] + "..."
        print(json.dumps(result_copy, indent=2, default=str))
        print("\n")
    
    print("RAG Engine test completed!")

if __name__ == "__main__":
    test_rag_engine()