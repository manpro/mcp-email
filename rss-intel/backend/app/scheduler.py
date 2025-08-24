from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
from typing import Optional
from .config import settings
from .freshrss_client import FreshRSSClient
from .direct_rss_client import DirectRSSClient
from .scoring import ScoringEngine
from .store import ArticleStore, Article
from .deps import SessionLocal
from .content_service import ContentExtractionService
from .ml.embedding import batch_embed_articles
from .ml.trainer import ModelTrainer
from .ml.ranker import batch_score_articles
from .clustering import cluster_articles_batch
from .ml.personalization import PersonalizationEngine

class RefreshScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_result = {"new_entries": 0, "scored": 0}
    
    async def poll_and_score(self) -> dict:
        """Main task: poll RSS feeds and score new entries"""
        print(f"Starting poll and score at {datetime.now()}")
        
        db = SessionLocal()
        store = ArticleStore(db)
        scorer = ScoringEngine()
        
        # Try FreshRSS first, fallback to DirectRSSClient
        client = None
        use_direct_rss = False
        
        try:
            client = FreshRSSClient()
            if not client.login():
                print("FreshRSS login failed, falling back to DirectRSSClient")
                client = DirectRSSClient(db)
                use_direct_rss = True
        except Exception as e:
            print(f"FreshRSS unavailable ({e}), using DirectRSSClient")
            client = DirectRSSClient(db)
            use_direct_rss = True
        
        # Start a new run
        run = store.create_run()
        
        new_entries = 0
        scored = 0
        errors = []
        
        try:
            # Skip login check if using DirectRSSClient (already handled above)
            if not use_direct_rss and not client.login():
                errors.append("Failed to login to FreshRSS")
                return {"new_entries": 0, "scored": 0, "errors": errors}
            
            # Get timestamp from 7 days ago to avoid missing articles
            from datetime import timedelta
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            since_timestamp = int(seven_days_ago.timestamp())
            
            # Fetch new entries
            if use_direct_rss:
                entries = await client.get_entries(since_timestamp=since_timestamp, limit=500)
                print(f"Fetched {len(entries)} entries from DirectRSS")
            else:
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
                    
                    # Apply labels and stars (stored in database)
                    labels = scorer.get_labels_for_score(score_total, entities)
                    
                    # Store labels in article flags
                    for label in labels:
                        if "flags" not in article_data:
                            article_data["flags"] = {}
                        article_data["flags"][label] = True
                        
                        # Also try to add to external system if not DirectRSS
                        if not use_direct_rss:
                            client.add_label(entry["freshrss_entry_id"], label)
                    
                    # Star if threshold met
                    if scorer.should_star(score_total):
                        if article:
                            article.flags = article.flags or {}
                            article.flags["starred"] = True
                            db.commit()
                            
                        # Also try to star in external system if not DirectRSS
                        if not use_direct_rss:
                            client.star_entry(entry["freshrss_entry_id"])
                    
                    print(f"Processed: {entry['title'][:50]}... Score: {score_total}")
                    
                except Exception as e:
                    error_msg = f"Error processing entry {entry.get('title', 'Unknown')}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
                    continue
            
            # Import RSSHub routes if configured (only for FreshRSS)
            if not use_direct_rss:
                await self._import_rsshub_feeds(client, scorer.sources_config)
            
            # Extract content for high-scoring articles
            if settings.content_extraction_enabled:
                print("Starting content extraction for high-scoring articles...")
                extraction_service = ContentExtractionService(
                    db=db,
                    max_concurrent=settings.content_extraction_concurrent,
                    rate_limit=settings.content_extraction_rate_limit
                )
                
                try:
                    # Process articles with score >= threshold
                    extraction_stats = await extraction_service.process_pending_articles(
                        limit=settings.content_extraction_batch_size,
                        min_score=settings.content_extraction_min_score
                    )
                    print(f"Content extraction stats: {extraction_stats}")
                except Exception as extraction_error:
                    error_msg = f"Content extraction error: {str(extraction_error)}"
                    errors.append(error_msg)
                    print(error_msg)
                finally:
                    await extraction_service.close()
            
        except Exception as e:
            error_msg = f"Poll and score error: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
        finally:
            # Finish the run
            store.finish_run(run.id, new_entries, scored, errors)
            db.close()
            
            # Close client connection
            try:
                if use_direct_rss and hasattr(client, 'close'):
                    await client.close()
                elif hasattr(client, 'client') and hasattr(client.client, 'close'):
                    client.client.close()
            except Exception as e:
                print(f"Error closing client: {e}")
        
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
        
        # Schedule main RSS polling job
        self.scheduler.add_job(
            self.poll_and_score,
            trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
            id="poll_and_score",
            name="Poll RSS and score articles",
            replace_existing=True
        )
        
        # Schedule ML jobs
        self._schedule_ml_jobs()
        
        self.scheduler.start()
        self.is_running = True
        print(f"Scheduler started, will run every {settings.scheduler_interval_minutes} minutes")
        
        # Run once immediately
        asyncio.create_task(self.poll_and_score())
    
    def _schedule_ml_jobs(self):
        """Schedule ML-related jobs"""
        import os
        # Embed new articles every 15 minutes
        self.scheduler.add_job(
            self._embed_new_articles,
            trigger=IntervalTrigger(minutes=15),
            id="embed_articles",
            name="Embed new articles",
            replace_existing=True
        )
        
        # Daily training at 3 AM
        from apscheduler.triggers.cron import CronTrigger
        daily_train_hour = int(os.getenv('ML_DAILY_TRAIN_HOUR', '3'))
        self.scheduler.add_job(
            self._daily_train,
            trigger=CronTrigger(hour=daily_train_hour),
            id="daily_train",
            name="Daily ML model training",
            replace_existing=True
        )
        
        # Score articles hourly
        self.scheduler.add_job(
            self._score_articles,
            trigger=IntervalTrigger(hours=1),
            id="score_articles",
            name="Score articles with ML model",
            replace_existing=True
        )
        
        # Run ingest from additional sources every 30 minutes
        self.scheduler.add_job(
            self._run_ingest_sources,
            trigger=IntervalTrigger(minutes=30),
            id="run_ingest",
            name="Ingest from additional sources",
            replace_existing=True
        )
        
        # Process article chunks hourly
        self.scheduler.add_job(
            self._process_chunks,
            trigger=IntervalTrigger(hours=1),
            id="process_chunks", 
            name="Process article chunks for search",
            replace_existing=True
        )
        
        # Cluster articles every 30 minutes
        self.scheduler.add_job(
            self._cluster_articles,
            trigger=IntervalTrigger(minutes=30),
            id="cluster_articles",
            name="Cluster articles into stories",
            replace_existing=True
        )
        
        # Train personalization model daily at 4 AM
        daily_personalization_hour = int(os.getenv('ML_PERSONALIZATION_TRAIN_HOUR', '4'))
        self.scheduler.add_job(
            self._train_personalization,
            trigger=CronTrigger(hour=daily_personalization_hour),
            id="train_personalization",
            name="Train personalization model",
            replace_existing=True
        )
        
        # Score articles with personalization every 2 hours
        self.scheduler.add_job(
            self._score_personalization,
            trigger=IntervalTrigger(hours=2),
            id="score_personalization", 
            name="Score articles with personalization model",
            replace_existing=True
        )
        
        # Generate daily spotlight at 07:00 Europe/Stockholm
        self.scheduler.add_job(
            self._generate_daily_spotlight,
            trigger=CronTrigger(hour=7, minute=0, timezone='Europe/Stockholm'),
            id="generate_spotlight",
            name="Generate daily spotlight digest",
            replace_existing=True
        )
    
    async def _embed_new_articles(self):
        """Background job to embed new articles"""
        db = SessionLocal()
        try:
            count = batch_embed_articles(db, limit=50)
            print(f"Embedded {count} new articles")
        except Exception as e:
            print(f"Embedding job error: {e}")
        finally:
            db.close()
    
    async def _daily_train(self):
        """Background job for daily model training"""
        db = SessionLocal()
        try:
            trainer = ModelTrainer(db)
            result = trainer.train_and_save(lookback_days=30)
            if result['success']:
                print(f"Daily training completed: AUC={result['metrics'].get('test_auc', 0):.3f}")
            else:
                print(f"Daily training failed: {result.get('error')}")
        except Exception as e:
            print(f"Training job error: {e}")
        finally:
            db.close()
    
    async def _score_articles(self):
        """Background job to score articles"""
        db = SessionLocal()
        try:
            result = batch_score_articles(db, limit=500)
            print(f"Scored {result['total_scored']} articles")
        except Exception as e:
            print(f"Scoring job error: {e}")
        finally:
            db.close()
    
    async def _run_ingest_sources(self):
        """Background job to run ingest from additional sources"""
        try:
            from .ingest.scheduler import ingest_scheduler
            result = await ingest_scheduler.run_all_sources()
            print(f"Ingest completed: {result}")
        except Exception as e:
            print(f"Ingest job error: {e}")
    
    async def _process_chunks(self):
        """Background job to process article chunks for search"""
        db = SessionLocal()
        try:
            from .vec.upsert_chunks import upsert_chunks_for_articles
            result = upsert_chunks_for_articles(db, limit=100)
            print(f"Chunk processing: {result}")
        except Exception as e:
            print(f"Chunk processing error: {e}")
        finally:
            db.close()
    
    async def _cluster_articles(self):
        """Background job to cluster articles into stories"""
        db = SessionLocal()
        try:
            result = cluster_articles_batch(db, limit=100)
            print(f"Article clustering: {result}")
        except Exception as e:
            print(f"Article clustering error: {e}")
        finally:
            db.close()
    
    async def _train_personalization(self):
        """Background job to train personalization model"""
        db = SessionLocal()
        try:
            engine = PersonalizationEngine(db)
            result = engine.train_model(lookback_days=30)
            if result['success']:
                print(f"Personalization training completed: AUC={result.get('auc', 0):.3f}, samples={result.get('training_samples', 0)}")
            else:
                print(f"Personalization training failed: {result.get('error')}")
        except Exception as e:
            print(f"Personalization training error: {e}")
        finally:
            db.close()
    
    async def _score_personalization(self):
        """Background job to score articles with personalization model"""
        db = SessionLocal()
        try:
            # Get recent unscored articles
            from sqlalchemy import text
            recent_articles = db.execute(text("""
                SELECT a.id FROM articles a
                LEFT JOIN predictions p ON p.article_id = a.id 
                    AND p.model_id = (SELECT id FROM ml_models WHERE model_type = 'personalization' AND is_active = true LIMIT 1)
                WHERE a.published_at >= NOW() - INTERVAL '7 days'
                AND p.id IS NULL
                ORDER BY a.published_at DESC
                LIMIT 200
            """)).fetchall()
            
            if recent_articles:
                article_ids = [row.id for row in recent_articles]
                engine = PersonalizationEngine(db)
                result = engine.score_articles_batch(article_ids)
                print(f"Personalization scoring: {result}")
            else:
                print("No new articles to score with personalization model")
        except Exception as e:
            print(f"Personalization scoring error: {e}")
        finally:
            db.close()
    
    async def _generate_daily_spotlight(self):
        """Background job to generate daily spotlight digest"""
        db = SessionLocal()
        try:
            from .spotlight_engine import generate_daily_spotlight
            result = generate_daily_spotlight(db)
            print(f"Daily spotlight generated: {result}")
        except Exception as e:
            print(f"Spotlight generation error: {e}")
        finally:
            db.close()
    
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