#!/usr/bin/env python3
"""
Import AI Research and Blockchain RSS feeds into RSS Intelligence Dashboard
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rss_user:rss_password@localhost:5432/rss_intel")

# Feed categories and sources
AI_BLOCKCHAIN_FEEDS = {
    "AI Research": {
        "arXiv": [
            {
                "url": "https://rss.arxiv.org/rss/cs.LG",
                "title": "arXiv - Computer Science: Machine Learning",
                "description": "Latest machine learning papers from arXiv",
                "category": "AI Research",
                "priority": 10
            },
            {
                "url": "https://rss.arxiv.org/rss/cs.AI",
                "title": "arXiv - Computer Science: Artificial Intelligence",
                "description": "Latest AI papers from arXiv",
                "category": "AI Research",
                "priority": 10
            },
            {
                "url": "https://rss.arxiv.org/rss/cs.CL",
                "title": "arXiv - Computer Science: Computation and Language",
                "description": "Latest NLP and computational linguistics papers",
                "category": "AI Research",
                "priority": 9
            },
            {
                "url": "https://rss.arxiv.org/rss/cs.CV",
                "title": "arXiv - Computer Science: Computer Vision",
                "description": "Latest computer vision papers from arXiv",
                "category": "AI Research",
                "priority": 9
            },
            {
                "url": "https://rss.arxiv.org/rss/stat.ML",
                "title": "arXiv - Statistics: Machine Learning",
                "description": "Statistical machine learning papers",
                "category": "AI Research",
                "priority": 8
            },
            {
                "url": "https://rss.arxiv.org/rss/cs.AI+cs.LG+stat.ML",
                "title": "arXiv - Combined AI/ML/Stats",
                "description": "Combined feed for AI, ML, and Statistics",
                "category": "AI Research",
                "priority": 10
            }
        ],
        "Journals": [
            {
                "url": "https://www.jmlr.org/jmlr.xml",
                "title": "Journal of Machine Learning Research (JMLR)",
                "description": "Peer-reviewed machine learning research",
                "category": "AI Journals",
                "priority": 10
            },
            {
                "url": "https://www.nature.com/subjects/machine-learning.rss",
                "title": "Nature - Machine Learning",
                "description": "Machine learning articles from Nature",
                "category": "AI Journals",
                "priority": 9
            },
            {
                "url": "https://www.nature.com/natmachintell.rss",
                "title": "Nature Machine Intelligence",
                "description": "Nature's dedicated AI/ML journal",
                "category": "AI Journals",
                "priority": 10
            }
        ],
        "News": [
            {
                "url": "https://news.mit.edu/topic/mitmachine-learning-rss.xml",
                "title": "MIT News - Machine Learning",
                "description": "Machine learning news from MIT",
                "category": "AI News",
                "priority": 8
            },
            {
                "url": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
                "title": "ScienceDaily - Artificial Intelligence",
                "description": "AI news and research summaries",
                "category": "AI News",
                "priority": 7
            }
        ]
    },
    "Blockchain": {
        "Cryptography": [
            {
                "url": "https://eprint.iacr.org/rss/",
                "title": "IACR Cryptology ePrint Archive",
                "description": "Latest cryptography research papers",
                "category": "Cryptography",
                "priority": 9
            }
        ],
        "Ethereum": [
            {
                "url": "https://blog.ethereum.org/en/feed.xml",
                "title": "Ethereum Foundation Blog",
                "description": "Official Ethereum Foundation updates",
                "category": "Blockchain",
                "priority": 8
            },
            {
                "url": "https://ethresear.ch/latest.rss",
                "title": "Ethereum Research Forum",
                "description": "Ethereum research discussions",
                "category": "Blockchain",
                "priority": 8
            }
        ],
        "Bitcoin": [
            {
                "url": "https://bitcoincore.org/en/rss.xml",
                "title": "Bitcoin Core Blog",
                "description": "Bitcoin Core development updates",
                "category": "Blockchain",
                "priority": 7
            },
            {
                "url": "https://www.mail-archive.com/bitcoin-dev@lists.linuxfoundation.org/maillist.xml",
                "title": "Bitcoin-dev Mailing List",
                "description": "Bitcoin development discussions",
                "category": "Blockchain",
                "priority": 6
            }
        ]
    }
}

def create_db_connection():
    """Create database connection"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def feed_exists(session, url):
    """Check if feed already exists in database"""
    # Check in ai_feed table (used by RSS Intelligence Dashboard)
    result = session.execute(
        text("SELECT COUNT(*) FROM ai_feed WHERE url = :url"),
        {"url": url}
    )
    return result.scalar() > 0

