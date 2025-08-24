"""
Background worker for content extraction
Can run as a separate process or be triggered on-demand
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import settings
from .deps import SessionLocal
from .content_service import ContentExtractionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExtractionWorker:
    """Background worker for processing content extraction queue"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_stats = {}
    
    async def process_extraction_queue(self) -> dict:
        """Process pending articles for content extraction"""
        logger.info(f"Starting content extraction worker at {datetime.utcnow()}")
        
        db = SessionLocal()
        extraction_service = ContentExtractionService(
            db=db,
            max_concurrent=settings.content_extraction_concurrent,
            rate_limit=settings.content_extraction_rate_limit
        )
        
        try:
            # Process pending articles
            stats = await extraction_service.process_pending_articles(
                limit=settings.content_extraction_batch_size,
                min_score=settings.content_extraction_min_score
            )
            
            self.last_run = datetime.utcnow()
            self.last_stats = stats
            
            logger.info(f"Content extraction completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Extraction worker error: {e}")
            return {"error": str(e)}
            
        finally:
            await extraction_service.close()
            db.close()
    
    async def process_specific_articles(self, article_ids: list[int], force: bool = False) -> dict:
        """Process specific articles by ID"""
        logger.info(f"Processing specific articles: {article_ids}")
        
        db = SessionLocal()
        extraction_service = ContentExtractionService(
            db=db,
            max_concurrent=settings.content_extraction_concurrent,
            rate_limit=settings.content_extraction_rate_limit
        )
        
        try:
            stats = await extraction_service.process_article_batch(
                article_ids=article_ids,
                force=force
            )
            
            logger.info(f"Batch extraction completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Batch extraction error: {e}")
            return {"error": str(e)}
            
        finally:
            await extraction_service.close()
            db.close()
    
    def start_scheduled(self, interval_minutes: int = 30):
        """Start scheduled extraction processing"""
        if self.is_running:
            logger.warning("Extraction worker is already running")
            return
        
        # Schedule the job
        self.scheduler.add_job(
            self.process_extraction_queue,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="extraction_queue",
            name="Process content extraction queue",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Extraction worker started, will run every {interval_minutes} minutes")
        
        # Run once immediately
        asyncio.create_task(self.process_extraction_queue())
    
    def stop(self):
        """Stop the scheduled worker"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Extraction worker stopped")
    
    def get_status(self) -> dict:
        """Get worker status"""
        return {
            "running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_stats": self.last_stats,
            "next_run": self.scheduler.get_job("extraction_queue").next_run_time.isoformat()
                if self.is_running and self.scheduler.get_job("extraction_queue") else None
        }


# Global worker instance
extraction_worker = ExtractionWorker()


async def main():
    """Run extraction worker as standalone process"""
    worker = ExtractionWorker()
    
    # Run in a loop
    while True:
        try:
            await worker.process_extraction_queue()
            
            # Wait before next run
            await asyncio.sleep(settings.content_extraction_interval_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("Extraction worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(60)  # Wait a minute before retry


if __name__ == "__main__":
    # Run as standalone worker
    asyncio.run(main())