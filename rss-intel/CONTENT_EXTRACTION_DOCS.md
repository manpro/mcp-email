# RSS Intelligence Dashboard - Content Extraction Documentation

## Overview

The RSS Intelligence Dashboard now includes full article content extraction capabilities, allowing users to read complete articles directly within the application without leaving the dashboard.

## Features

### 🎯 Core Features
- **Full Article Extraction**: Extracts complete article text from web pages
- **Multiple Extraction Methods**: Uses newspaper3k with fallback to readability-lxml
- **Reader Mode**: Clean, distraction-free reading experience
- **Iframe Fallback**: View original page when extraction fails
- **Rate Limiting**: Respects server resources with configurable rate limits
- **Robots.txt Compliance**: Checks robots.txt before extraction
- **Background Processing**: Async extraction with queue management
- **User Agent Rotation**: Rotates user agents to avoid blocking

### 📊 Extraction Statistics
- Track extraction success rates
- Monitor pending vs completed extractions
- View extraction errors and retry counts

## Architecture

### Backend Components

#### 1. ContentExtractor (`app/content_extractor.py`)
- Primary extraction using newspaper3k
- Fallback to readability-lxml
- HTML cleaning and sanitization
- Image extraction
- Keyword and summary generation

#### 2. ContentExtractionService (`app/content_service.py`)
- Rate limiting per domain
- Retry logic with exponential backoff
- Robots.txt compliance checking
- Concurrent extraction management
- Statistics tracking

#### 3. ExtractionWorker (`app/extraction_worker.py`)
- Background worker for batch processing
- Scheduled extraction runs
- On-demand extraction triggers
- Queue management

### Frontend Components

#### ArticleReader Component (`web/src/components/ArticleReader.tsx`)
- Modal reader interface
- Toggle between extracted content and iframe view
- Fullscreen mode
- Re-extraction trigger
- Loading states and error handling

## API Endpoints

### Get Article Content
```http
GET /articles/{article_id}/content
```
Returns extracted content if available, or extraction status.

**Response:**
```json
{
  "id": 123,
  "title": "Article Title",
  "url": "https://example.com/article",
  "full_content": "Full article text...",
  "content_html": "<p>HTML content...</p>",
  "content_summary": "Brief summary...",
  "content_keywords": ["keyword1", "keyword2"],
  "authors": ["Author Name"],
  "top_image_url": "https://example.com/image.jpg",
  "extracted_at": "2025-08-23T00:00:00Z",
  "extraction_status": "success"
}
```

### Trigger Article Extraction
```http
POST /articles/{article_id}/extract?force=false
```
Triggers content extraction for a specific article.

**Response:**
```json
{
  "status": "success",
  "message": "Content extracted successfully",
  "data": {
    "full_content": "...",
    "extraction_status": "success"
  }
}
```

### Batch Extraction
```http
POST /extraction/batch
```
**Body:**
```json
{
  "article_ids": [1, 2, 3],
  "force": false
}
```

### Process Pending Extractions
```http
POST /extraction/process-pending?limit=50&min_score=70
```

### Get Extraction Statistics
```http
GET /extraction/stats
```
**Response:**
```json
{
  "total_articles": 1000,
  "with_content": 750,
  "status_breakdown": {
    "success": 750,
    "pending": 200,
    "failed": 50
  },
  "extraction_rate": 75.0
}
```

### Get Extraction Worker Status
```http
GET /extraction/status
```

## Configuration

Add these settings to your `.env` file or environment variables:

```env
# Content Extraction Settings
CONTENT_EXTRACTION_ENABLED=true
CONTENT_EXTRACTION_MIN_SCORE=70        # Minimum score for auto-extraction
CONTENT_EXTRACTION_BATCH_SIZE=20       # Articles per batch
CONTENT_EXTRACTION_CONCURRENT=5        # Max concurrent extractions
CONTENT_EXTRACTION_RATE_LIMIT=1.0      # Requests per second per domain
CONTENT_EXTRACTION_INTERVAL_MINUTES=30 # Worker run interval
```

