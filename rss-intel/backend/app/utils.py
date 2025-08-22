import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random
import yaml

from .deps import SessionLocal
from .store import ArticleStore
from .freshrss_client import FreshRSSClient
from .config import settings

def seed():
    """Seed initial data and configuration"""
    print("Seeding initial data...")
    
    # Ensure config directory exists
    config_dir = Path(settings.config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default config files if they don't exist
    configs = {
        "scoring.yml": {
            "keywords": {
                "ai": 10,
                "payments": 12,
                "visa": 15,
                "mastercard": 15,
                "crypto": 10,
                "regulation": 8,
                "fintech": 10,
                "banking": 8,
                "blockchain": 9,
                "api": 7,
                "security": 8,
                "innovation": 6,
                "digital": 5,
                "mobile": 6,
                "startup": 7
            },
            "source_weights": {
                "finextra.com": 8,
                "thepaypers.com": 6,
                "riksbank.se": 10,
                "reddit.com": 4,
                "github.com": 6,
                "techcrunch.com": 5,
                "bloomberg.com": 7
            },
            "recency": {
                "half_life_hours": 36
            },
            "thresholds": {
                "star": 80,
                "interesting": 60
            }
        },
        "watchlist.yml": {
            "entities": [
                "Klarna", "Adyen", "Stripe", "Swish", "SEB",
                "Swedbank", "Nordea", "Handelsbanken", "PayPal",
                "Square", "Revolut", "Wise", "N26", "Coinbase",
                "Binance", "OpenAI", "Anthropic", "Google Pay",
                "Apple Pay", "Samsung Pay", "Mastercard", "Visa"
            ],
            "weights": {
                "default": 12,
                "Klarna": 15,
                "Stripe": 14,
                "OpenAI": 16
            },
            "labels": {
                "prefix": "watch:"
            }
        },
        "sources.yml": {
            "rsshub": {
                "enabled": True,
                "routes": [
                    "/github/trending/daily/javascript",
                    "/reddit/r/fintech/top/week",
                    "/hackernews/best/weekly"
                ]
            },
            "native_feeds": [
                "https://finextra.com/rss",
                "https://www.riksbank.se/sv/press-och-publicerat/nyheter/rss/",
                "https://news.ycombinator.com/rss"
            ]
        }
    }
    
    for filename, content in configs.items():
        config_path = config_dir / filename
        if not config_path.exists():
            with open(config_path, 'w') as f:
                yaml.dump(content, f, default_flow_style=False, sort_keys=False)
            print(f"Created {filename}")
    
    # Create FreshRSS API user
    client = FreshRSSClient()
    if client.login():
        print("FreshRSS API user verified")
        
        # Import default feeds
        sources_config = configs["sources.yml"]
        
        # Add native feeds
        for feed_url in sources_config.get("native_feeds", []):
            success = client.create_feed(feed_url)
            if success:
                print(f"Added feed: {feed_url}")
        
        # Add RSSHub routes
        rsshub_config = sources_config.get("rsshub", {})
        if rsshub_config.get("enabled"):
            rsshub_base = settings.rsshub_base_url
            for route in rsshub_config.get("routes", []):
                feed_url = f"{rsshub_base}{route}.rss"
                success = client.create_feed(feed_url)
                if success:
                    print(f"Added RSSHub feed: {route}")
        
        client.client.close()
    else:
        print("Warning: Could not connect to FreshRSS")
    
    # Create sample articles in database (for testing)
    db = SessionLocal()
    store = ArticleStore(db)
    
    sample_articles = [
        {
            "freshrss_entry_id": f"sample_{i}",
            "title": f"Sample Article {i}: " + random.choice([
                "New Payment Regulations Impact Fintech",
                "AI Breakthrough in Financial Services",
                "Visa Announces New API Platform",
                "Klarna Expands to New Markets",
                "Cryptocurrency Regulation Update"
            ]),
            "url": f"https://example.com/article/{i}",
            "source": random.choice(["finextra.com", "techcrunch.com", "bloomberg.com"]),
            "published_at": datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72)),
            "score_total": random.randint(40, 95),
            "scores": {
                "keywords": random.randint(10, 40),
                "watchlist": random.randint(0, 20),
                "source": random.randint(5, 10),
                "recency_factor": round(random.uniform(0.3, 1.0), 2)
            },
            "topics": random.sample(["payments", "ai", "fintech", "regulation"], k=2),
            "entities": {"matched": random.sample(["Visa", "Klarna", "Stripe"], k=1)},
            "flags": {"interesting": True} if random.random() > 0.5 else {}
        }
        for i in range(10)
    ]
    
    for article_data in sample_articles:
        store.upsert_article(article_data)
    
    db.close()
    print(f"Seeded {len(sample_articles)} sample articles")
    print("\nSeeding complete!")
    print("You can now:")
    print("  - Access FreshRSS at http://localhost:8080")
    print("  - Access the API at http://localhost:8000")
    print("  - Access the Web UI at http://localhost:3000")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed()
    else:
        print("Usage: python -m app.utils seed")