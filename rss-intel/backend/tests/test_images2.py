"""
Tests for enhanced image extraction pipeline
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.images2 import ImageExtractor, ImageCandidate, CachedImageMeta

@pytest.fixture
def image_extractor():
    return ImageExtractor()

class TestImageCandidate:
    def test_area_calculation(self):
        candidate = ImageCandidate("http://example.com/image.jpg", width=400, height=300)
        assert candidate.area == 120000
        
        # No dimensions
        candidate_no_dims = ImageCandidate("http://example.com/image.jpg")
        assert candidate_no_dims.area == 0

class TestImageExtractor:
    
    def test_normalize_candidate_url(self, image_extractor):
        base_url = "https://example.com/article"
        
        # Relative URL
        relative = "images/photo.jpg"
        result = image_extractor.normalize_candidate_url(base_url, relative)
        assert result == "https://example.com/images/photo.jpg"
        
        # Absolute URL with tracking
        tracked = "https://cdn.example.com/photo.jpg?utm_source=newsletter&fbclid=123"
        result = image_extractor.normalize_candidate_url(base_url, tracked)
        assert "utm_source" not in result
        assert "fbclid" not in result
        assert result == "https://cdn.example.com/photo.jpg"
    
    def test_extract_youtube_id(self, image_extractor):
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ", 
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
        ]
        
        for url in urls:
            video_id = image_extractor._extract_youtube_id(url)
            assert video_id == "dQw4w9WgXcQ"
        
        # Invalid URL
        assert image_extractor._extract_youtube_id("https://example.com") is None
    
    def test_extract_from_rss_enclosures(self, image_extractor):
        entry = {
            "enclosures": [
                {"href": "https://example.com/photo.jpg", "type": "image/jpeg"},
                {"href": "https://example.com/video.mp4", "type": "video/mp4"},  # Should be ignored
                {"href": "https://example.com/photo2.png", "type": "image/png"},
            ]
        }
        
        candidates = image_extractor._extract_from_rss_enclosures(entry)
        assert len(candidates) == 2
        assert all(c.source_type == "enclosure" for c in candidates)
        assert candidates[0].url == "https://example.com/photo.jpg"
        assert candidates[1].url == "https://example.com/photo2.png"
    
    def test_extract_from_media_content(self, image_extractor):
        entry = {
            "media_content": [
                {"url": "https://example.com/large.jpg", "medium": "image", "width": "800", "height": "600"},
                {"url": "https://example.com/video.mp4", "medium": "video"},  # Should be ignored
            ],
            "media_thumbnail": [
                {"url": "https://example.com/thumb.jpg", "width": "150", "height": "100"},
            ]
        }
        
        candidates = image_extractor._extract_from_media_content(entry)
        assert len(candidates) == 2
        
        # Check media content
        media_candidate = next(c for c in candidates if c.width == 800)
        assert media_candidate.height == 600
        assert media_candidate.confidence == 0.85
        
        # Check thumbnail 
        thumb_candidate = next(c for c in candidates if c.width == 150)
        assert thumb_candidate.confidence == 0.7
    
    def test_extract_from_content_html(self, image_extractor):
        content_html = """
        <div>
            <img src="photo1.jpg" width="400" height="300" alt="Photo 1" />
            <img data-src="lazy-photo.jpg" width="600" height="400" />
            <img srcset="small.jpg 400w, large.jpg 800w" />
            <noscript>
                <img src="noscript-photo.jpg" width="500" height="300" />
            </noscript>
        </div>
        """
        base_url = "https://example.com/article"
        
        candidates = image_extractor._extract_from_content(content_html, base_url)
        
        # Should find multiple images
        assert len(candidates) >= 3
        assert all(c.source_type == "content" for c in candidates)
        
        # Check that URLs are normalized
        urls = [c.url for c in candidates]
        assert any("https://example.com/photo1.jpg" in url for url in urls)
        assert any("lazy-photo.jpg" in url for url in urls)
    
    def test_extract_from_meta_tags(self, image_extractor):
        page_html = """
        <html>
        <head>
            <meta property="og:image" content="https://example.com/og-image.jpg" />
            <meta name="twitter:image" content="https://example.com/twitter-image.jpg" />
            <meta property="og:image:width" content="1200" />
        </head>
        </html>
        """
        base_url = "https://example.com/article"
        
        candidates = image_extractor._extract_from_meta_tags(page_html, base_url)
        
        assert len(candidates) == 2
        assert all(c.source_type == "og" for c in candidates)
        urls = [c.url for c in candidates]
        assert "https://example.com/og-image.jpg" in urls
        assert "https://example.com/twitter-image.jpg" in urls
    
    def test_extract_from_jsonld(self, image_extractor):
        page_html = """
        <script type="application/ld+json">
        {
            "@type": "Article",
            "headline": "Test Article",
            "image": [
                "https://example.com/image1.jpg",
                {"@type": "ImageObject", "url": "https://example.com/image2.jpg", "width": 800, "height": 600}
            ]
        }
        </script>
        """
        base_url = "https://example.com/article"
        
        candidates = image_extractor._extract_from_jsonld(page_html, base_url)
        
        assert len(candidates) == 2
        assert all(c.source_type == "jsonld" for c in candidates)
        
        # Check that structured data with dimensions is parsed
        structured_candidate = next(c for c in candidates if c.width == 800)
        assert structured_candidate.height == 600
    
    def test_extract_youtube_thumbnails(self, image_extractor):
        entry = {
            "content": [{"value": "Check out this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"}]
        }
        base_url = "https://example.com/article"
        
        candidates = image_extractor._extract_youtube_thumbnails(entry, base_url)
        
        assert len(candidates) == 3  # maxres, hq, mq
        assert all(c.source_type == "yt" for c in candidates)
        assert all("dQw4w9WgXcQ" in c.url for c in candidates)
        
        # Check confidence ordering (maxres should be highest)
        candidates_sorted = sorted(candidates, key=lambda x: x.confidence, reverse=True)
        assert candidates_sorted[0].width == 1280
        assert candidates_sorted[0].height == 720
    
    def test_is_blocked_by_patterns(self, image_extractor):
        # Mock rules
        image_extractor.rules = {
            "global": {"blocked_patterns": ["logo", "sprite", "icon"]},
            "domains": {
                "example.com": {"blocked_patterns": ["ads", "banner"]}
            }
        }
        
        # Test global blocking
        assert image_extractor._is_blocked_by_patterns("https://site.com/logo.png") is True
        assert image_extractor._is_blocked_by_patterns("https://site.com/photo.jpg") is False
        
        # Test domain-specific blocking
        assert image_extractor._is_blocked_by_patterns("https://example.com/ads.jpg", "example.com") is True
        assert image_extractor._is_blocked_by_patterns("https://example.com/photo.jpg", "example.com") is False
    
    def test_meets_size_requirements(self, image_extractor):
        # Good candidate
        good_candidate = ImageCandidate("http://example.com/photo.jpg", width=400, height=300)
        assert image_extractor._meets_size_requirements(good_candidate) is True
        
        # Too small
        small_candidate = ImageCandidate("http://example.com/tiny.jpg", width=100, height=50)
        assert image_extractor._meets_size_requirements(small_candidate) is False
        
        # Bad aspect ratio (too wide)
        wide_candidate = ImageCandidate("http://example.com/wide.jpg", width=1000, height=100)
        assert image_extractor._meets_size_requirements(wide_candidate) is False
        
        # No dimensions (should pass)
        no_dims_candidate = ImageCandidate("http://example.com/unknown.jpg")
        assert image_extractor._meets_size_requirements(no_dims_candidate) is True
    
    def test_select_best_candidate(self, image_extractor):
        candidates = [
            ImageCandidate("http://example.com/small.jpg", width=200, height=150, confidence=0.8),
            ImageCandidate("http://example.com/large.jpg", width=800, height=600, confidence=0.7),
            ImageCandidate("http://example.com/logo.jpg", width=400, height=300, confidence=0.9),  # Should be blocked
            ImageCandidate("http://example.com/best.jpg", width=600, height=400, confidence=0.85),
        ]
        
        # Mock the blocking method to block logo
        image_extractor._is_blocked_by_patterns = lambda url, domain=None: "logo" in url
        image_extractor._meets_size_requirements = lambda c, domain=None: c.width >= 300
        
        best = image_extractor.select_best_candidate(candidates)
        
        # Should pick the highest confidence among valid candidates
        assert best.url == "http://example.com/best.jpg"
        assert best.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_get_cache_path(self, image_extractor):
        url = "https://example.com/photos/image.jpg"
        file_path, proxy_path = image_extractor._get_cache_path(url)
        
        # Should create hierarchical path
        assert "/" in str(file_path)
        assert proxy_path.count("/") == 2  # h1/h2/filename
        assert proxy_path.endswith(".jpg")

class TestIntegration:
    
    @pytest.mark.asyncio
    async def test_extract_primary_image_priority(self, image_extractor):
        """Test that extraction follows priority order"""
        
        # Mock entry with multiple image sources
        entry = {
            "link": "https://example.com/article",
            "enclosures": [
                {"href": "https://example.com/enclosure.jpg", "type": "image/jpeg"}
            ],
            "media_content": [
                {"url": "https://example.com/media.jpg", "medium": "image"}
            ],
            "content": [{"value": '<img src="content.jpg" />'}]
        }
        
        # Mock all the internal methods to return candidates
        image_extractor._extract_from_rss_enclosures = Mock(return_value=[
            ImageCandidate("https://example.com/enclosure.jpg", confidence=0.9, source_type="enclosure")
        ])
        image_extractor._extract_from_media_content = Mock(return_value=[
            ImageCandidate("https://example.com/media.jpg", confidence=0.85, source_type="media")
        ])
        image_extractor._extract_from_content = Mock(return_value=[
            ImageCandidate("https://example.com/content.jpg", confidence=0.8, source_type="content")
        ])
        
        # Should select enclosure (highest priority)
        result = await image_extractor.extract_primary_image(entry)
        
        assert result is not None
        assert result.source_type == "enclosure"
        assert result.url == "https://example.com/enclosure.jpg"

    @pytest.mark.asyncio 
    async def test_fetch_and_cache_image_success(self, image_extractor):
        """Test successful image fetch and cache"""
        
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_response.headers = {
            'content-type': 'image/jpeg',
            'etag': '"12345"',
            'last-modified': 'Wed, 21 Oct 2015 07:28:00 GMT'
        }
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        image_extractor.get_session = AsyncMock(return_value=mock_session)
        
        # Mock PIL Image processing
        with patch('app.images2.Image') as mock_image:
            mock_img = Mock()
            mock_img.size = (800, 600)
            mock_img.mode = 'RGB'
            mock_img.save = Mock()
            mock_image.open.return_value.__enter__.return_value = mock_img
            
            # Mock blurhash generation
            with patch('app.images2.blurhash') as mock_blurhash:
                mock_blurhash.encode.return_value = "test_hash"
                
                # Mock file operations
                with patch('pathlib.Path.exists', return_value=False), \
                     patch('pathlib.Path.mkdir'), \
                     patch('pathlib.Path.stat') as mock_stat, \
                     patch('builtins.open', mock_open=True), \
                     patch('pathlib.Path.unlink'):
                    
                    mock_stat.return_value.st_size = 50000
                    
                    result = await image_extractor.fetch_and_cache_image(
                        "https://example.com/image.jpg",
                        referer="https://example.com/article"
                    )
                    
                    assert result is not None
                    assert isinstance(result, CachedImageMeta)
                    assert result.width == 800
                    assert result.height == 600
                    assert result.blurhash == "test_hash"


# Mock open function for file operations
def mock_open(filename, mode='r', *args, **kwargs):
    if 'w' in mode:
        return Mock()
    elif filename.endswith('.json'):
        return Mock(read=Mock(return_value='{}'))
    else:
        return Mock()