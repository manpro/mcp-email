#!/usr/bin/env python3
"""
Test DirectRSSClient implementation
"""
import asyncio
import sys
import os

from app.direct_rss_client import DirectRSSClient
from app.deps import SessionLocal


async def test_direct_rss():
    """Test DirectRSSClient with a few feeds"""
    print("Testing DirectRSSClient...")
    
    db = SessionLocal()
    client = DirectRSSClient(db)
    
    try:
        # Test 1: Get feeds from database
        print("\n1. Getting feeds from database...")
        feeds = client.get_feeds()
        print(f"Found {len(feeds)} feeds:")
        for feed in feeds[:5]:  # Show first 5
            print(f"  - {feed['title']} ({feed['url']})")
        
        if not feeds:
            print("❌ No feeds found - something is wrong!")
            return
        
        # Test 2: Fetch a single feed
        print("\n2. Testing single feed fetch...")
        test_feed = feeds[0]  # Use first feed
        print(f"Fetching: {test_feed['title']}")
        
        entries = await client.fetch_feed_entries(
            test_feed['url'], 
            test_feed['title']
        )
        
        print(f"Fetched {len(entries)} entries")
        if entries:
            print("First entry:")
            entry = entries[0]
            print(f"  Title: {entry['title'][:80]}...")
            print(f"  URL: {entry['url']}")
            print(f"  Published: {entry['published_at']}")
            print(f"  Source: {entry['source']}")
        
        # Test 3: Get all entries (limited)
        print("\n3. Testing get_entries() with limit...")
        all_entries = await client.get_entries(limit=10)
        print(f"Got {len(all_entries)} total entries from all feeds")
        
        if all_entries:
            print("Sample entries:")
            for i, entry in enumerate(all_entries[:3]):
                print(f"  {i+1}. {entry['title'][:60]}... ({entry['source']})")
        
        print("\n✅ DirectRSSClient test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(test_direct_rss())