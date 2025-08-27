#!/usr/bin/env python3
"""
Integration tests for Search and Ask APIs
"""
import pytest
import httpx
from datetime import datetime
import json

BASE_URL = "http://localhost:8000"

class TestSearchAPI:
    """Test search API endpoint"""
    
    def test_search_basic(self):
        """Test basic search functionality"""
        response = httpx.get(f"{BASE_URL}/api/search", params={"q": "AI", "k": 5})
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "total_found" in data
        assert data["query"] == "AI"
        assert isinstance(data["results"], list)
    
    def test_search_with_filters(self):
        """Test search with language and hybrid filters"""
        response = httpx.get(
            f"{BASE_URL}/api/search",
            params={
                "q": "blockchain",
                "k": 10,
                "lang": "en",
                "hybrid": "true",
                "alpha": 0.7
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["lang"] == "en"
        assert data["filters"]["hybrid"] is True
        assert data["filters"]["alpha"] == 0.7
    
    def test_search_empty_query(self):
        """Test search with empty query"""
        response = httpx.get(f"{BASE_URL}/api/search", params={"q": ""})
        assert response.status_code == 422  # Validation error
    
    def test_search_result_structure(self):
        """Test search result data structure"""
        response = httpx.get(f"{BASE_URL}/api/search", params={"q": "technology", "k": 1})
        assert response.status_code == 200
        
        data = response.json()
        if data["results"]:
            result = data["results"][0]
            assert "article_id" in result
            assert "title" in result
            assert "snippet" in result
            assert "url" in result
            assert "source" in result
            assert "published_at" in result
            assert "relevance_score" in result
            assert "search_metadata" in result

class TestAskAPI:
    """Test Ask API endpoint"""
    
    def test_ask_basic(self):
        """Test basic question answering"""
        response = httpx.post(
            f"{BASE_URL}/api/ask",
            json={"q": "What is artificial intelligence?", "k": 5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "question" in data
        assert "confidence" in data
        assert "sources_count" in data
        assert "generation_time_ms" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
    
    def test_ask_with_language(self):
        """Test asking with language preference"""
        response = httpx.post(
            f"{BASE_URL}/api/ask",
            json={
                "q": "What are the latest blockchain trends?",
                "k": 10,
                "lang": "en"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["question"] == "What are the latest blockchain trends?"
        assert isinstance(data["citations"], list)
    
    def test_ask_invalid_request(self):
        """Test ask with invalid request"""
        response = httpx.post(
            f"{BASE_URL}/api/ask",
            json={"q": "ab"}  # Too short
        )
        assert response.status_code == 422  # Validation error
    
    def test_ask_citation_structure(self):
        """Test citation data structure in ask response"""
        response = httpx.post(
            f"{BASE_URL}/api/ask",
            json={"q": "Tell me about recent AI developments", "k": 3}
        )
        assert response.status_code == 200
        
        data = response.json()
        if data["citations"]:
            citation = data["citations"][0]
            assert "title" in citation
            assert "source" in citation
            assert "url" in citation
            assert "relevance_score" in citation

class TestIntelligenceAPI:
    """Test Intelligence API endpoints"""
    
    def test_intelligence_status(self):
        """Test intelligence system status"""
        response = httpx.get(f"{BASE_URL}/api/intelligence/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "trend_detector" in data
        assert "content_classifier" in data
        assert "sentiment_analyzer" in data
        assert "keyword_extractor" in data
        assert "quality_scorer" in data
        assert "similarity_detector" in data
    
    def test_get_current_trends(self):
        """Test getting current trends"""
        response = httpx.get(
            f"{BASE_URL}/api/intelligence/trends/current",
            params={"limit": 5, "min_confidence": 0.5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "trends" in data
        assert "total" in data
        assert "generated_at" in data
        assert isinstance(data["trends"], list)

class TestSystemHealth:
    """Test system health and performance"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = httpx.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_search_performance(self):
        """Test search response time"""
        start_time = datetime.now()
        response = httpx.get(f"{BASE_URL}/api/search", params={"q": "test", "k": 10})
        end_time = datetime.now()
        
        assert response.status_code == 200
        response_time = (end_time - start_time).total_seconds()
        assert response_time < 1.0  # Should respond within 1 second
        
        data = response.json()
        assert data["search_time_ms"] < 500  # Search should be under 500ms
    
    def test_ask_performance(self):
        """Test ask response time"""
        start_time = datetime.now()
        response = httpx.post(
            f"{BASE_URL}/api/ask",
            json={"q": "What is machine learning?", "k": 5}
        )
        end_time = datetime.now()
        
        assert response.status_code == 200
        response_time = (end_time - start_time).total_seconds()
        assert response_time < 3.0  # Should respond within 3 seconds
        
        data = response.json()
        assert data["generation_time_ms"] < 3000  # Generation should be under 3s

if __name__ == "__main__":
    # Run tests
    print("Running API Integration Tests...")
    
    # Test Search API
    search_tests = TestSearchAPI()
    search_tests.test_search_basic()
    search_tests.test_search_with_filters()
    search_tests.test_search_result_structure()
    print("✓ Search API tests passed")
    
    # Test Ask API
    ask_tests = TestAskAPI()
    ask_tests.test_ask_basic()
    ask_tests.test_ask_with_language()
    ask_tests.test_ask_citation_structure()
    print("✓ Ask API tests passed")
    
    # Test Intelligence API
    intel_tests = TestIntelligenceAPI()
    intel_tests.test_intelligence_status()
    intel_tests.test_get_current_trends()
    print("✓ Intelligence API tests passed")
    
    # Test System Health
    health_tests = TestSystemHealth()
    health_tests.test_health_check()
    health_tests.test_search_performance()
    health_tests.test_ask_performance()
    print("✓ System health tests passed")
    
    print("\n✅ All integration tests passed successfully!")