from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
from typing import Optional
from .config import settings
from .freshrss_client import FreshRSSClient
from .scoring import ScoringEngine
from .store import ArticleStore, Article
from .deps import SessionLocal

class RefreshScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_result = {"new_entries": 0, "scored": 0}
    
    async def poll_and_score(self) -> dict:
        """Main task: poll FreshRSS and score new entries"""
        print(f"Starting poll and score at {datetime.now()}")
        
        db = SessionLocal()
        store = ArticleStore(db)
        client = FreshRSSClient()
        scorer = ScoringEngine()
        
        # Start a new run
        run = store.create_run()
        
        new_entries = 0
        scored = 0
        errors = []
        
        try:
            # Login to FreshRSS
            if not client.login():
                errors.append("Failed to login to FreshRSS")
                return {"new_entries": 0, "scored": 0, "errors": errors}
            
            # Get last run timestamp
            last_article = db.query(Article).order_by(Article.created_at.desc()).first()
            since_timestamp = None
            if last_article:
                since_timestamp = int(last_article.created_at.timestamp())
            
            # Fetch new entries
            entries = client.get_entries(since_timestamp=since_timestamp, limit=200)
            print(f"Fetched {len(entries)} entries from FreshRSS")
            
            for entry in entries:
                try:
                    # Calculate score
                    score_total, scores, topics, entities = scorer.calculate_score(
                        title=entry["title"],
                        content=entry.get("content", ""),
                        source=entry["source"],
                        published_at=entry["published_at"]
                    )
                    
                    # Prepare article data
                    article_data = {
                        "freshrss_entry_id": entry["freshrss_entry_id"],
                        "title": entry["title"],
                        "url": entry["url"],
                        "source": entry["source"],
                        "published_at": entry["published_at"],
                        "score_total": score_total,
                        "scores": scores,
                        "topics": topics,
                        "entities": {"matched": entities},
                        "flags": {}
                    }
                    
                    # Check for duplicates
                    existing = store.get_article_by_entry_id(entry["freshrss_entry_id"])
                    if not existing:
                        new_entries += 1
                    
                    # Upsert article
                    article = store.upsert_article(article_data)
                    scored += 1
                    
                    # Apply labels and stars in FreshRSS
                    labels = scorer.get_labels_for_score(score_total, entities)
                    
                    for label in labels:
                        success = client.add_label(entry["freshrss_entry_id"], label)
                        if success:
                            if "flags" not in article_data:
                                article_data["flags"] = {}
                            article_data["flags"][label] = True
                    
                    # Star if threshold met
                    if scorer.should_star(score_total):
                        success = client.star_entry(entry["freshrss_entry_id"])
                        if success and article:
                            article.flags = article.flags or {}
                            article.flags["starred"] = True
                            db.commit()
                    
                    print(f"Processed: {entry['title'][:50]}... Score: {score_total}")
                    
                except Exception as e:
                    error_msg = f"Error processing entry {entry.get('title', 'Unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
                    continue
            
            # Import RSSHub routes if configured
            await self._import_rsshub_feeds(client, scorer.sources_config)
            
        except Exception as e:
            error_msg = f"Poll and score error: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
        finally:
            # Finish the run
            store.finish_run(run.id, new_entries, scored, errors)
            db.close()
            client.client.close()
        
        self.last_run = datetime.now()
        self.last_result = {"new_entries": new_entries, "scored": scored}
        
        print(f"Poll and score completed: {new_entries} new, {scored} scored")
        return self.last_result
    
    async def _import_rsshub_feeds(self, client: FreshRSSClient, sources_config: dict):
        """Import RSSHub routes as feeds"""
        rsshub_config = sources_config.get("rsshub", {})
        if not rsshub_config.get("enabled", False):
            return
        
        rsshub_base = settings.rsshub_base_url
        existing_feeds = client.get_feeds()
        existing_urls = [f.get("url", "") for f in existing_feeds]
        
        for route in rsshub_config.get("routes", []):
            feed_url = f"{rsshub_base}{route}.rss"
            if feed_url not in existing_urls:
                success = client.create_feed(feed_url)
                if success:
                    print(f"Added RSSHub feed: {route}")
    
    def start(self):
        """Start the scheduler"""
        if not settings.scheduler_enabled:
            print("Scheduler is disabled")
            return
        
        if self.is_running:
            print("Scheduler is already running")
            return
        
        # Schedule the job
        self.scheduler.add_job(
            self.poll_and_score,
            trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
            id="poll_and_score",
            name="Poll FreshRSS and score articles",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        print(f"Scheduler started, will run every {settings.scheduler_interval_minutes} minutes")
        
        # Run once immediately
        asyncio.create_task(self.poll_and_score())
    
    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            print("Scheduler stopped")
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            "running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_result": self.last_result,
            "next_run": self.scheduler.get_job("poll_and_score").next_run_time.isoformat() 
                if self.is_running and self.scheduler.get_job("poll_and_score") else None
        }

# Global scheduler instance
scheduler = RefreshScheduler()