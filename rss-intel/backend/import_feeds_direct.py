#!/usr/bin/env python3
"""
Direct RSS import from inside backend container
"""

import httpx
import feedparser
import hashlib
from datetime import datetime, timezone
from app.store import ArticleStore
from app.deps import get_db
from app.scoring import ScoringEngine
from app.images import ImageProcessor
from app.proxy_utils import create_httpx_client, get_proxy_config, test_proxy_connection
import asyncio

# Test feeds
TEST_FEEDS = [
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://news.ycombinator.com/rss", "Hacker News"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://openai.com/blog/rss.xml", "OpenAI Blog"),
    ("https://arstechnica.com/feed/", "Ars Technica"),
]

async def main():
    print("🚀 Direct RSS import and scoring with images (inside Docker)...")
    print("=" * 70)
    
    # Test proxy connection först - MANDATORY PROXY (no fallback)
    print("\n🌐 Verifierar MANDATORY proxy-anslutning...")
    proxy_working = test_proxy_connection()
    if proxy_working:
        print("✅ Hetzner proxy fungerar - RSS-feeds hämtas ENDAST via 95.216.172.130")
    else:
        print("❌ KRITISKT FEL: Proxy fungerar inte!")
        print("🚫 RSS Intelligence stängs ner - ingen fallback tillåten!")
        return  # Avsluta funktionen
    print("-" * 70)
    
    db = next(get_db())
    store = ArticleStore(db)
    scorer = ScoringEngine()
    image_processor = ImageProcessor()
    
    total_articles = 0
    scored_articles = 0
    
    try:
        for feed_url, source_name in TEST_FEEDS:
            print(f"\n📡 Fetching: {source_name}")
            print(f"   URL: {feed_url}")
            
            try:
                # Fetch RSS feed via proxy
                with create_httpx_client(timeout=30) as client:
                    response = client.get(feed_url)
                feed = feedparser.parse(response.text)
                
                print(f"   Found {len(feed.entries)} entries")
                
                # Process entries (limit to 3 per feed for initial test)
                for entry in feed.entries[:3]:
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
                        print(f"     ⏭️  Already exists: {title[:40]}...")
                        continue
                    
                    # Get content/summary - try different sources for longer content
                    content = ""
                    
                    # First try content field (usually has full HTML content)
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value if hasattr(entry.content[0], 'value') else str(entry.content[0])
                        print(f"     🔍 Found detailed content field")
                    
                    # Fallback to summary/description
                    if not content:
                        content = entry.get('summary', entry.get('description', ''))
                        print(f"     🔍 Using summary/description field")
                    
                    print(f"     🔍 Content preview: {content[:150] if content else 'NO CONTENT'}...")
                    
                    # Clean HTML tags for storage
                    import re
                    if content:
                        content_text = re.sub(r'<[^>]+>', '', content)
                        content_text = ' '.join(content_text.split())
                    else:
                        content_text = ""
                    
                    # Extract image
                    image_meta = None
                    image_data = {}
                    try:
                        image_candidate = image_processor.pick_primary_image(entry)
                        if image_candidate:
                            print(f"     🖼️ Found image candidate: {image_candidate.url[:80]}...")
                            image_meta = await image_processor.fetch_and_cache(
                                image_candidate.url, url
                            )
                            if image_meta:
                                image_data = {
                                    "image_src_url": image_candidate.url,
                                    "image_proxy_path": image_meta.proxy_path,
                                    "image_width": image_meta.width,
                                    "image_height": image_meta.height,
                                    "image_blurhash": image_meta.blurhash_value,
                                    "has_image": True
                                }
                                print(f"     ✅ Image cached: {image_meta.width}x{image_meta.height}")
                            else:
                                print(f"     ❌ Image fetch failed")
                        else:
                            print(f"     📷 No image found")
                    except Exception as e:
                        print(f"     ❌ Image error: {e}")
                    
                    # Set has_image for scoring
                    has_image = image_data.get("has_image", False)
                    
                    score_total, scores, topics, entities = scorer.calculate_score(
                        title=title,
                        content=content_text,
                        source=source_name,
                        published_at=published_at,
                        has_image=has_image
                    )
                    
                    # Create article data
                    article_data = {
                        "freshrss_entry_id": entry_id,
                        "title": title,
                        "url": url,
                        "content": content_text[:1000] if content_text else None,  # Store first 1000 chars
                        "source": source_name,
                        "published_at": published_at,
                        "score_total": score_total,
                        "scores": scores,
                        "topics": topics,
                        "entities": {"matched": entities},
                        "flags": {},
                        **image_data  # Add image fields
                    }
                    
                    # Add flags based on score
                    if score_total >= 80:
                        article_data["flags"]["hot"] = True
                    elif score_total >= 60:
                        article_data["flags"]["interesting"] = True
                    
                    # Store article
                    store.upsert_article(article_data)
                    total_articles += 1
                    scored_articles += 1
                    
                    # Show score breakdown
                    score_parts = []
                    if scores.get('keyword_score', 0) > 0:
                        score_parts.append(f"keywords:{scores['keyword_score']}")
                    if scores.get('entity_score', 0) > 0:
                        score_parts.append(f"entities:{scores['entity_score']}")
                    if scores.get('source_score', 0) > 0:
                        score_parts.append(f"source:{scores['source_score']}")
                    
                    status_emoji = "🔥" if score_total >= 80 else "✨" if score_total >= 60 else "📄"
                    print(f"     {status_emoji} {title[:45]}... (Score: {score_total})")
                    if topics:
                        print(f"        Topics: {', '.join(topics[:3])}")
                    if entities:
                        print(f"        Entities: {', '.join(entities[:3])}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
    
    finally:
        db.close()
    
    print("\n" + "=" * 70)
    print(f"📊 Import Summary:")
    print(f"   Total articles imported: {total_articles}")
    print(f"   Articles scored: {scored_articles}")
    
    if scored_articles > 0:
        print(f"\n✨ Success! Visit http://localhost:3001 to see scored articles")
        print(f"   🔥 Hot articles (80+): Check for red highlights")
        print(f"   ✨ Interesting articles (60+): Check for yellow highlights")
    else:
        print(f"\n⚠️  No new articles imported")

if __name__ == "__main__":
    asyncio.run(main())