#!/usr/bin/env python3
"""
Test OpenAI-enhanced RAG functionality
"""

import sys
import os

# Import app modules
sys.path.insert(0, '/app')
from app.rag_engine import rag_engine
from app.config import settings

def test_openai_rag():
    """Test Q&A functionality with and without OpenAI"""
    
    print("Testing OpenAI-Enhanced RAG Engine...")
    print("=" * 50)
    
    # Check OpenAI configuration
    if settings.openai_api_key:
        print(f"✅ OpenAI API key configured")
        print(f"   Model: {settings.openai_model}")
        print(f"   Max tokens: {settings.openai_max_tokens}")
        print(f"   Temperature: {settings.openai_temperature}")
    else:
        print("❌ No OpenAI API key configured")
        print("   Will use extractive approach only")
    
    print()
    
    # Test questions
    test_questions = [
        "What are the latest developments in artificial intelligence?",
        "How is blockchain technology changing payments?"
    ]
    
    for question in test_questions:
        print(f"Question: {question}")
        print("-" * 40)
        
        # Ask the question
        result = rag_engine.ask_question(
            question=question,
            max_chunks=8,
            alpha=0.7
        )
        
        # Display results
        print(f"Generation method: {result.get('generation_method', 'unknown')}")
        print(f"Confidence: {result['confidence']}")
        print(f"Sources used: {result.get('total_chunks_retrieved', 0)}")
        
        print(f"\nAnswer:")
        print(f"{result['answer']}")
        
        if result.get('sources'):
            print(f"\nTop sources:")
            for i, source in enumerate(result['sources'][:2]):
                print(f"{i+1}. [{source['source']}] {source['title']}")
        
        print("\n" + "=" * 50 + "\n")

if __name__ == "__main__":
    test_openai_rag()