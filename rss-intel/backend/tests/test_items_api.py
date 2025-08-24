import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.deps import get_db
from app.store import Base, Article

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_articles():
    db = TestingSessionLocal()
    
    # Create sample articles with and without images
    articles_data = [
        {
            "freshrss_entry_id": "test_1",
            "title": "Article with Image",
            "url": "https://example.com/1",
            "content": "Article content with image",
            "source": "Test Source",
            "content_hash": "hash1",
            "score_total": 85,
            "scores": {"keywords": 10, "image_bonus": 3},
            "entities": {},
            "topics": ["AI", "Tech"],
            "flags": {"hot": True},
            "has_image": True,
            "image_src_url": "https://example.com/image1.jpg",
            "image_proxy_path": "ab/cd/hash1.jpg",
            "image_width": 800,
            "image_height": 600,
            "image_blurhash": "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
        },
        {
            "freshrss_entry_id": "test_2",
            "title": "Article without Image",
            "url": "https://example.com/2",
            "content": "Article content without image",
            "source": "Test Source",
            "content_hash": "hash2",
            "score_total": 70,
            "scores": {"keywords": 15},
            "entities": {},
            "topics": ["News"],
            "flags": {"interesting": True},
            "has_image": False
        },
        {
            "freshrss_entry_id": "test_3",
            "title": "Low Score Article with Image",
            "url": "https://example.com/3",
            "content": "Low score content",
            "source": "Other Source",
            "content_hash": "hash3",
            "score_total": 30,
            "scores": {"image_bonus": 3},
            "entities": {},
            "topics": [],
            "flags": {},
            "has_image": True,
            "image_src_url": "https://example.com/image3.jpg",
            "image_proxy_path": "ef/gh/hash3.jpg",
            "image_width": 400,
            "image_height": 300,
            "image_blurhash": "LHFFaXYk^6#M@-5c,1J5@[or[Q6."
        }
    ]
    
    for data in articles_data:
        article = Article(**data)
        db.add(article)
    
    db.commit()
    
    yield articles_data
    
    # Cleanup
    db.query(Article).delete()
    db.commit()
    db.close()

def test_get_items_basic(client, setup_database, sample_articles):
    """Test basic items endpoint"""
    response = client.get("/items")
    assert response.status_code == 200
    
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 3
    assert data["total"] == 3

def test_get_items_with_image_filter(client, setup_database, sample_articles):
    """Test filtering by has_image=true"""
    response = client.get("/items?has_image=true")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["items"]) == 2  # Only articles with images
    assert data["total"] == 2
    
    # Check all returned articles have images
    for item in data["items"]:
        assert item["has_image"] is True
        assert item["image_proxy_path"] is not None

def test_get_items_without_images(client, setup_database, sample_articles):
    """Test filtering by has_image=false"""
    response = client.get("/items?has_image=false")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["items"]) == 1  # Only article without image
    assert data["total"] == 1
    
    item = data["items"][0]
    assert item["has_image"] is False
    assert item["image_proxy_path"] is None

def test_get_items_score_filter_with_images(client, setup_database, sample_articles):
    """Test combining score and image filters"""
    response = client.get("/items?min_score=60&has_image=true")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["items"]) == 1  # Only high-score article with image
    assert data["total"] == 1
    
    item = data["items"][0]
    assert item["score_total"] >= 60
    assert item["has_image"] is True

def test_image_bonus_in_scoring(client, setup_database, sample_articles):
    """Test that image bonus is included in scoring"""
    response = client.get("/items")
    assert response.status_code == 200
    
    data = response.json()
    
    # Find articles with images
    image_articles = [item for item in data["items"] if item["has_image"]]
    
    for article in image_articles:
        # Check if scores contain image_bonus
        scores = article.get("scores", {})
        assert "image_bonus" in scores
        assert scores["image_bonus"] == 3

def test_image_fields_in_response(client, setup_database, sample_articles):
    """Test that all image fields are present in API response"""
    response = client.get("/items?has_image=true")
    assert response.status_code == 200
    
    data = response.json()
    article = data["items"][0]
    
    # Check all image fields are present
    expected_image_fields = [
        "has_image",
        "image_src_url", 
        "image_proxy_path",
        "image_width",
        "image_height", 
        "image_blurhash"
    ]
    
    for field in expected_image_fields:
        assert field in article
    
    # Check values for article with image
    if article["has_image"]:
        assert article["image_src_url"] is not None
        assert article["image_proxy_path"] is not None
        assert article["image_width"] > 0
        assert article["image_height"] > 0
        assert article["image_blurhash"] is not None

def test_config_includes_image_settings(client, setup_database):
    """Test that config endpoint includes image settings"""
    response = client.get("/config")
    assert response.status_code == 200
    
    data = response.json()
    assert "imageEnabled" in data
    assert "imageProxyBase" in data
    assert data["imageEnabled"] is True
    assert data["imageProxyBase"] == "/img"

def test_search_with_image_content(client, setup_database, sample_articles):
    """Test search functionality includes image articles"""
    response = client.get("/items?q=image")
    assert response.status_code == 200
    
    data = response.json()
    # Should find articles with "image" in title or content
    assert len(data["items"]) >= 1
    
    # Check that search results can include articles with images
    image_results = [item for item in data["items"] if item["has_image"]]
    assert len(image_results) > 0