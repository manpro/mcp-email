#!/usr/bin/env python3
"""
Force add RSS feeds to FreshRSS
"""

import httpx
import time

# FreshRSS configuration
BASE_URL = "http://localhost:8081"
USERNAME = "admin"
PASSWORD = "adminadmin"

# Priority feeds to add
FEEDS = [
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://cointelegraph.com/rss", "Cointelegraph"),
    ("https://openai.com/blog/rss.xml", "OpenAI Blog"),
    ("https://www.anthropic.com/rss.xml", "Anthropic Blog"),
    ("https://news.ycombinator.com/rss", "Hacker News"),
    ("https://www.finextra.com/rss/headlines.aspx", "Finextra"),
    ("https://www.pymnts.com/feed/", "PYMNTS"),
    ("https://stripe.com/blog/feed.rss", "Stripe Blog"),
    ("https://arstechnica.com/feed/", "Ars Technica"),
    ("https://www.theverge.com/rss/index.xml", "The Verge"),
    ("https://venturebeat.com/ai/feed/", "VentureBeat AI"),
    ("https://www.artificialintelligence-news.com/feed/", "AI News"),
    ("https://decrypt.co/feed", "Decrypt"),
    ("https://www.riksbank.se/sv/press-och-publicerat/nyheter/rss/", "Riksbanken"),
]

def main():
    print("🚀 Force adding RSS feeds to FreshRSS...")
    print("=" * 60)
    
    client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    try:
        # Get initial page to start session
        print("Starting session...")
        response = client.get(BASE_URL)
        
        # Login
        print(f"Logging in as {USERNAME}...")
        login_data = {
            "username": USERNAME,
            "password": PASSWORD,
            "_csrf": "",
        }
        
        login_url = f"{BASE_URL}/i/?c=auth&a=login"
        response = client.post(login_url, data=login_data)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return
        
        print("✅ Logged in successfully")
        
        # Add each feed
        success_count = 0
        for feed_url, title in FEEDS:
            print(f"\nAdding: {title}")
            print(f"  URL: {feed_url[:60]}...")
            
            # Try to add the feed
            add_data = {
                "url_rss": feed_url,
                "category": "1",  # Default category
            }
            
            add_url = f"{BASE_URL}/i/?c=subscription&a=add"
            
            try:
                response = client.post(add_url, data=add_data)
                if response.status_code == 200:
                    print(f"  ✅ Added successfully")
                    success_count += 1
                else:
                    print(f"  ⚠️  Response: {response.status_code}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            time.sleep(0.5)  # Be nice to the server
        
        print("\n" + "=" * 60)
        print(f"📊 Summary: {success_count}/{len(FEEDS)} feeds added")
        
        if success_count > 0:
            print("\n🔄 Now fetching articles from feeds...")
            # Try to trigger actualize via web interface
            actualize_url = f"{BASE_URL}/i/?c=feed&a=actualize&id=-1"
            response = client.get(actualize_url)
            print("✅ Actualize triggered")
            
    finally:
        client.close()
    
    print("\n✨ Done! Check http://localhost:3001 for new articles")

if __name__ == "__main__":
    main()