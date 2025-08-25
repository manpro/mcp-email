#!/usr/bin/env python3
"""
Train ML personalization model for RSS Intelligence
"""
import sys
import os
sys.path.insert(0, '/app')

from app.deps import SessionLocal
from app.ml.personalization import PersonalizationEngine
from app.config import settings
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Train personalization model"""
    logger.info("Starting personalization model training...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize personalization engine
        engine = PersonalizationEngine(db)
        
        # Train model
        result = engine.train_model(lookback_days=30)
        
        if result['success']:
            logger.info(f"✅ Model training successful!")
            logger.info(f"   AUC Score: {result['auc']:.3f}")
            logger.info(f"   Training samples: {result['training_samples']}")
            logger.info(f"   Positive samples: {result['positive_samples']}")
            logger.info(f"   Model saved to: {result['model_path']}")
            return 0
        else:
            logger.error(f"❌ Model training failed: {result['error']}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Training error: {e}")
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())