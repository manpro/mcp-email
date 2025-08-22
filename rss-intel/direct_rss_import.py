#!/usr/bin/env python3
"""
Direct RSS import bypassing FreshRSS for testing
"""

import httpx
import feedparser
import hashlib
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add the backend path
sys.path.append('/home/micke/claude-env/rss-intel/backend')

from app.store import ArticleStore
from app.deps import SessionLocal
from app.scoring import ScoringEngine

# Test feeds
TEST_FEEDS = [
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://news.ycombinator.com/rss", "Hacker News"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://openai.com/blog/rss.xml", "OpenAI Blog"),
]

def fetch_and_score_feeds():
    print("🚀 Direct RSS import and scoring...")
    print("=" * 60)
    
    # Create local database connection
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use localhost instead of postgres hostname
    DATABASE_URL = "postgresql://rss:changeme@localhost:5432/rssintel"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    store = ArticleStore(db)
    scorer = ScoringEngine()
    
    total_articles = 0
    scored_articles = 0
    
    try:
        for feed_url, source_name in TEST_FEEDS:
            print(f"\n📡 Fetching: {source_name}")
            print(f"   URL: {feed_url}")
            
            try:
                # Fetch RSS feed
                response = httpx.get(feed_url, timeout=30, follow_redirects=True)
                feed = feedparser.parse(response.text)
                
                print(f"   Found {len(feed.entries)} entries")
                
                # Process entries
                for entry in feed.entries[:5]:  # Limit to 5 per feed
                    title = entry.get('title', 'No title')
                    url = entry.get('link', '')
                    
                    # Get published date
                    if 'published_parsed' in entry:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    else:
                        published_at = datetime.now(timezone.utc)
                    
                    # Generate entry ID
                    entry_id = f"direct_{hashlib.md5(url.encode()).hexdigest()[:12]}"
                    
                    # Check if already exists
                    if store.get_article_by_entry_id(entry_id):
                        continue
                    
                    # Calculate score
                    content = entry.get('summary', entry.get('description', ''))
                    score_total, scores, topics, entities = scorer.calculate_score(
                        title=title,
                        content=content,
                        source=source_name,
                        published_at=published_at
                    )
                    
                    # Create article data
                    article_data = {
                        "freshrss_entry_id": entry_id,
                        "title": title,
                        "url": url,
                        "source": source_name,
                        "published_at": published_at,
                        "score_total": score_total,
                        "scores": scores,
                        "topics": topics,
                        "entities": {"matched": entities},
                        "flags": {}
                    }
                    
                    # Add flags based on score
                    if score_total >= scorer.scoring_config.get("thresholds", {}).get("star", 80):
                        article_data["flags"]["hot"] = True
                    elif score_total >= scorer.scoring_config.get("thresholds", {}).get("interesting", 60):
                        article_data["flags"]["interesting"] = True
                    
                    # Store article
                    store.upsert_article(article_data)
                    total_articles += 1
                    scored_articles += 1
                    
                    print(f"     ✅ {title[:50]}... (Score: {score_total})")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
    
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print(f"📊 Import Summary:")
    print(f"   Total articles imported: {total_articles}")
    print(f"   Articles scored: {scored_articles}")
    
    if scored_articles > 0:
        print(f"\n✨ Success! Check http://localhost:3001 to see scored articles")
    else:
        print(f"\n⚠️  No new articles imported")

if __name__ == "__main__":
    fetch_and_score_feeds()