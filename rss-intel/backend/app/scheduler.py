from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
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
from .events import publish_article_event, EventType
from .intelligence import (
    trend_detector, content_classifier, sentiment_analyzer,
    keyword_extractor, quality_scorer, similarity_detector
)

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
                    score_total, scores, topics, entities, event_flags = scorer.calculate_score(
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
                        "flags": event_flags
                    }
                    
                    # Check for duplicates
                    existing = store.get_article_by_entry_id(entry["freshrss_entry_id"])
                    is_new_article = not existing
                    if is_new_article:
                        new_entries += 1
                    
                    # Upsert article
                    article = store.upsert_article(article_data)
                    scored += 1
                    
                    # Publish event for new or updated articles
                    if article:
                        event_type = EventType.ARTICLE_NEW if is_new_article else EventType.ARTICLE_UPDATED
                        await publish_article_event(
                            article_id=article.id,
                            event_type=event_type,
                            data={
                                "title": article.title,
                                "source": article.source,
                                "score": article.score_total,
                                "url": article.url,
                                "published_at": article.published_at.isoformat() if article.published_at else None
                            }
                        )
                        
                        # Send notifications for high-scoring new articles (temporarily disabled)
                        if is_new_article and score_total >= 8.0:
                            # from .notifications import send_high_score_alert
                            send_high_score_alert = lambda *args, **kwargs: None
                            # TODO: Get list of users who want high score alerts
                            # For now, send to test user
                            try:
                                await send_high_score_alert("test-user", {
                                    "title": article.title,
                                    "url": article.url,
                                    "score": score_total,
                                    "source": article.source,
                                    "article_id": article.id
                                })
                            except Exception as e:
                                print(f"Failed to send high score notification: {e}")
                        
                        # Send breaking news for very high scores (temporarily disabled)
                        if is_new_article and score_total >= 9.0:
                            # from .notifications import send_breaking_news_alert
                            send_breaking_news_alert = lambda *args, **kwargs: None
                            try:
                                await send_breaking_news_alert("test-user", {
                                    "title": article.title,
                                    "url": article.url,
                                    "score": score_total,
                                    "source": article.source,
                                    "article_id": article.id
                                })
                            except Exception as e:
                                print(f"Failed to send breaking news notification: {e}")
                    
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
        
        # Schedule intelligence analysis jobs
        self._schedule_intelligence_jobs()
        
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
    
    def _schedule_intelligence_jobs(self):
        """Schedule AI intelligence analysis jobs"""
        
        # Trend detection every hour
        self.scheduler.add_job(
            self._run_trend_detection,
            trigger=IntervalTrigger(hours=1),
            id="trend_detection",
            name="AI Trend Detection",
            replace_existing=True
        )
        
        # Content analysis for recent articles every 30 minutes
        self.scheduler.add_job(
            self._analyze_recent_content,
            trigger=IntervalTrigger(minutes=30),
            id="content_analysis",
            name="AI Content Analysis",
            replace_existing=True
        )
        
        # Quality assessment daily
        self.scheduler.add_job(
            self._assess_content_quality,
            trigger=IntervalTrigger(hours=24),
            id="quality_assessment",
            name="Content Quality Assessment",
            replace_existing=True
        )
        
        # Similarity detection for new articles every 2 hours
        self.scheduler.add_job(
            self._update_similarity_index,
            trigger=IntervalTrigger(hours=2),
            id="similarity_update",
            name="Similarity Index Update",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self._cleanup_spam_content,
            trigger=IntervalTrigger(hours=6),
            id="spam_cleanup",
            name="Spam and Low-Quality Content Cleanup",
            replace_existing=True
        )
        
        # Daily spam statistics update
        from .config.spam_config import get_spam_config
        config = get_spam_config()
        self.scheduler.add_job(
            self._update_spam_statistics,
            trigger=CronTrigger(hour=config.stats_update_hour, minute=0),
            id="spam_stats_update",
            name="Daily Spam Statistics Update",
            replace_existing=True
        )
    
    async def _run_trend_detection(self):
        """Background job for trend detection"""
        db = SessionLocal()
        try:
            # Get recent articles for trend detection
            from datetime import datetime, timedelta
            recent_time = datetime.now() - timedelta(hours=24)
            
            articles = db.query(Article).filter(
                Article.created_at >= recent_time
            ).limit(200).all()
            
            if not articles:
                print("No recent articles for trend detection")
                return
            
            # Convert to trend detection format
            content_items = [
                {
                    "id": str(article.id),
                    "title": article.title,
                    "content": article.content or "",
                    "url": article.url,
                    "source": article.source,
                    "published_at": article.published_at
                }
                for article in articles
            ]
            
            # Run trend detection
            trends = trend_detector.detect_trends(content_items)
            
            # Send trend alerts if significant trends found
            significant_trends = [t for t in trends if t.confidence >= 0.8 and t.article_count >= 5]
            
            if significant_trends:
                # from .notifications import send_trend_alert
                send_trend_alert = lambda *args, **kwargs: None  # Placeholder
                for trend in significant_trends[:3]:  # Limit to top 3 trends
                    try:
                        await send_trend_alert("test-user", {
                            "trend_name": trend.name,
                            "article_count": trend.article_count,
                            "confidence": trend.confidence,
                            "keywords": trend.keywords[:5]
                        })
                    except Exception as e:
                        print(f"Failed to send trend alert: {e}")
            
            print(f"Trend detection completed: {len(trends)} trends found, {len(significant_trends)} significant")
            
        except Exception as e:
            print(f"Trend detection job error: {e}")
        finally:
            db.close()
    
    async def _analyze_recent_content(self):
        """Background job for content analysis (classification, sentiment, keywords)"""
        db = SessionLocal()
        try:
            from datetime import datetime, timedelta
            
            # Get recent articles that haven't been analyzed
            recent_time = datetime.now() - timedelta(hours=2)
            
            articles = db.query(Article).filter(
                Article.created_at >= recent_time,
                Article.topics.is_(None)  # Use topics field to track if analyzed
            ).limit(50).all()
            
            if not articles:
                return
            
            analyzed_count = 0
            
            for article in articles:
                try:
                    # Classification
                    classification = content_classifier.classify_content(
                        title=article.title,
                        content=article.content or "",
                        url=article.url,
                        source=article.source
                    )
                    
                    # Sentiment Analysis
                    sentiment = sentiment_analyzer.analyze_sentiment(
                        title=article.title,
                        content=article.content or "",
                        source=article.source
                    )
                    
                    # Keyword Extraction
                    keywords = keyword_extractor.extract_keywords(
                        title=article.title,
                        content=article.content or "",
                        url=article.url,
                        max_keywords=10
                    )
                    
                    # Store results in article
                    article.topics = {
                        "primary_category": classification.primary_category.name,
                        "sentiment_label": sentiment.overall_sentiment.label,
                        "sentiment_polarity": sentiment.overall_sentiment.polarity,
                        "keywords": [kw.keyword for kw in keywords.keywords[:5]],
                        "analyzed_at": datetime.now().isoformat()
                    }
                    
                    analyzed_count += 1
                    
                except Exception as e:
                    print(f"Error analyzing article {article.id}: {e}")
            
            db.commit()
            print(f"Content analysis completed: {analyzed_count} articles analyzed")
            
        except Exception as e:
            print(f"Content analysis job error: {e}")
        finally:
            db.close()
    
    async def _assess_content_quality(self):
        """Background job for content quality assessment"""
        db = SessionLocal()
        try:
            from datetime import datetime, timedelta
            
            # Get high-scoring articles from last 24 hours for quality assessment
            recent_time = datetime.now() - timedelta(hours=24)
            
            articles = db.query(Article).filter(
                Article.created_at >= recent_time,
                Article.score_total >= 7.0  # Only assess high-quality articles
            ).limit(30).all()
            
            quality_assessments = []
            
            for article in articles:
                try:
                    quality = quality_scorer.score_content_quality(
                        title=article.title,
                        content=article.content or "",
                        source_url=article.url,
                        publish_date=article.published_at
                    )
                    
                    quality_assessments.append({
                        "article_id": article.id,
                        "quality_score": quality.overall_score,
                        "quality_grade": quality.quality_grade,
                        "title": article.title[:50] + "..." if len(article.title) > 50 else article.title
                    })
                    
                except Exception as e:
                    print(f"Error assessing quality for article {article.id}: {e}")
            
            # Log quality summary
            if quality_assessments:
                avg_quality = sum(qa["quality_score"] for qa in quality_assessments) / len(quality_assessments)
                high_quality = [qa for qa in quality_assessments if qa["quality_score"] >= 0.8]
                
                print(f"Quality assessment completed: {len(quality_assessments)} articles, avg score: {avg_quality:.2f}, {len(high_quality)} high quality")
            
        except Exception as e:
            print(f"Quality assessment job error: {e}")
        finally:
            db.close()
    
    async def _update_similarity_index(self):
        """Background job to update similarity detection index"""
        db = SessionLocal()
        try:
            from datetime import datetime, timedelta
            
            # Get recent articles to add to similarity index
            recent_time = datetime.now() - timedelta(hours=4)
            
            articles = db.query(Article).filter(
                Article.created_at >= recent_time
            ).limit(100).all()
            
            added_count = 0
            duplicate_found = 0
            
            for article in articles:
                try:
                    # Add to similarity detector
                    similarity_detector.add_content(
                        content_id=str(article.id),
                        title=article.title,
                        content=article.content or "",
                        url=article.url
                    )
                    added_count += 1
                    
                    # Check for duplicates in new articles
                    if added_count <= 10:  # Only check duplicates for first few articles to avoid overload
                        similarity_result = similarity_detector.detect_similar_content(
                            content_id=str(article.id),
                            similarity_types=["duplicate", "near_duplicate"]
                        )
                        
                        if similarity_result.duplicate_matches:
                            duplicate_found += len(similarity_result.duplicate_matches)
                            # Could flag duplicates here
                    
                except Exception as e:
                    print(f"Error adding article {article.id} to similarity index: {e}")
            
            print(f"Similarity index updated: {added_count} articles added, {duplicate_found} duplicates detected")
            
        except Exception as e:
            print(f"Similarity update job error: {e}")
        finally:
            db.close()

    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            print("Scheduler stopped")
    
    async def _cleanup_spam_content(self):
        """Background job to identify and mark spam/low-quality content using SpamService"""
        db = SessionLocal()
        try:
            from datetime import datetime, timedelta
            from .services.spam_service import SpamService
            from .config.spam_config import get_spam_config
            
            config = get_spam_config()
            
            # Skip if spam detection is disabled
            if not config.enabled:
                print("Spam detection disabled in config, skipping cleanup")
                return
            
            # Get recent articles for spam analysis
            recent_time = datetime.now() - timedelta(hours=12)  # Last 12 hours
            
            articles = db.query(Article).filter(
                Article.created_at >= recent_time,
                Article.score.isnot(None),  # Only analyze scored articles
                Article.last_spam_check.is_(None)  # Haven't been checked yet
            ).limit(config.batch_size).all()
            
            if not articles:
                print("No new articles to analyze for spam")
                return
            
            spam_service = SpamService(db)
            article_ids = [article.id for article in articles]
            
            # Run batch analysis
            batch_results = spam_service.batch_analyze_articles(article_ids)
            
            # Log cleanup summary
            print(f"Spam cleanup completed: {batch_results['summary']['total_articles']} articles analyzed")
            print(f"  - Spam detected: {batch_results['summary']['spam_detected']}")  
            print(f"  - Spam rate: {batch_results['summary']['spam_rate']:.1%}")
            print(f"  - Avg content score: {batch_results['summary']['average_content_score']:.1%}")
            
            if batch_results['errors']:
                print(f"  - Errors: {len(batch_results['errors'])}")
                for error in batch_results['errors'][:5]:  # Show first 5 errors
                    print(f"    {error}")
            
        except Exception as e:
            print(f"Spam cleanup job error: {e}")
        finally:
            db.close()
    
    async def _update_spam_statistics(self):
        """Background job to update daily spam statistics"""
        db = SessionLocal()
        try:
            from .services.spam_service import SpamService
            
            spam_service = SpamService(db)
            updated_stats = spam_service.update_daily_stats()
            
            print(f"Updated spam statistics for {updated_stats.date}")
            print(f"  - Articles checked: {updated_stats.total_articles_checked}")
            print(f"  - Spam detected: {updated_stats.spam_detected_count}")
            print(f"  - Spam rate: {updated_stats.spam_rate:.1%}")
            
            if updated_stats.avg_spam_probability:
                print(f"  - Avg spam probability: {updated_stats.avg_spam_probability:.1%}")
            if updated_stats.avg_content_score:
                print(f"  - Avg content score: {updated_stats.avg_content_score:.1%}")
            
        except Exception as e:
            print(f"Spam statistics update job error: {e}")
        finally:
            db.close()
    
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