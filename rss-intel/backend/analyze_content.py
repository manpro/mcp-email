#!/usr/bin/env python3
"""
Analyze content patterns in articles to understand what we're working with
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

def analyze_content_patterns():
    """Analyze content patterns to understand the articles"""
    db = SessionLocal()
    
    try:
        # Get sample articles with title and content
        articles = db.execute(text("""
            SELECT id, title, content, url, source, published_at
            FROM articles 
            WHERE title IS NOT NULL
            ORDER BY published_at DESC
            LIMIT 100
        """)).fetchall()
        
        print(f"Analyzing content patterns in {len(articles)} recent articles...")
        
        # Common promotional patterns to look for
        promotional_patterns = [
            r'\b(?:sponsored|advertisement|promo|deal|offer|sale|discount)\b',
            r'\b(?:buy|purchase|shop|order)\s+(?:now|today)\b',
            r'\b(?:\d+%?\s*(?:off|discount|save))\b',
            r'\b(?:free|limited|exclusive|special)\s+(?:offer|deal)\b',
            r'\b(?:click|visit|check)\s+(?:here|now|out)\b',
            r'\$\d+|\b\d+\s*kr\b',
            r'\b(?:affiliate|partner|commission)\b'
        ]
        
        pattern_matches = Counter()
        source_stats = Counter()
        content_lengths = []
        
        # Check for promotional patterns
        for article in articles:
            title = article.title or ""
            content = article.content or ""
            text = f"{title} {content}".lower()
            content_lengths.append(len(text))
            source_stats[article.source or "unknown"] += 1
            
            for pattern in promotional_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    pattern_matches[pattern] += len(matches)
                    print(f"Found pattern '{pattern}' in: {title[:60]}...")
        
        print(f"\n=== CONTENT ANALYSIS RESULTS ===")
        print(f"Articles analyzed: {len(articles)}")
        print(f"Average content length: {sum(content_lengths)/len(content_lengths):.0f} characters")
        
        print(f"\n=== TOP SOURCES ===")
        for source, count in source_stats.most_common(10):
            print(f"{source}: {count} articles")
        
        print(f"\n=== PROMOTIONAL PATTERNS FOUND ===")
        if pattern_matches:
            for pattern, count in pattern_matches.most_common():
                print(f"'{pattern}': {count} matches")
        else:
            print("No promotional patterns detected!")
        
        # Check for some specific high-quality content indicators
        quality_indicators = [
            r'\b(?:research|study|analysis|report)\b',
            r'\b(?:scientists?|researchers?|experts?)\b', 
            r'\b(?:according to|published in|peer.reviewed)\b',
            r'\b(?:university|institute|journal)\b'
        ]
        
        quality_matches = Counter()
        for article in articles:
            title = article.title or ""
            content = article.content or ""
            text = f"{title} {content}".lower()
            for pattern in quality_indicators:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    quality_matches[pattern] += len(matches)
        
        print(f"\n=== QUALITY INDICATORS FOUND ===")
        if quality_matches:
            for pattern, count in quality_matches.most_common():
                print(f"'{pattern}': {count} matches")
        else:
            print("No specific quality indicators found")
            
        # Show a few example titles
        print(f"\n=== SAMPLE ARTICLE TITLES ===")
        for i, article in enumerate(articles[:10]):
            source = article.source or "unknown"
            title = article.title or "No title"
            print(f"{i+1}. [{source}] {title}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    analyze_content_patterns()