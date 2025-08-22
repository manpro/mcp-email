#!/usr/bin/env python3
"""
Import RSS feeds into FreshRSS via backend
"""

import yaml
import time
import sys
from pathlib import Path
from freshrss_client import FreshRSSClient
from config import settings

def load_sources():
    """Load sources from config file"""
    config_path = Path(settings.config_dir) / "sources.yml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    print("🚀 Starting RSS feed import to FreshRSS...")
    print("=" * 60)
    
    # Initialize FreshRSS client
    client = FreshRSSClient()
    
    if not client.login():
        print("❌ Failed to login to FreshRSS")
        return
    
    print("✅ Connected to FreshRSS")
    
    # Load sources
    sources = load_sources()
    
    total_feeds = 0
    successful_imports = 0
    
    # Import RSSHub routes
    if sources.get("rsshub", {}).get("enabled", False):
        print("\n📡 Importing RSSHub routes...")
        print("-" * 40)
        
        for route in sources["rsshub"].get("routes", []):
            feed_url = f"{settings.rsshub_base_url}{route}.rss"
            
            # Extract a nice title from the route
            if "twitter/user/" in route:
                title = f"Twitter: {route.split('/')[-1]}"
            elif "reddit/r/" in route:
                parts = route.split('/')
                subreddit = parts[2] if len(parts) > 2 else "unknown"
                title = f"Reddit: r/{subreddit}"
            elif "github/trending" in route:
                title = f"GitHub Trending: {route.split('/')[-1]}"
            else:
                title = route.replace("/", " - ").strip(" -")
            
            total_feeds += 1
            
            try:
                if client.create_feed(feed_url, title):
                    print(f"  ✅ Added: {title}")
                    successful_imports += 1
                else:
                    print(f"  ⏭️  Skipped: {title} (may already exist)")
            except Exception as e:
                print(f"  ❌ Failed: {title} - {str(e)}")
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.2)
    
    # Import native feeds
    print("\n📰 Importing native RSS feeds...")
    print("-" * 40)
    
    for feed_url in sources.get("native_feeds", []):
        total_feeds += 1
        
        # Extract domain as title hint
        try:
            from urllib.parse import urlparse
            domain = urlparse(feed_url).netloc
            title = domain.replace("www.", "").replace(".com", "").replace(".org", "").title()
        except:
            title = "Feed"
        
        try:
            if client.create_feed(feed_url, title):
                print(f"  ✅ Added: {title}")
                successful_imports += 1
            else:
                print(f"  ⏭️  Skipped: {title} (may already exist)")
        except Exception as e:
            print(f"  ❌ Failed: {title} - {str(e)}")
        
        # Small delay
        time.sleep(0.2)
    
    # Close client
    client.client.close()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Import Summary:")
    print(f"   Total feeds processed: {total_feeds}")
    print(f"   Successfully imported: {successful_imports}")
    print(f"   Failed/Skipped: {total_feeds - successful_imports}")
    
    if successful_imports > 0:
        print(f"\n✨ Success! {successful_imports} feeds imported to FreshRSS")
        print(f"   The system will start scoring articles in the next refresh cycle")
    else:
        print(f"\n⚠️  No new feeds were imported (they may already exist)")

if __name__ == "__main__":
    main()