#!/usr/bin/env python3
"""
Simple analysis of article content
"""
import os
import sys
import re
from collections import Counter

# Add the app directory to Python path
sys.path.append('/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rss:changeme@postgres:5432/rssintel")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def simple_content_analysis():
    """Simple content analysis"""
    db = SessionLocal()
    
    try:
        # Get sample articles
        articles = db.execute(text("""
            SELECT id, title, source, published_at
            FROM articles 
            WHERE title IS NOT NULL
            ORDER BY published_at DESC
            LIMIT 50
        """)).fetchall()
        
        print(f"Analyzing {len(articles)} recent articles...")
        
        source_stats = Counter()
        
        # Basic stats
        for article in articles:
            source = getattr(article, 'source', None) or "unknown"
            source_stats[source] += 1
        
        print(f"\n=== SOURCES ===")
        for source, count in source_stats.most_common(10):
            print(f"{source}: {count} articles")
        
        # Sample titles
        print(f"\n=== SAMPLE TITLES ===")
        for i, article in enumerate(articles[:15]):
            source = getattr(article, 'source', None) or "unknown"
            title = getattr(article, 'title', None) or "No title"
            print(f"{i+1}. [{source}] {title}")
        
        # Look for obvious promotional keywords
        promo_count = 0
        for article in articles:
            title = getattr(article, 'title', None) or ""
            title_lower = title.lower()
            
            promo_keywords = ['sponsored', 'advertisement', 'buy now', 'sale', 'discount', 
                             'offer', 'deal', 'free', 'promo', 'affiliate']
            
            for keyword in promo_keywords:
                if keyword in title_lower:
                    promo_count += 1
                    print(f"Promotional keyword '{keyword}' found in: {title}")
                    break
        
        print(f"\n=== RESULTS ===")
        print(f"Total articles: {len(articles)}")
        print(f"Articles with promotional keywords: {promo_count}")
        print(f"Clean articles: {len(articles) - promo_count} ({(len(articles) - promo_count)/len(articles)*100:.1f}%)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    simple_content_analysis()