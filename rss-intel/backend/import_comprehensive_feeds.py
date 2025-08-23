#!/usr/bin/env python3
"""
Import comprehensive RSS feeds into RSS Intelligence Dashboard
Categories: AI/ML, Blockchain/Crypto, Fintech, Emerging Tech
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rss:changeme@localhost:5432/rssintel")

# Comprehensive feed categories and sources
COMPREHENSIVE_FEEDS = {
    "AI & Machine Learning": {
        "Major Companies": [
            {
                "url": "https://openai.com/blog/rss/",
                "title": "OpenAI Blog",
                "description": "Model releases, research updates, AI safety discussions",
                "category": "AI News",
                "priority": 10
            },
            {
                "url": "https://ai.googleblog.com/feeds/posts/default",
                "title": "Google AI Blog",
                "description": "TensorFlow news, AI research, enterprise applications",
                "category": "AI News",
                "priority": 10
            },
            {
                "url": "https://blogs.microsoft.com/ai/feed/",
                "title": "Microsoft AI Blog",
                "description": "Azure AI features, enterprise AI case studies",
                "category": "AI News",
                "priority": 9
            },
            {
                "url": "https://huggingface.co/blog/feed.xml",
                "title": "Hugging Face Blog",
                "description": "Updates from the popular AI model hub",
                "category": "AI News",
                "priority": 9
            },
            {
                "url": "https://blog.tensorflow.org/feeds/posts/default",
                "title": "TensorFlow Blog",
                "description": "TensorFlow updates, tutorials, and community news",
                "category": "AI Tools",
                "priority": 8
            }
        ],
        "Research": [
            {
                "url": "https://rss.arxiv.org/rss/cs.LG",
                "title": "arXiv - Machine Learning",
                "description": "Latest machine learning papers from arXiv",
                "category": "AI Research",
                "priority": 9
            },
            {
                "url": "https://rss.arxiv.org/rss/cs.AI",
                "title": "arXiv - Artificial Intelligence",
                "description": "Latest AI papers from arXiv",
                "category": "AI Research",
                "priority": 9
            },
            {
                "url": "https://rss.arxiv.org/rss/cs.CV",
                "title": "arXiv - Computer Vision",
                "description": "Computer vision research papers",
                "category": "AI Research",
                "priority": 8
            },
            {
                "url": "https://www.nature.com/natmachintell.rss",
                "title": "Nature Machine Intelligence",
                "description": "Nature's dedicated AI/ML journal",
                "category": "AI Research",
                "priority": 10
            },
            {
                "url": "https://news.mit.edu/topic/mitmachine-learning-rss.xml",
                "title": "MIT News - Machine Learning",
                "description": "Machine learning news from MIT",
                "category": "AI Research",
                "priority": 8
            }
        ],
        "Media": [
            {
                "url": "https://www.technologyreview.com/feed/",
                "title": "MIT Technology Review",
                "description": "In-depth technology analysis and AI ethics",
                "category": "Tech Media",
                "priority": 9
            },
            {
                "url": "https://machinelearningmastery.com/blog/feed",
                "title": "Machine Learning Mastery",
                "description": "Hands-on Python/R tutorials and code snippets",
                "category": "AI Education",
                "priority": 7
            }
        ]
    },
    "Blockchain & Crypto": {
        "Major News": [
            {
                "url": "https://cointelegraph.com/rss",
                "title": "Cointelegraph",
                "description": "Bitcoin, Ethereum, Blockchain, Altcoin news and analysis",
                "category": "Crypto News",
                "priority": 9
            },
            {
                "url": "https://theblock.co/rss",
                "title": "The Block",
                "description": "Institutional crypto news and market analysis",
                "category": "Crypto News",
                "priority": 9
            },
            {
                "url": "https://thedefiant.io/api/feed",
                "title": "The Defiant",
                "description": "DeFi, Ethereum, and Web3 news",
                "category": "DeFi News",
                "priority": 8
            },
            {
                "url": "https://bitcoinist.com/feed",
                "title": "Bitcoinist",
                "description": "Bitcoin news portal with guides and analysis",
                "category": "Crypto News",
                "priority": 7
            },
            {
                "url": "https://crypto.news/feed",
                "title": "Crypto News",
                "description": "Latest updates on Bitcoin, Ethereum, and Ripple",
                "category": "Crypto News",
                "priority": 8
            }
        ],
        "Technical": [
            {
                "url": "https://blog.ethereum.org/en/feed.xml",
                "title": "Ethereum Foundation Blog",
                "description": "Official Ethereum Foundation updates",
                "category": "Blockchain Tech",
                "priority": 9
            },
            {
                "url": "https://ethresear.ch/latest.rss",
                "title": "Ethereum Research Forum",
                "description": "Ethereum research discussions",
                "category": "Blockchain Tech",
                "priority": 8
            },
            {
                "url": "https://bitcoincore.org/en/rss.xml",
                "title": "Bitcoin Core Blog",
                "description": "Bitcoin Core development updates",
                "category": "Blockchain Tech",
                "priority": 7
            },
            {
                "url": "https://eprint.iacr.org/rss/",
                "title": "IACR Cryptology ePrint Archive",
                "description": "Latest cryptography research papers",
                "category": "Cryptography",
                "priority": 8
            }
        ],
        "DeFi": [
            {
                "url": "https://coinscipher.com/feed",
                "title": "CoinsCipher",
                "description": "DeFi, NFTs, GameFi, and blockchain analysis",
                "category": "DeFi News",
                "priority": 7
            },
            {
                "url": "https://crypto-reporter.com/feed",
                "title": "Crypto Reporter",
                "description": "Cryptocurrencies, NFTs, DeFi, GameFi magazine",
                "category": "DeFi News",
                "priority": 6
            }
        ]
    },
    "Fintech": {
        "Global": [
            {
                "url": "https://www.finextra.com/rss/rss.aspx",
                "title": "Finextra Research",
                "description": "Latest fintech news, analysis, interviews by experts",
                "category": "Fintech News",
                "priority": 10
            },
            {
                "url": "https://www.fintechweekly.com/feed",
                "title": "FinTech Weekly",
                "description": "News and articles on fintech, finance, blockchain",
                "category": "Fintech News",
                "priority": 8
            },
            {
                "url": "https://fintech.global/feed/",
                "title": "FinTech Global",
                "description": "Leading provider of FinTech information services",
                "category": "Fintech News",
                "priority": 9
            },
            {
                "url": "https://finovate.com/feed",
                "title": "Finovate",
                "description": "Financial technology innovations and events",
                "category": "Fintech Innovation",
                "priority": 8
            }
        ],
        "Regional": [
            {
                "url": "https://fintechnews.ch/feed",
                "title": "Fintech News Switzerland",
                "description": "Swiss and global fintech insights since 2014",
                "category": "Fintech Regional",
                "priority": 6
            },
            {
                "url": "https://fintechnews.am/feed",
                "title": "Fintech News America",
                "description": "American fintech news and analysis",
                "category": "Fintech Regional",
                "priority": 6
            }
        ],
        "Payments": [
            {
                "url": "https://www.paymentscardsandmobile.com/feed/",
                "title": "Payments Cards & Mobile",
                "description": "Global payments, contactless, m-banking news",
                "category": "Payment Tech",
                "priority": 7
            }
        ]
    },
    "Emerging Technology": {
        "General Tech": [
            {
                "url": "https://www.wired.com/feed/rss",
                "title": "Wired",
                "description": "Technology culture and future tech trends",
                "category": "Tech Culture",
                "priority": 8
            },
            {
                "url": "https://spectrum.ieee.org/rss/fulltext",
                "title": "IEEE Spectrum",
                "description": "Engineering and technology perspectives",
                "category": "Engineering",
                "priority": 8
            },
            {
                "url": "https://arstechnica.com/rss/",
                "title": "Ars Technica",
                "description": "Deep technical analysis and science news",
                "category": "Tech Analysis",
                "priority": 8
            },
            {
                "url": "https://www.computerweekly.com/rss",
                "title": "Computer Weekly",
                "description": "Latest information technology news and analysis",
                "category": "Enterprise Tech",
                "priority": 7
            }
        ],
        "Science": [
            {
                "url": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
                "title": "ScienceDaily - AI",
                "description": "AI news and research summaries",
                "category": "Tech Science",
                "priority": 7
            },
            {
                "url": "https://www.nature.com/subjects/computer-science.rss",
                "title": "Nature - Computer Science",
                "description": "Computer science articles from Nature",
                "category": "Tech Science",
                "priority": 8
            }
        ],
        "Quantum & Emerging": [
            {
                "url": "https://www.nature.com/subjects/quantum-physics.rss",
                "title": "Nature - Quantum Physics",
                "description": "Latest quantum physics research",
                "category": "Quantum Tech",
                "priority": 6
            },
            {
                "url": "https://www.ibm.com/blogs/research/feed/",
                "title": "IBM Research Blog",
                "description": "IBM's research in AI, quantum, and emerging tech",
                "category": "Research",
                "priority": 7
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
        for main_category, subcategories in COMPREHENSIVE_FEEDS.items():
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
                                """),
                                {"name": feed["category"]}
                            )
                            session.commit()
                            cat_result = session.execute(
                                text("SELECT id FROM ai_category WHERE name = :name"),
                                {"name": feed["category"]}
                            )
                            category_id = cat_result.scalar()
                        
                        # Insert feed into ai_feed table
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
    print("RSS Intelligence Dashboard - Comprehensive Feed Importer")
    print("Categories: AI/ML, Blockchain/Crypto, Fintech, Emerging Tech")
    print("=" * 60)
    
    # Show current status
    list_current_feeds()
    
    # Import new feeds
    print("\nStarting import of comprehensive feeds...")
    import_feeds()
    
    # Show updated status
    print("\nUpdated feed status:")
    list_current_feeds()