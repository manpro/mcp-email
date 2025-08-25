#!/usr/bin/env python3
"""
Train advanced ML personalization model with improved features
"""
import sys
import os
sys.path.insert(0, '/app')

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import joblib
import logging

from app.deps import SessionLocal
from app.ml.advanced_features import build_advanced_training_dataset
from app.store import MLModel
from app.config import settings
from sqlalchemy import text

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def train_multiple_models(X_train, X_test, y_train, y_test, feature_names):
    """Train and compare multiple ML models"""
    
    models = {
        'logistic_regression': LogisticRegression(
            random_state=42, max_iter=1000, class_weight='balanced'
        ),
        'random_forest': RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight='balanced',
            max_depth=10, min_samples_split=5, min_samples_leaf=2
        ),
        'gradient_boosting': GradientBoostingClassifier(
            n_estimators=100, random_state=42, max_depth=5,
            learning_rate=0.1, min_samples_split=5, min_samples_leaf=2
        )
    }
    
    results = {}
    
    for model_name, model in models.items():
        logger.info(f"\n=== Training {model_name} ===")
        
        # Train model
        if model_name == 'logistic_regression':
            # Scale features for logistic regression
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            model.fit(X_train_scaled, y_train)
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            # Tree-based models don't need scaling
            scaler = None
            model.fit(X_train, y_train)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Evaluate
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        # Cross validation
        if scaler:
            X_scaled = scaler.transform(X_train)
            cv_scores = cross_val_score(model, X_scaled, y_train, cv=5, scoring='roc_auc')
        else:
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
        
        results[model_name] = {
            'model': model,
            'scaler': scaler,
            'auc_score': auc_score,
            'cv_mean': np.mean(cv_scores),
            'cv_std': np.std(cv_scores),
            'y_pred_proba': y_pred_proba
        }
        
        logger.info(f"AUC Score: {auc_score:.3f}")
        logger.info(f"CV AUC: {np.mean(cv_scores):.3f} (+/- {np.std(cv_scores)*2:.3f})")
        
        # Feature importance for tree-based models
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            top_features = np.argsort(importances)[-10:][::-1]
            logger.info("Top 10 most important features:")
            for i, idx in enumerate(top_features):
                logger.info(f"  {i+1}. Feature {idx}: {importances[idx]:.3f}")
    
    return results

def save_best_model(db, results, feature_names, X_train, y_train):
    """Save the best performing model"""
    
    # Find best model by AUC score
    best_model_name = max(results.keys(), key=lambda k: results[k]['auc_score'])
    best_result = results[best_model_name]
    
    logger.info(f"\n=== Best Model: {best_model_name} ===")
    logger.info(f"AUC Score: {best_result['auc_score']:.3f}")
    
    # Save model
    model_dir = "/app/models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_version = "2.0"  # Advanced model version
    model_path = f"{model_dir}/personalization_advanced_v{model_version}.pkl"
    
    model_data = {
        'model': best_result['model'],
        'scaler': best_result['scaler'],
        'feature_names': feature_names,
        'model_type': best_model_name,
        'version': model_version
    }
    
    joblib.dump(model_data, model_path)
    
    # Store in database
    # Deactivate old models
    db.execute(text("""
        UPDATE ml_models SET is_active = false 
        WHERE model_type = 'personalization' AND is_active = true
    """))
    
    model_record = MLModel(
        model_type='personalization',
        version=model_version,
        params={
            'model_algorithm': best_model_name,
            'feature_count': len(feature_names),
            'training_samples': len(X_train),
            'positive_samples': int(sum(y_train))
        },
        metrics={
            'auc': float(best_result['auc_score']),
            'cv_auc_mean': float(best_result['cv_mean']),
            'cv_auc_std': float(best_result['cv_std']),
            'training_samples': len(X_train)
        },
        model_path=model_path,
        is_active=True
    )
    
    db.add(model_record)
    db.commit()
    
    return {
        'success': True,
        'model_type': best_model_name,
        'auc': best_result['auc_score'],
        'cv_auc': f"{best_result['cv_mean']:.3f} (+/- {best_result['cv_std']*2:.3f})",
        'training_samples': len(X_train),
        'positive_samples': int(sum(y_train)),
        'feature_count': len(feature_names),
        'model_path': model_path
    }

def main():
    """Train advanced personalization model"""
    logger.info("Starting advanced personalization model training...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Build advanced training dataset
        logger.info("Building advanced feature dataset...")
        X, y, feature_names = build_advanced_training_dataset(
            db, lookback_days=45, min_interactions=1  # Lower threshold for more data
        )
        
        logger.info(f"Training dataset: {len(X)} samples, {len(feature_names)} features")
        logger.info(f"Positive samples: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Train multiple models
        results = train_multiple_models(X_train, X_test, y_train, y_test, feature_names)
        
        # Save best model
        result = save_best_model(db, results, feature_names, X_train, y_train)
        
        logger.info(f"\n✅ Advanced model training successful!")
        logger.info(f"   Best Model: {result['model_type']}")
        logger.info(f"   AUC Score: {result['auc']:.3f}")
        logger.info(f"   CV AUC: {result['cv_auc']}")
        logger.info(f"   Training samples: {result['training_samples']}")
        logger.info(f"   Features: {result['feature_count']}")
        logger.info(f"   Model saved to: {result['model_path']}")
        
        return 0
            
    except Exception as e:
        logger.error(f"❌ Advanced training failed: {e}")
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())