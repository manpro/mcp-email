#!/usr/bin/env python3
"""
Import Extended Cryptocurrency RSS feeds into RSS Intelligence Dashboard
Adds additional crypto sources beyond the existing ones
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

# Extended Cryptocurrency Feeds - sources not in the existing setup
EXTENDED_CRYPTO_FEEDS = {
    "Major Crypto News": [
        {
            "url": "https://cryptoslate.com/feed",
            "title": "CryptoSlate",
            "description": "Breaking news, analysis, and research on cryptocurrencies",
            "category": "Cryptocurrency",
            "priority": 9
        },
        {
            "url": "https://cryptopotato.com/feed",
            "title": "CryptoPotato",
            "description": "Cryptocurrency news, prices, charts and analysis",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://cryptonews.com/news/feed",
            "title": "Cryptonews.com",
            "description": "Daily crypto news and insights",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://u.today/rss",
            "title": "U.Today",
            "description": "Latest cryptocurrency news",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://www.newsbtc.com/feed",
            "title": "NewsBTC",
            "description": "Bitcoin news, price analysis, and crypto insights",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://ambcrypto.com/feed",
            "title": "AMBCrypto",
            "description": "Cryptocurrency and blockchain news",
            "category": "Cryptocurrency",
            "priority": 7
        },
        {
            "url": "https://blockonomi.com/feed",
            "title": "Blockonomi",
            "description": "Cryptocurrency news, guides and research",
            "category": "Cryptocurrency",
            "priority": 7
        },
        {
            "url": "https://dailyhodl.com/feed",
            "title": "The Daily Hodl",
            "description": "Cryptocurrency and blockchain news",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://www.coinjournal.net/feed",
            "title": "Coin Journal",
            "description": "Digital currency news and analysis",
            "category": "Cryptocurrency",
            "priority": 7
        },
        {
            "url": "https://coinmarketcap.com/alexandria/rss",
            "title": "CoinMarketCap Alexandria",
            "description": "Educational crypto content from CoinMarketCap",
            "category": "Cryptocurrency",
            "priority": 8
        }
    ],
    "DeFi and Web3": [
        {
            "url": "https://defi.org/rss.xml",
            "title": "DeFi.org",
            "description": "Decentralized finance news and updates",
            "category": "DeFi",
            "priority": 8
        },
        {
            "url": "https://defipulse.com/blog/feed",
            "title": "DeFi Pulse",
            "description": "DeFi analytics and insights",
            "category": "DeFi",
            "priority": 8
        },
        {
            "url": "https://thedefiant.io/feed",
            "title": "The Defiant (Extended)",
            "description": "DeFi news and analysis",
            "category": "DeFi",
            "priority": 9
        },
        {
            "url": "https://www.bankless.com/rss",
            "title": "Bankless",
            "description": "Guide to crypto finance and Web3",
            "category": "DeFi",
            "priority": 9
        },
        {
            "url": "https://finematics.com/feed",
            "title": "Finematics",
            "description": "DeFi education and explanations",
            "category": "DeFi",
            "priority": 7
        },
        {
            "url": "https://newsletter.thedefiant.io/feed",
            "title": "The Defiant Newsletter",
            "description": "Daily DeFi newsletter",
            "category": "DeFi",
            "priority": 8
        }
    ],
    "Blockchain Technology": [
        {
            "url": "https://www.blockchain.com/blog/feed",
            "title": "Blockchain.com Blog",
            "description": "Blockchain technology insights",
            "category": "Blockchain",
            "priority": 8
        },
        {
            "url": "https://blog.chain.link/feed",
            "title": "Chainlink Blog",
            "description": "Oracle network and smart contract updates",
            "category": "Blockchain",
            "priority": 8
        },
        {
            "url": "https://medium.com/feed/@consensys",
            "title": "ConsenSys Blog",
            "description": "Ethereum ecosystem development",
            "category": "Blockchain",
            "priority": 8
        },
        {
            "url": "https://polkadot.network/blog/feed",
            "title": "Polkadot Blog",
            "description": "Polkadot network updates",
            "category": "Blockchain",
            "priority": 7
        },
        {
            "url": "https://blog.cosmos.network/feed",
            "title": "Cosmos Blog",
            "description": "Cosmos ecosystem updates",
            "category": "Blockchain",
            "priority": 7
        },
        {
            "url": "https://near.org/blog/feed",
            "title": "NEAR Protocol Blog",
            "description": "NEAR blockchain updates",
            "category": "Blockchain",
            "priority": 7
        },
        {
            "url": "https://solana.com/news/feed",
            "title": "Solana News",
            "description": "Solana blockchain updates",
            "category": "Blockchain",
            "priority": 8
        },
        {
            "url": "https://www.avax.network/blog/feed",
            "title": "Avalanche Blog",
            "description": "Avalanche blockchain news",
            "category": "Blockchain",
            "priority": 7
        },
        {
            "url": "https://www.cardano.org/feed",
            "title": "Cardano Foundation",
            "description": "Cardano blockchain updates",
            "category": "Blockchain",
            "priority": 7
        }
    ],
    "Trading and Markets": [
        {
            "url": "https://www.tradingview.com/feed",
            "title": "TradingView Ideas",
            "description": "Crypto trading ideas and analysis",
            "category": "Crypto Trading",
            "priority": 7
        },
        {
            "url": "https://cryptopanic.com/news/rss",
            "title": "CryptoPanic",
            "description": "Aggregated crypto news affecting markets",
            "category": "Crypto Trading",
            "priority": 8
        },
        {
            "url": "https://messari.io/rss",
            "title": "Messari",
            "description": "Professional crypto research and data",
            "category": "Crypto Trading",
            "priority": 9
        },
        {
            "url": "https://glassnode.com/insights/feed",
            "title": "Glassnode Insights",
            "description": "On-chain crypto analytics",
            "category": "Crypto Trading",
            "priority": 8
        },
        {
            "url": "https://cryptoquant.com/feed",
            "title": "CryptoQuant",
            "description": "On-chain and market data analysis",
            "category": "Crypto Trading",
            "priority": 8
        },
        {
            "url": "https://santiment.net/feed",
            "title": "Santiment",
            "description": "Crypto market behavior analysis",
            "category": "Crypto Trading",
            "priority": 7
        }
    ],
    "NFT and Metaverse": [
        {
            "url": "https://nftnow.com/feed",
            "title": "nft now",
            "description": "NFT news and culture",
            "category": "NFT",
            "priority": 7
        },
        {
            "url": "https://www.nftculture.com/feed",
            "title": "NFT Culture",
            "description": "NFT news and market updates",
            "category": "NFT",
            "priority": 6
        },
        {
            "url": "https://nftevening.com/feed",
            "title": "NFT Evening",
            "description": "Daily NFT news",
            "category": "NFT",
            "priority": 6
        },
        {
            "url": "https://www.playtoearn.online/feed",
            "title": "PlayToEarn",
            "description": "Blockchain gaming news",
            "category": "NFT",
            "priority": 6
        }
    ],
    "Regulation and Policy": [
        {
            "url": "https://www.coindesk.com/policy/feed",
            "title": "CoinDesk Policy",
            "description": "Crypto regulation and policy news",
            "category": "Crypto Regulation",
            "priority": 8
        },
        {
            "url": "https://www.theblockcrypto.com/rss/policy",
            "title": "The Block Policy",
            "description": "Regulatory developments in crypto",
            "category": "Crypto Regulation",
            "priority": 8
        },
        {
            "url": "https://www.forbes.com/crypto-blockchain/feed",
            "title": "Forbes Crypto",
            "description": "Crypto news from Forbes",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://www.bloomberg.com/crypto/feed",
            "title": "Bloomberg Crypto",
            "description": "Professional crypto market coverage",
            "category": "Cryptocurrency",
            "priority": 9
        }
    ],
    "Layer 2 and Scaling": [
        {
            "url": "https://l2beat.com/feed.xml",
            "title": "L2Beat",
            "description": "Layer 2 analytics and updates",
            "category": "Blockchain",
            "priority": 8
        },
        {
            "url": "https://blog.polygon.technology/feed",
            "title": "Polygon Blog",
            "description": "Polygon network updates",
            "category": "Blockchain",
            "priority": 8
        },
        {
            "url": "https://medium.com/feed/arbitrum",
            "title": "Arbitrum Blog",
            "description": "Arbitrum layer 2 updates",
            "category": "Blockchain",
            "priority": 7
        },
        {
            "url": "https://optimism.mirror.xyz/feed/atom",
            "title": "Optimism Blog",
            "description": "Optimism L2 updates",
            "category": "Blockchain",
            "priority": 7
        }
    ],
    "Mining and Infrastructure": [
        {
            "url": "https://bitcoinmagazine.com/feed",
            "title": "Bitcoin Magazine",
            "description": "Bitcoin news and deep analysis",
            "category": "Cryptocurrency",
            "priority": 8
        },
        {
            "url": "https://www.coinwarz.com/news/feed",
            "title": "CoinWarz",
            "description": "Mining profitability and news",
            "category": "Crypto Mining",
            "priority": 6
        },
        {
            "url": "https://hashrateindex.com/feed",
            "title": "Hashrate Index",
            "description": "Bitcoin mining analytics",
            "category": "Crypto Mining",
            "priority": 7
        }
    ],
    "Regional Crypto News": [
        {
            "url": "https://cointelegraph.com/rss/tag/asia",
            "title": "Cointelegraph Asia",
            "description": "Asian crypto market news",
            "category": "Cryptocurrency",
            "priority": 7
        },
        {
            "url": "https://www.coindesk.com/consensus/feed",
            "title": "CoinDesk Consensus",
            "description": "Major crypto conference updates",
            "category": "Cryptocurrency",
            "priority": 7
        },
        {
            "url": "https://cryptoslate.com/press-releases/feed",
            "title": "CryptoSlate Press Releases",
            "description": "Official crypto project announcements",
            "category": "Cryptocurrency",
            "priority": 6
        }
    ]
}

def create_db_connection():
    """Create database connection"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def feed_exists(session, url):
    """Check if feed already exists in database"""
    result = session.execute(
        text("SELECT COUNT(*) FROM ai_feed WHERE url = :url"),
        {"url": url}
    )
    return result.scalar() > 0

