import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.main import app
from app.deps import get_db
from app.store import Base, Article

# Test database - use PostgreSQL or skip ARRAY fields
SQLALCHEMY_DATABASE_URL = "postgresql://rss:changeme@postgres:5432/rssintel_test"
try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
    engine.connect()
except:
    # Fallback to main database if test DB not available
    SQLALCHEMY_DATABASE_URL = "postgresql://rss:changeme@postgres:5432/rssintel"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class TestAPI:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and teardown for each test"""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def sample_article(self):
        """Create a sample article in the database"""
        db = TestingSessionLocal()
        article = Article(
            freshrss_entry_id="test_001",
            title="Test Payment Article",
            url="https://example.com/test",
            source="test.com",
            published_at=datetime.now(timezone.utc),
            content_hash="testhash123",
            score_total=75,
            scores={"keywords": 50, "source": 10, "watchlist": 15},
            entities={"matched": ["TestCorp"]},
            topics=["payments", "fintech"],
            flags={"interesting": True}
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        db.close()
        return article
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_get_items_empty(self):
        """Test getting items when database is empty"""
        response = client.get("/items")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
    
    def test_get_items_with_data(self, sample_article):
        """Test getting items with data"""
        response = client.get("/items")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Payment Article"
    
    def test_get_items_with_min_score(self, sample_article):
        """Test filtering by minimum score"""
        # Score is 75, should be included
        response = client.get("/items?min_score=70")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        
        # Score is 75, should be excluded
        response = client.get("/items?min_score=80")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
    
    def test_get_items_with_search(self, sample_article):
        """Test search functionality"""
        # Should find by title
        response = client.get("/items?q=Payment")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        
        # Should not find
        response = client.get("/items?q=Nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
    
    def test_get_items_pagination(self):
        """Test pagination"""
        # Create multiple articles
        db = TestingSessionLocal()
        for i in range(10):
            article = Article(
                freshrss_entry_id=f"test_{i:03d}",
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                source="test.com",
                published_at=datetime.now(timezone.utc),
                content_hash=f"hash{i}",
                score_total=50 + i
            )
            db.add(article)
        db.commit()
        db.close()
        
        # Get first page
        response = client.get("/items?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["items"]) == 5
        assert data["page"] == 1
        
        # Get second page
        response = client.get("/items?page=2&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["items"]) == 5
        assert data["page"] == 2
    
    def test_get_single_item(self, sample_article):
        """Test getting single item by entry ID"""
        response = client.get("/items/test_001")
        assert response.status_code == 200
        data = response.json()
        assert data["freshrss_entry_id"] == "test_001"
        assert data["title"] == "Test Payment Article"
    
    def test_get_nonexistent_item(self):
        """Test getting non-existent item"""
        response = client.get("/items/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_config_endpoint(self):
        """Test configuration endpoint"""
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "scoring" in data
        assert "thresholds" in data
        assert "sources" in data
    
    def test_scheduler_status(self):
        """Test scheduler status endpoint"""
        response = client.get("/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "last_run" in data
        assert "last_result" in data