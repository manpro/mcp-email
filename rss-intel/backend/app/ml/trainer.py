"""ML model training module"""
import logging
import os
import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, brier_score_loss, classification_report
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from sqlalchemy import text

from .features import build_training_features
from .labels import get_training_labels, compute_label_stats
from .uservec import get_user_embedding
from ..deps import SessionLocal

logger = logging.getLogger(__name__)

# Configuration
MODELS_DIR = Path(os.getenv('ML_MODELS_DIR', '/app/models'))
LOOKBACK_DAYS = int(os.getenv('ML_LOOKBACK_DAYS', '30'))
MIN_SAMPLES = int(os.getenv('ML_MIN_TRAIN_SAMPLES', '100'))

class ModelTrainer:
    """ML model trainer with evaluation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.models_dir = MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_training_data(
        self, 
        lookback_days: int = LOOKBACK_DAYS,
        user_id: str = "owner"
    ) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        Prepare training dataset with features and labels
        
        Returns:
            (DataFrame with features and labels, stats dict)
        """
        logger.info(f"Preparing training data, lookback={lookback_days} days")
        
        # Get user embedding for content features
        user_embedding = get_user_embedding(self.db, user_id, lookback_days=30)
        
        # Build features
        features_df = build_training_features(
            self.db, 
            user_embedding=user_embedding,
            lookback_days=lookback_days,
            min_interactions=2
        )
        
        if features_df.empty:
            logger.warning("No feature data available")
            return None, {"error": "No feature data"}
        
        # Get labels
        article_ids = features_df['article_id'].tolist()
        labels_df = get_training_labels(
            self.db,
            lookback_days=lookback_days,
            min_events_per_article=2,
            user_id=user_id
        )
        
        if labels_df.empty:
            logger.warning("No label data available")
            return None, {"error": "No label data"}
        
        # Merge features and labels
        training_df = features_df.merge(labels_df, on='article_id', how='inner')
        
        # Remove unlabeled samples
        training_df = training_df[training_df['label'].notna()]
        
        if len(training_df) < MIN_SAMPLES:
            logger.warning(f"Not enough training samples: {len(training_df)} < {MIN_SAMPLES}")
            return None, {"error": f"Insufficient samples: {len(training_df)}"}
        
        # Compute stats
        label_stats = compute_label_stats(training_df)
        feature_stats = {
            "total_samples": len(training_df),
            "feature_dim": len(training_df.iloc[0]['features']) if not training_df.empty else 0,
            "time_range": {
                "start": training_df['published_at'].min().isoformat() if 'published_at' in training_df else None,
                "end": training_df['published_at'].max().isoformat() if 'published_at' in training_df else None
            }
        }
        
        stats = {**label_stats, **feature_stats}
        logger.info(f"Training data prepared: {stats}")
        
        return training_df, stats
    
    def train_model(
        self, 
        training_df: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[LogisticRegression, StandardScaler, Dict]:
        """
        Train logistic regression model
        
        Returns:
            (trained model, scaler, metrics dict)
        """
        logger.info("Training logistic regression model")
        
        # Prepare features and labels
        X = np.array(training_df['features'].tolist())
        y = training_df['label'].values
        
        # Temporal split (use recent data for test)
        training_df_sorted = training_df.sort_values('published_at')
        split_idx = int(len(training_df_sorted) * (1 - test_size))
        
        train_df = training_df_sorted.iloc[:split_idx]
        test_df = training_df_sorted.iloc[split_idx:]
        
        X_train = np.array(train_df['features'].tolist())
        y_train = train_df['label'].values
        X_test = np.array(test_df['features'].tolist())
        y_test = test_df['label'].values
        
        logger.info(f"Train: {len(X_train)} samples, Test: {len(X_test)} samples")
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = LogisticRegression(
            class_weight='balanced',
            random_state=random_state,
            max_iter=1000,
            C=1.0  # L2 regularization
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        metrics = self._evaluate_model(model, scaler, X_train, y_train, X_test, y_test)
        
        logger.info(f"Model training completed: AUC={metrics.get('test_auc', 0):.3f}")
        
        return model, scaler, metrics
    
    def _evaluate_model(
        self,
        model: LogisticRegression,
        scaler: StandardScaler,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """Evaluate model performance"""
        
        X_train_scaled = scaler.transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Predictions
        y_train_pred = model.predict_proba(X_train_scaled)[:, 1]
        y_test_pred = model.predict_proba(X_test_scaled)[:, 1]
        
        # Metrics
        metrics = {
            "train_auc": float(roc_auc_score(y_train, y_train_pred)),
            "test_auc": float(roc_auc_score(y_test, y_test_pred)),
            "train_brier": float(brier_score_loss(y_train, y_train_pred)),
            "test_brier": float(brier_score_loss(y_test, y_test_pred)),
            "train_samples": int(len(y_train)),
            "test_samples": int(len(y_test)),
            "positive_rate": float(y_test.mean()),
        }
        
        # Cross-validation on full dataset
        X_full_scaled = scaler.transform(np.vstack([X_train, X_test]))
        y_full = np.hstack([y_train, y_test])
        cv_scores = cross_val_score(model, X_full_scaled, y_full, cv=3, scoring='roc_auc')
        metrics["cv_auc_mean"] = float(cv_scores.mean())
        metrics["cv_auc_std"] = float(cv_scores.std())
        
        return metrics
    
    def save_model(
        self,
        model: LogisticRegression,
        scaler: StandardScaler,
        metrics: Dict,
        model_type: str = "logreg"
    ) -> int:
        """Save model and return model ID"""
        timestamp = datetime.utcnow()
        model_filename = f"{model_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.pkl"
        model_path = self.models_dir / model_filename
        
        # Save model and scaler
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': model,
                'scaler': scaler,
                'created_at': timestamp,
                'metrics': metrics
            }, f)
        
        # Save to database
        result = self.db.execute(text("""
            INSERT INTO models (type, created_at, metrics, artifact_path)
            VALUES (:type, :created_at, :metrics, :artifact_path)
            RETURNING id
        """), {
            "type": model_type,
            "created_at": timestamp,
            "metrics": json.dumps(metrics),
            "artifact_path": str(model_path)
        })
        
        model_id = result.fetchone()[0]
        self.db.commit()
        
        logger.info(f"Model saved: ID={model_id}, path={model_path}")
        return model_id
    
    def train_and_save(
        self,
        lookback_days: int = LOOKBACK_DAYS,
        user_id: str = "owner"
    ) -> Dict:
        """Full training pipeline"""
        try:
            # Prepare data
            training_df, stats = self.prepare_training_data(lookback_days, user_id)
            if training_df is None:
                return {"success": False, "error": "Data preparation failed", "stats": stats}
            
            # Train model
            model, scaler, metrics = self.train_model(training_df)
            
            # Save model
            model_id = self.save_model(model, scaler, metrics)
            
            return {
                "success": True,
                "model_id": model_id,
                "metrics": metrics,
                "data_stats": stats
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"success": False, "error": str(e)}

def load_latest_model(db: Session) -> Optional[Tuple[LogisticRegression, StandardScaler, int]]:
    """Load the latest trained model"""
    result = db.execute(text("""
        SELECT id, artifact_path 
        FROM models 
        WHERE type = 'logreg' 
        ORDER BY created_at DESC 
        LIMIT 1
    """))
    
    row = result.fetchone()
    if not row:
        logger.warning("No trained model found")
        return None
    
    model_path = Path(row.artifact_path)
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return None
    
    try:
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            return data['model'], data['scaler'], row.id
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None

if __name__ == "__main__":
    # CLI for training
    import sys
    
    db = SessionLocal()
    try:
        trainer = ModelTrainer(db)
        
        if len(sys.argv) > 1 and sys.argv[1] == "train":
            lookback = int(sys.argv[2]) if len(sys.argv) > 2 else LOOKBACK_DAYS
            result = trainer.train_and_save(lookback_days=lookback)
            print(json.dumps(result, indent=2))
        else:
            print("Usage: python -m app.ml.trainer train [lookback_days]")
            
    finally:
        db.close()