## Database Schema

New fields added to the `articles` table:

```sql
-- Content fields
full_content TEXT                      -- Extracted article text
content_html TEXT                      -- Clean HTML content
extracted_at TIMESTAMP WITH TIME ZONE  -- Extraction timestamp
extraction_status VARCHAR(20)          -- pending/success/failed/robots_blocked
extraction_error TEXT                  -- Error message if failed
content_keywords TEXT[]                -- Extracted keywords
content_summary TEXT                   -- Article summary
authors TEXT[]                         -- Article authors
top_image_url VARCHAR(500)            -- Main article image
robots_txt_checked BOOLEAN            -- Robots.txt check flag
```

## Usage

### Automatic Extraction
High-scoring articles (score >= 70 by default) are automatically queued for extraction during RSS polling.

### Manual Extraction
1. Click the 📖 (book) icon on any article card
2. The ArticleReader modal opens
3. If content isn't extracted yet, it triggers extraction automatically
4. Use the "Reader/Original" toggle to switch views

### Batch Processing
The extraction worker runs every 30 minutes by default to process pending articles.

### Force Re-extraction
Click the refresh icon in the ArticleReader to re-extract content.

## Performance Optimization

### Rate Limiting
- 1 request per second per domain (configurable)
- Domain-specific throttling
- Global concurrent limit (5 by default)

### Caching
- Robots.txt cached for 24 hours
- Extracted content stored in database
- No re-extraction unless forced

### Resource Management
- Async/await for non-blocking operations
- Connection pooling for HTTP requests
- Automatic retry with exponential backoff

## Troubleshooting

### Common Issues

#### Extraction Fails
- Check if the site blocks automated access
- Verify robots.txt compliance
- Try force re-extraction
- Check extraction_error in database

#### Slow Extraction
- Adjust CONTENT_EXTRACTION_CONCURRENT setting
- Increase CONTENT_EXTRACTION_RATE_LIMIT
- Check network connectivity

#### Missing Dependencies
```bash
docker-compose exec backend pip install newspaper3k readability-lxml aiohttp asyncio-throttle
```

#### Database Migration Issues
Run migration manually:
```bash
docker-compose exec backend alembic upgrade head
```

## Development

### Testing Extraction
```python
# Test extraction for a specific URL
from app.content_extractor import ContentExtractor

extractor = ContentExtractor()
content = await extractor.extract_article("https://example.com/article")
print(content.full_text)
```

### Adding New Extraction Methods
Extend the ContentExtractor class:
```python
async def _extract_with_custom_method(self, url: str) -> Optional[ArticleContent]:
    # Your extraction logic here
    pass
```

## Security Considerations

1. **User Agent Rotation**: Prevents blocking by identifying as different browsers
2. **Robots.txt Compliance**: Respects site crawling rules
3. **Rate Limiting**: Prevents overwhelming target servers
4. **HTML Sanitization**: Removes scripts and dangerous content
5. **Iframe Sandboxing**: Restricts iframe capabilities for security

## Best Practices

1. **Respect Content Owners**
   - Always check robots.txt
   - Use reasonable rate limits
   - Identify your bot properly

2. **Error Handling**
   - Log extraction failures
   - Provide fallback options
   - Retry with backoff

3. **Performance**
   - Process high-score articles first
   - Use batch processing
   - Cache when possible

4. **User Experience**
   - Show loading states
   - Provide extraction status
   - Allow manual triggers

## Future Enhancements

- [ ] PDF article support
- [ ] Archive.org fallback for dead links
- [ ] Translation integration
- [ ] Text-to-speech support
- [ ] Offline reading mode
- [ ] Content export (PDF, EPUB)
- [ ] ML-based content summarization
- [ ] Related articles suggestions

## Support

For issues or questions:
1. Check extraction_error in the database
2. Review backend logs: `docker-compose logs backend`
3. Test specific endpoints with curl
4. File an issue with error details