def import_feeds():
    """Import all feeds into the database"""
    session = create_db_connection()
    
    total_feeds = 0
    imported_feeds = 0
    skipped_feeds = 0
    
    try:
        for main_category, subcategories in AI_BLOCKCHAIN_FEEDS.items():
            print(f"\n{'='*60}")
            print(f"Processing {main_category} feeds...")
            print(f"{'='*60}")
            
            for subcategory, feeds in subcategories.items():
                print(f"\n{subcategory}:")
                print("-" * 40)
                
                for feed in feeds:
                    total_feeds += 1
                    
                    if feed_exists(session, feed["url"]):
                        print(f"  ⏭️  Skipping (already exists): {feed['title']}")
                        skipped_feeds += 1
                        continue
                    
                    try:
                        # First, check if category exists, if not create it
                        cat_result = session.execute(
                            text("SELECT id FROM ai_category WHERE name = :name"),
                            {"name": feed["category"]}
                        )
                        category_id = cat_result.scalar()
                        
                        if not category_id:
                            # Create category
                            session.execute(
                                text("""
                                    INSERT INTO ai_category (name)
                                    VALUES (:name)
                                    RETURNING id
                                """),
                                {"name": feed["category"]}
                            )
                            cat_result = session.execute(
                                text("SELECT id FROM ai_category WHERE name = :name"),
                                {"name": feed["category"]}
                            )
                            category_id = cat_result.scalar()
                        
                        # Insert feed into ai_feed table (using FreshRSS schema)
                        # Note: Column names are case-sensitive in PostgreSQL
                        import time
                        session.execute(
                            text("""
                                INSERT INTO ai_feed (url, name, description, category, website, priority, kind, "lastUpdate", error, ttl)
                                VALUES (:url, :name, :description, :category, :website, :priority, :kind, :lastUpdate, :error, :ttl)
                            """),
                            {
                                "url": feed["url"],
                                "name": feed["title"],
                                "description": feed["description"],
                                "category": category_id,
                                "website": feed["url"].split('/')[2] if '//' in feed["url"] else feed["url"],
                                "priority": feed["priority"],
                                "kind": 0,  # RSS feed type
                                "lastUpdate": int(time.time()),
                                "error": 0,  # No error
                                "ttl": 3600  # 1 hour TTL
                            }
                        )
                        session.commit()
                        imported_feeds += 1
                        print(f"  ✅ Imported: {feed['title']}")
                        
                    except Exception as e:
                        session.rollback()
                        print(f"  ❌ Error importing {feed['title']}: {str(e)}")
        
        print(f"\n{'='*60}")
        print("Import Summary:")
        print(f"{'='*60}")
        print(f"Total feeds processed: {total_feeds}")
        print(f"Successfully imported: {imported_feeds}")
        print(f"Skipped (duplicates): {skipped_feeds}")
        print(f"Failed: {total_feeds - imported_feeds - skipped_feeds}")
        
        if imported_feeds > 0:
            print(f"\n✨ Success! {imported_feeds} new feeds added to RSS Intelligence Dashboard")
            print("\nNext steps:")
            print("1. The RSS poller will fetch articles from these feeds on the next run")
            print("2. High-scoring articles will be automatically queued for content extraction")
            print("3. You can manually trigger polling via the API or wait for scheduled runs")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        session.rollback()
        
    finally:
        session.close()

def list_current_feeds():
    """List all current feeds in the database"""
    session = create_db_connection()
    
    try:
        result = session.execute(
            text("""
                SELECT c.name as category, COUNT(f.id) as count
                FROM ai_feed f
                LEFT JOIN ai_category c ON f.category = c.id
                GROUP BY c.name 
                ORDER BY c.name
            """)
        )
        
        print("\nCurrent RSS Feeds in Database:")
        print("=" * 60)
        
        total = 0
        for row in result:
            category_name = row.category if row.category else "Uncategorized"
            print(f"{category_name}: {row.count} feeds")
            total += row.count
        
        print("-" * 60)
        print(f"Total: {total} feeds")
        
    finally:
        session.close()

if __name__ == "__main__":
    print("RSS Intelligence Dashboard - AI & Blockchain Feed Importer")
    print("=" * 60)
    
    # Show current status
    list_current_feeds()
    
    # Import new feeds
    print("\nStarting import of AI Research and Blockchain feeds...")
    import_feeds()
    
    # Show updated status
    print("\nUpdated feed status:")
    list_current_feeds()