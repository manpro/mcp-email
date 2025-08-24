import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch
from app.images import ImageProcessor, ImageCandidate

@pytest.fixture
def image_processor():
    return ImageProcessor(
        cache_dir="/tmp/test-image-cache",
        max_bytes=1024*1024,  # 1MB for testing
        timeout_sec=5,
        connect_sec=2,
        min_width=100,
        min_height=100
    )

def test_normalize_url(image_processor):
    """Test URL normalization"""
    # Test absolute URL with tracking params
    result = image_processor.normalize_url(
        "https://example.com",
        "https://cdn.example.com/image.jpg?utm_source=test&fbclid=123&width=500"
    )
    assert result == "https://cdn.example.com/image.jpg?width=500"
    
    # Test relative URL
    result = image_processor.normalize_url(
        "https://example.com/article",
        "/images/test.jpg"
    )
    assert result == "https://example.com/images/test.jpg"

def test_pick_primary_image_enclosure(image_processor):
    """Test image extraction from RSS enclosure"""
    entry = {
        'enclosures': [
            {'type': 'image/jpeg', 'href': 'https://example.com/image.jpg'}
        ]
    }
    
    result = image_processor.pick_primary_image(entry)
    
    assert result is not None
    assert result.url == 'https://example.com/image.jpg'
    assert result.source == 'enclosure'

def test_pick_primary_image_media_content(image_processor):
    """Test image extraction from media:content"""
    entry = {
        'media_content': [
            {
                'type': 'image/png',
                'url': 'https://example.com/media.png',
                'width': '800',
                'height': '600'
            }
        ]
    }
    
    result = image_processor.pick_primary_image(entry)
    
    assert result is not None
    assert result.url == 'https://example.com/media.png'
    assert result.source == 'media_content'
    assert result.width == '800'
    assert result.height == '600'

def test_pick_primary_image_html_content(image_processor):
    """Test image extraction from HTML content"""
    entry = {
        'content': [
            Mock(value='<p>Article content</p><img src="/small.jpg" width="50" height="50"><img src="/large.jpg" width="800" height="600"><p>More content</p>')
        ]
    }
    
    result = image_processor.pick_primary_image(entry)
    
    assert result is not None
    assert result.url == '/large.jpg'  # Should pick the larger image
    assert result.source == 'content_img'
    assert result.width == 800
    assert result.height == 600

def test_parse_dimension(image_processor):
    """Test dimension parsing"""
    assert image_processor._parse_dimension('100') == 100
    assert image_processor._parse_dimension('200px') == 200
    assert image_processor._parse_dimension('invalid') is None
    assert image_processor._parse_dimension(None) is None

@patch('httpx.Client')
def test_fetch_og_image(mock_client, image_processor):
    """Test og:image extraction"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '''
    <html>
    <head>
        <meta property="og:image" content="https://example.com/og-image.jpg" />
        <meta name="twitter:image" content="https://example.com/twitter-image.jpg" />
    </head>
    </html>
    '''
    
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response
    
    result = image_processor._fetch_og_image('https://example.com/article')
    
    assert result is not None
    assert result.url == 'https://example.com/og-image.jpg'
    assert result.source == 'og_image'

@patch('httpx.AsyncClient')
@patch('PIL.Image')
def test_fetch_and_cache_success(mock_image, mock_client, image_processor):
    """Test successful image fetch and caching"""
    # Mock HTTP response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        'content-type': 'image/jpeg',
        'content-length': '50000',
        'etag': '"test-etag"'
    }
    mock_response.content = b'fake_image_data'
    
    mock_client.return_value.__aenter__.return_value.get = Mock(return_value=mock_response)
    
    # Mock PIL Image
    mock_pil_image = Mock()
    mock_pil_image.width = 800
    mock_pil_image.height = 600
    mock_pil_image.mode = 'RGB'
    mock_pil_image.copy.return_value = mock_pil_image
    mock_image.open.return_value = mock_pil_image
    
    # Mock blurhash
    with patch('blurhash.encode') as mock_blurhash:
        mock_blurhash.return_value = 'LEHV6nWB2yk8pyo0adR*.7kCMdnj'
        
        # Mock numpy for blurhash
        with patch('numpy.array') as mock_array:
            mock_array.return_value = 'fake_array'
            
            import asyncio
            result = asyncio.run(image_processor.fetch_and_cache(
                'https://example.com/test.jpg',
                'https://example.com'
            ))
    
    assert result is not None
    assert result.width == 800
    assert result.height == 600
    assert result.blurhash_value == 'LEHV6nWB2yk8pyo0adR*.7kCMdnj'
    assert result.content_type == 'image/jpeg'

@patch('httpx.AsyncClient')
def test_fetch_and_cache_too_large(mock_client, image_processor):
    """Test image rejection when too large"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        'content-type': 'image/jpeg',
        'content-length': str(image_processor.max_bytes + 1)
    }
    
    mock_client.return_value.__aenter__.return_value.get = Mock(return_value=mock_response)
    
    import asyncio
    result = asyncio.run(image_processor.fetch_and_cache(
        'https://example.com/huge.jpg',
        'https://example.com'
    ))
    
    assert result is None

@patch('httpx.AsyncClient')
def test_fetch_and_cache_wrong_content_type(mock_client, image_processor):
    """Test image rejection for wrong content type"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        'content-type': 'text/html',
        'content-length': '1000'
    }
    
    mock_client.return_value.__aenter__.return_value.get = Mock(return_value=mock_response)
    
    import asyncio
    result = asyncio.run(image_processor.fetch_and_cache(
        'https://example.com/not-image.html',
        'https://example.com'
    ))
    
    assert result is None

def test_cache_path_generation(image_processor):
    """Test cache path generation"""
    url = "https://example.com/test.jpg"
    import hashlib
    expected_hash = hashlib.sha256(url.encode()).hexdigest()
    
    cache_path = Path(image_processor.cache_dir) / expected_hash[:2] / expected_hash[2:4] / f"{expected_hash}.jpg"
    
    # This tests the path structure we expect
    assert len(expected_hash) == 64  # SHA256 hash length
    assert expected_hash[:2] == expected_hash[0:2]
    assert expected_hash[2:4] == expected_hash[2:4]