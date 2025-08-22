#!/usr/bin/env python3
"""
Import RSS feeds into FreshRSS
"""

import httpx
import yaml
import time
import sys
from pathlib import Path

# Configuration
FRESHRSS_URL = "http://localhost:8081"
FRESHRSS_USER = "admin"
FRESHRSS_PASS = "adminadmin"
RSSHUB_URL = "http://localhost:1200"

def load_sources():
    """Load sources from config file"""
    config_path = Path("config/sources.yml")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def add_feed_to_freshrss(feed_url, title=None):
    """Add a single feed to FreshRSS using the web interface"""
    client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    try:
        # First, get the login page to get session
        login_page = client.get(f"{FRESHRSS_URL}/i/")
        
        # Login
        login_data = {
            "username": FRESHRSS_USER,
            "password": FRESHRSS_PASS,
            "submit": "Login"
        }
        
        login_response = client.post(
            f"{FRESHRSS_URL}/i/?c=auth&a=login",
            data=login_data
        )
        
        # Check if logged in
        if "logout" not in login_response.text.lower():
            print(f"  ⚠️  Login failed for {feed_url}")
            return False
        
        # Add the feed
        add_data = {
            "url_rss": feed_url,
            "category": "000000000001",  # Default category
        }
        
        if title:
            add_data["title"] = title
        
        add_response = client.post(
            f"{FRESHRSS_URL}/i/?c=feed&a=add",
            data=add_data
        )
        
        if "error" in add_response.text.lower():
            print(f"  ❌ Error adding feed: {feed_url[:60]}")
            return False
        else:
            print(f"  ✅ Added: {feed_url[:60]}")
            return True
            
    except Exception as e:
        print(f"  ❌ Failed to add {feed_url[:60]}: {str(e)}")
        return False
    finally:
        client.close()

def main():
    print("🚀 Starting RSS feed import to FreshRSS...")
    print("=" * 60)
    
    # Load sources
    sources = load_sources()
    
    total_feeds = 0
    successful_imports = 0
    
    # Import RSSHub routes
    if sources.get("rsshub", {}).get("enabled", False):
        print("\n📡 Importing RSSHub routes...")
        print("-" * 40)
        
        for route in sources["rsshub"].get("routes", []):
            feed_url = f"{RSSHUB_URL}{route}.rss"
            
            # Extract a nice title from the route
            if "twitter/user/" in route:
                title = f"Twitter: {route.split('/')[-1]}"
            elif "reddit/r/" in route:
                title = f"Reddit: r/{route.split('/')[-2]}"
            elif "github/trending" in route:
                title = f"GitHub Trending: {route.split('/')[-1]}"
            else:
                title = route.replace("/", " - ").strip(" -")
            
            total_feeds += 1
            if add_feed_to_freshrss(feed_url, title):
                successful_imports += 1
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)
    
    # Import native feeds
    print("\n📰 Importing native RSS feeds...")
    print("-" * 40)
    
    for feed_url in sources.get("native_feeds", []):
        total_feeds += 1
        
        # Extract domain as title hint
        try:
            from urllib.parse import urlparse
            domain = urlparse(feed_url).netloc
            title = domain.replace("www.", "").replace(".com", "").replace(".org", "")
        except:
            title = None
        
        if add_feed_to_freshrss(feed_url, title):
            successful_imports += 1
        
        # Small delay
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Import Summary:")
    print(f"   Total feeds processed: {total_feeds}")
    print(f"   Successfully imported: {successful_imports}")
    print(f"   Failed/Skipped: {total_feeds - successful_imports}")
    
    if successful_imports > 0:
        print(f"\n✨ Success! {successful_imports} feeds imported to FreshRSS")
        print(f"   Visit http://localhost:8081 to manage your feeds")
        print(f"   The system will start scoring articles in the next refresh cycle")
    else:
        print(f"\n⚠️  No feeds were imported. Please check your FreshRSS installation")

if __name__ == "__main__":
    main()