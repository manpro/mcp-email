"""Background scheduler for real-time ML model updates"""
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from .deps import SessionLocal
from .ml.realtime_learner import RealtimeLearner

logger = logging.getLogger(__name__)

class LearningScheduler:
    """Handles scheduled ML model updates"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 3600  # Check every hour
        
    async def start(self):
        """Start the learning scheduler"""
        if self.running:
            logger.warning("Learning scheduler is already running")
            return
            
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Learning scheduler started")
    
    async def stop(self):
        """Stop the learning scheduler"""
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Learning scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info(f"Learning scheduler loop started, checking every {self.check_interval} seconds")
        
        while self.running:
            try:
                await self._check_and_update_models()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Learning scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in learning scheduler: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_update_models(self):
        """Check if models need updating and perform updates if needed"""
        db = None
        try:
            db = SessionLocal()
            learner = RealtimeLearner(db)
            
            # Check if update is needed
            if learner.should_update_model():
                logger.info("Automatic model update triggered")
                
                success = learner.perform_incremental_update()
                
                if success:
                    logger.info("Automatic model update completed successfully")
                else:
                    logger.warning("Automatic model update failed or not supported")
            else:
                logger.debug("Model update not needed at this time")
                
        except Exception as e:
            logger.error(f"Error in automatic model update check: {e}")
        finally:
            if db:
                db.close()
    
    def force_update(self) -> bool:
        """Force an immediate model update check"""
        if not self.running:
            logger.error("Learning scheduler not running")
            return False
            
        # Create a one-time update task
        asyncio.create_task(self._check_and_update_models())
        logger.info("Force update requested")
        return True

# Global scheduler instance
learning_scheduler = LearningScheduler()

async def start_learning_scheduler():
    """Start the global learning scheduler"""
    await learning_scheduler.start()

async def stop_learning_scheduler():
    """Stop the global learning scheduler"""
    await learning_scheduler.stop()