def ensure_category(session, category_name):
    """Ensure category exists and return its ID"""
    result = session.execute(
        text("SELECT id FROM ai_category WHERE name = :name"),
        {"name": category_name}
    )
    category_id = result.scalar()
    
    if not category_id:
        # Create category
        result = session.execute(
            text("""
                INSERT INTO ai_category (name)
                VALUES (:name)
                RETURNING id
            """),
            {"name": category_name}
        )
        session.commit()
        category_id = result.scalar()
    
    return category_id

def import_feeds():
    """Import all extended crypto feeds into the database"""
    session = create_db_connection()
    
    total_feeds = 0
    imported_feeds = 0
    skipped_feeds = 0
    failed_feeds = []
    
    try:
        print("\n" + "="*70)
        print("EXTENDED CRYPTOCURRENCY FEEDS IMPORTER")
        print("="*70)
        
        for category_name, feeds in EXTENDED_CRYPTO_FEEDS.items():
            print(f"\n📁 {category_name}")
            print("-" * 50)
            
            for feed in feeds:
                total_feeds += 1
                
                if feed_exists(session, feed["url"]):
                    print(f"  ⏭️  Skipped (exists): {feed['title']}")
                    skipped_feeds += 1
                    continue
                
                try:
                    # Ensure category exists
                    category_id = ensure_category(session, feed["category"])
                    
                    # Insert feed
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
                            "kind": 0,  # RSS feed
                            "lastUpdate": int(time.time()),
                            "error": 0,
                            "ttl": 3600  # 1 hour
                        }
                    )
                    session.commit()
                    imported_feeds += 1
                    print(f"  ✅ Imported: {feed['title']}")
                    
                except Exception as e:
                    session.rollback()
                    print(f"  ❌ Failed: {feed['title']} - {str(e)}")
                    failed_feeds.append(feed['title'])
        
        # Print summary
        print("\n" + "="*70)
        print("📊 IMPORT SUMMARY")
        print("="*70)
        print(f"Total feeds processed: {total_feeds}")
        print(f"✅ Successfully imported: {imported_feeds}")
        print(f"⏭️  Skipped (duplicates): {skipped_feeds}")
        print(f"❌ Failed: {len(failed_feeds)}")
        
        if failed_feeds:
            print("\nFailed feeds:")
            for feed_name in failed_feeds:
                print(f"  - {feed_name}")
        
        if imported_feeds > 0:
            print(f"\n🎉 SUCCESS! Added {imported_feeds} new cryptocurrency feeds!")
            print("\n📋 Next steps:")
            print("  1. RSS poller will fetch articles on next run")
            print("  2. High-scoring crypto articles will be extracted")
            print("  3. Content will be indexed in Weaviate for AI search")
            
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        session.rollback()
        
    finally:
        session.close()

