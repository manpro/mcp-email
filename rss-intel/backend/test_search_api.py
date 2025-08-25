#!/usr/bin/env python3
"""
Test search API endpoints
"""

import requests
import json
import time

def test_search_api():
    """Test search and ask API endpoints"""
    
    base_url = "http://localhost:8000/api"
    
    print("Testing Search API endpoints...")
    print("=" * 50)
    
    # Test 1: Search endpoint
    print("\n1. Testing /search endpoint...")
    
    search_params = {
        'q': 'artificial intelligence machine learning',
        'k': 5,
        'hybrid': True,
        'alpha': 0.7
    }
    
    try:
        response = requests.get(f"{base_url}/search", params=search_params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search successful!")
            print(f"   Query: {data['query']}")
            print(f"   Results found: {data['total_found']}")
            print(f"   Search time: {data['search_time_ms']}ms")
            print(f"   Filters: {data['filters']}")
            
            print(f"\n   Top results:")
            for i, result in enumerate(data['results'][:3]):
                print(f"   {i+1}. [{result['source']}] {result['title']}")
                print(f"      Relevance: {result['relevance_score']}, Score: {result['rule_score']}")
                print(f"      Why: {', '.join(result['why_chips'])}")
                print(f"      Snippet: {result['snippet'][:100]}...")
                print()
        else:
            print(f"❌ Search failed: {response.status_code} - {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Is it running on localhost:8000?")
        return False
    
    except Exception as e:
        print(f"❌ Search test error: {e}")
    
    # Test 2: Ask endpoint
    print("\n2. Testing /ask endpoint...")
    
    ask_payload = {
        'q': 'What are the latest developments in blockchain technology?',
        'k': 10
    }
    
    try:
        response = requests.post(f"{base_url}/ask", json=ask_payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ask successful!")
            print(f"   Question: {data['question']}")
            print(f"   Confidence: {data['confidence']}")
            print(f"   Sources used: {data['sources_count']}")
            print(f"   Generation time: {data['generation_time_ms']}ms")
            
            print(f"\n   Answer:")
            print(f"   {data['answer']}")
            
            print(f"\n   Citations ({len(data['citations'])}):")
            for i, citation in enumerate(data['citations'][:3]):
                print(f"   {i+1}. [{citation['source']}] {citation['title']}")
                print(f"      Relevance: {citation.get('relevance_score', 0.0):.3f}")
                print(f"      URL: {citation['url'][:80]}...")
                print()
        else:
            print(f"❌ Ask failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Ask test error: {e}")
    
    # Test 3: Search stats endpoint
    print("\n3. Testing /search/stats endpoint...")
    
    try:
        response = requests.get(f"{base_url}/search/stats")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stats successful!")
            print(f"   Knowledge base: {data['knowledge_base']}")
            print(f"   Embedding model: {data['embedding_model']}")
            print(f"   Vector store: {data['vector_store']}")
        else:
            print(f"❌ Stats failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Stats test error: {e}")
    
    print("\n" + "=" * 50)
    print("API tests completed!")
    return True

if __name__ == "__main__":
    test_search_api()