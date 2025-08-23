#!/usr/bin/env python3
"""
Fix problematic RSS feed URLs and update the database
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rss:changeme@localhost:5432/rssintel")

# URLs to fix
URL_FIXES = {
    # Google AI Blog correct URL
    "https://ai.googleblog.com/feeds/posts/default": "https://blog.google/technology/ai/rss/",
    
    # The Block correct URL
    "https://theblock.co/rss": "https://www.theblock.co/rss.xml",
    
    # FinTech Weekly correct URL  
    "https://www.fintechweekly.com/feed": "https://fintechweekly.com/feed",
    
    # OpenAI (they may have blocked RSS, remove it)
    "https://openai.com/blog/rss/": None,  # Remove this one
    
    # Finextra - try alternative URL
    "https://www.finextra.com/rss/rss.aspx": "https://www.finextra.com/rss/headlines.aspx",
    
    # Computer Weekly - try alternative
    "https://www.computerweekly.com/rss": "https://www.computerweekly.com/rss/IT-news.xml",
    
    # IBM Research - try alternative
    "https://www.ibm.com/blogs/research/feed/": "https://research.ibm.com/blog/rss.xml"
}

def fix_feeds():
    """Fix problematic RSS feed URLs"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        for old_url, new_url in URL_FIXES.items():
            if new_url is None:
                # Remove the feed
                result = session.execute(
                    text("DELETE FROM ai_feed WHERE url = :url"),
                    {"url": old_url}
                )
                if result.rowcount > 0:
                    print(f"❌ Removed problematic feed: {old_url}")
            else:
                # Update the URL
                result = session.execute(
                    text("UPDATE ai_feed SET url = :new_url WHERE url = :old_url"),
                    {"old_url": old_url, "new_url": new_url}
                )
                if result.rowcount > 0:
                    print(f"✅ Updated: {old_url} -> {new_url}")
        
        session.commit()
        print(f"\n✨ Feed URLs have been fixed!")
        
        # Add some working feeds to replace problematic ones
        working_feeds = [
            {
                "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
                "name": "TechCrunch AI",
                "description": "AI news from TechCrunch",
                "category": "AI News"
            },
            {
                "url": "https://www.artificialintelligence-news.com/feed/",
                "name": "AI News",
                "description": "Latest AI news and analysis",
                "category": "AI News"
            },
            {
                "url": "https://decrypt.co/feed",
                "name": "Decrypt",
                "description": "Crypto and blockchain news",
                "category": "Crypto News"
            },
            {
                "url": "https://beincrypto.com/feed/",
                "name": "BeInCrypto",
                "description": "Cryptocurrency news and analysis",
                "category": "Crypto News"
            }
        ]
        
        for feed in working_feeds:
            # Check if it already exists
            existing = session.execute(
                text("SELECT COUNT(*) FROM ai_feed WHERE url = :url"),
                {"url": feed["url"]}
            ).scalar()
            
            if existing == 0:
                # Get or create category
                cat_result = session.execute(
                    text("SELECT id FROM ai_category WHERE name = :name"),
                    {"name": feed["category"]}
                )
                category_id = cat_result.scalar()
                
                if not category_id:
                    session.execute(
                        text("INSERT INTO ai_category (name) VALUES (:name)"),
                        {"name": feed["category"]}
                    )
                    session.commit()
                    cat_result = session.execute(
                        text("SELECT id FROM ai_category WHERE name = :name"),
                        {"name": feed["category"]}
                    )
                    category_id = cat_result.scalar()
                
                # Add the feed
                import time
                session.execute(
                    text("""
                        INSERT INTO ai_feed (url, name, description, category, website, priority, kind, "lastUpdate", error, ttl)
                        VALUES (:url, :name, :description, :category, :website, :priority, :kind, :lastUpdate, :error, :ttl)
                    """),
                    {
                        "url": feed["url"],
                        "name": feed["name"],
                        "description": feed["description"],
                        "category": category_id,
                        "website": feed["url"].split('/')[2],
                        "priority": 8,
                        "kind": 0,
                        "lastUpdate": int(time.time()),
                        "error": 0,
                        "ttl": 3600
                    }
                )
                print(f"✅ Added working feed: {feed['name']}")
        
        session.commit()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Fixing problematic RSS feed URLs...")
    fix_feeds()