def list_crypto_feeds():
    """List all cryptocurrency-related feeds"""
    session = create_db_connection()
    
    try:
        result = session.execute(
            text("""
                SELECT c.name as category, f.name as feed_name, f.url, f.priority
                FROM ai_feed f
                LEFT JOIN ai_category c ON f.category = c.id
                WHERE c.name IN ('Cryptocurrency', 'Blockchain', 'DeFi', 'NFT', 
                                 'Crypto Trading', 'Crypto Regulation', 'Crypto Mining')
                ORDER BY c.name, f.priority DESC, f.name
            """)
        )
        
        print("\n" + "="*70)
        print("📰 CURRENT CRYPTOCURRENCY FEEDS")
        print("="*70)
        
        current_category = None
        category_counts = {}
        
        for row in result:
            if row.category != current_category:
                current_category = row.category
                if current_category not in category_counts:
                    category_counts[current_category] = 0
                print(f"\n🔹 {current_category}:")
                print("-" * 40)
            
            category_counts[current_category] += 1
            priority_stars = "⭐" * (row.priority // 2) if row.priority else ""
            print(f"  [{row.priority}] {priority_stars} {row.feed_name}")
            print(f"       {row.url[:60]}...")
        
        print("\n" + "-"*70)
        print("📊 Summary by Category:")
        total = 0
        for cat, count in sorted(category_counts.items()):
            print(f"  {cat}: {count} feeds")
            total += count
        print(f"\n  TOTAL CRYPTO FEEDS: {total}")
        
    finally:
        session.close()

if __name__ == "__main__":
    import sys
    
    print("\n🚀 RSS INTELLIGENCE - EXTENDED CRYPTOCURRENCY FEEDS")
    print("Expanding crypto coverage with additional sources")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        # Just list current feeds
        list_crypto_feeds()
    else:
        # Show current status
        print("\n📍 Current Status:")
        list_crypto_feeds()
        
        # Import new feeds
        print("\n🔄 Starting import of extended cryptocurrency feeds...")
        import_feeds()
        
        # Show updated status
        print("\n✅ Updated Status:")
        list_crypto_feeds()