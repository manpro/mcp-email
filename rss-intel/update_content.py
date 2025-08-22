#!/usr/bin/env python3
"""
Update existing articles with content from RSS feeds
"""

import httpx
import feedparser
import hashlib
import sys
import os
sys.path.append('/app')

from app.store import ArticleStore
from app.deps import get_db

# Test feeds
TEST_FEEDS = [
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://news.ycombinator.com/rss", "Hacker News"),
    ("https://arstechnica.com/feed/", "Ars Technica"),
]

def main():
    print("🔄 Updating existing articles with content...")
    print("=" * 60)
    
    db = next(get_db())
    store = ArticleStore(db)
    
    updated_count = 0
    
    try:
        for feed_url, source_name in TEST_FEEDS:
            print(f"\n📡 Processing: {source_name}")
            
            try:
                # Fetch RSS feed
                response = httpx.get(feed_url, timeout=30, follow_redirects=True)
                feed = feedparser.parse(response.text)
                
                print(f"   Found {len(feed.entries)} entries")
                
                # Process entries
                for entry in feed.entries[:10]:  # Check more entries
                    title = entry.get('title', 'No title')
                    url = entry.get('link', '')
                    
                    # Generate entry ID
                    entry_id = f"direct_{hashlib.md5(url.encode()).hexdigest()[:12]}"
                    
                    # Check if exists and needs content
                    article = store.get_article_by_entry_id(entry_id)
                    if not article:
                        continue
                        
                    if article.content:
                        continue  # Already has content
                    
                    # Get content/summary - try different sources for longer content
                    content = ""
                    
                    # First try content field (usually has full HTML content)
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value if hasattr(entry.content[0], 'value') else str(entry.content[0])
                    
                    # Fallback to summary/description
                    if not content:
                        content = entry.get('summary', entry.get('description', ''))
                    
                    if content:
                        # Clean HTML tags and store longer content
                        import re
                        # Remove HTML tags but keep text
                        content_text = re.sub(r'<[^>]+>', '', content)
                        # Remove extra whitespace
                        content_text = ' '.join(content_text.split())
                        # Store first 1000 chars instead of 500
                        article.content = content_text[:1000]
                        updated_count += 1
                        print(f"   ✅ Updated: {title[:40]}...")
                        print(f"      Content: {content[:100]}...")
                    else:
                        print(f"   ❌ No content: {title[:40]}...")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        # Commit all changes
        db.commit()
    
    finally:
        db.close()
    
    print(f"\n✨ Updated {updated_count} articles with content")

if __name__ == "__main__":
    main()