"""
Personalization engine for RSS Intelligence
Uses user events to train a model that predicts read probability
"""
import numpy as np
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
import joblib
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..store import Event, Article, MLModel, Prediction, ArticleVector


class PersonalizationEngine:
    """Personalization engine using ML to predict user reading behavior"""
    
    def __init__(self, db: Session):
        self.db = db
        self.model = None
        self.scaler = None
        self.model_version = "1.0"
        
    def extract_features(self, article: Article) -> Dict[str, float]:
        """Extract features from an article for ML prediction"""
        
        # Basic article features
        features = {
            'title_length': len(article.title) if article.title else 0,
            'has_image': float(article.has_image or False),
            'score_total': float(article.score_total or 0),
            'has_content': float(bool(article.content)),
            'has_extracted_content': float(bool(article.full_content)),
            'extraction_success': float(article.extraction_status == 'success'),
        }
        
        # Source features (hashed for categorical encoding)
        source_hash = hashlib.md5(article.source.encode()).hexdigest()[:8]
        features['source_hash'] = float(int(source_hash, 16)) / (16**8)  # Normalize to 0-1
        
        # Time features
        if article.published_at:
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            pub_date = article.published_at
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            hours_since_published = (now_utc - pub_date).total_seconds() / 3600
            features['hours_since_published'] = hours_since_published
            features['recency_score'] = max(0, 1 - (hours_since_published / 168))  # Decay over 1 week
        else:
            features['hours_since_published'] = 0
            features['recency_score'] = 0
            
        # Score breakdown features
        if article.scores:
            features['keyword_score'] = float(article.scores.get('keywords', 0))
            features['source_score'] = float(article.scores.get('source', 0))
            features['recency_component'] = float(article.scores.get('recency', 0))
            features['watchlist_score'] = float(article.scores.get('watchlist', 0))
        else:
            features['keyword_score'] = 0
            features['source_score'] = 0
            features['recency_component'] = 0
            features['watchlist_score'] = 0
            
        # Topic features
        if article.topics:
            features['num_topics'] = float(len(article.topics))
            # One-hot encode common topics (simplified)
            common_topics = ['ai', 'crypto', 'blockchain', 'fintech', 'tech', 'ml', 'machine learning']
            for topic in common_topics:
                features[f'topic_{topic}'] = float(any(topic.lower() in t.lower() for t in article.topics))
        else:
            features['num_topics'] = 0
            common_topics = ['ai', 'crypto', 'blockchain', 'fintech', 'tech', 'ml', 'machine learning']
            for topic in common_topics:
                features[f'topic_{topic}'] = 0
        
        return features
    
    def create_training_data(self, lookback_days: int = 30) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Create training data from user events"""
        
        # Get articles from the last N days with events
        from datetime import timezone
        since_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        
        # Query articles with events
        articles_with_events = self.db.execute(text("""
            SELECT a.id, a.title, a.source, a.published_at, a.content, a.full_content, 
                   a.extraction_status, a.score_total, a.scores::text as scores_json, 
                   array_to_string(a.topics, ',') as topics_str, a.has_image,
                   CASE 
                       WHEN EXISTS(SELECT 1 FROM events e WHERE e.article_id = a.id 
                                  AND e.type IN ('open', 'external_click', 'star') 
                                  AND e.created_at >= :since_date) THEN 1
                       ELSE 0
                   END as is_positive
            FROM articles a
            JOIN events e ON e.article_id = a.id
            WHERE e.created_at >= :since_date
            AND a.published_at >= :since_date
            GROUP BY a.id, a.title, a.source, a.published_at, a.content, a.full_content,
                     a.extraction_status, a.score_total, a.scores::text, a.topics, a.has_image
        """), {"since_date": since_date}).fetchall()
        
        if len(articles_with_events) < 10:
            raise ValueError(f"Not enough training data: only {len(articles_with_events)} samples")
        
        # Extract features and labels
        X_data = []
        y_data = []
        feature_names = None
        
        for row in articles_with_events:
            # Parse JSON scores and topics
            import json
            try:
                scores_dict = json.loads(row.scores_json) if row.scores_json and row.scores_json != 'null' else {}
            except:
                scores_dict = {}
            
            topics_list = row.topics_str.split(',') if row.topics_str else []
            
            # Create article object
            article = Article(
                id=row.id,
                title=row.title,
                source=row.source,
                published_at=row.published_at,
                content=row.content,
                full_content=row.full_content,
                extraction_status=row.extraction_status,
                score_total=row.score_total,
                scores=scores_dict,
                topics=topics_list,
                has_image=row.has_image
            )
            
            features = self.extract_features(article)
            if feature_names is None:
                feature_names = list(features.keys())
            
            X_data.append([features[name] for name in feature_names])
            y_data.append(row.is_positive)
        
        return np.array(X_data), np.array(y_data), feature_names
    
    def train_model(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Train the personalization model"""
        
        try:
            # Get training data
            X, y, feature_names = self.create_training_data(lookback_days)
            
            print(f"Training on {len(X)} samples with {len(feature_names)} features")
            print(f"Positive samples: {sum(y)}, Negative samples: {len(y) - sum(y)}")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model with class balancing
            pos_weight = len(y) / (2 * sum(y)) if sum(y) > 0 else 1
            neg_weight = len(y) / (2 * (len(y) - sum(y))) if (len(y) - sum(y)) > 0 else 1
            
            self.model = LogisticRegression(
                class_weight={0: neg_weight, 1: pos_weight},
                random_state=42,
                max_iter=1000
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            auc_score = roc_auc_score(y_test, y_pred_proba)
            
            # Save model
            model_path = self.save_model(feature_names)
            
            # Store model metadata in database
            model_record = MLModel(
                model_type='personalization',
                version=self.model_version,
                params={
                    'lookback_days': lookback_days,
                    'feature_names': feature_names,
                    'training_samples': len(X),
                    'positive_samples': int(sum(y))
                },
                metrics={
                    'auc': float(auc_score),
                    'training_samples': len(X_train),
                    'test_samples': len(X_test)
                },
                model_path=model_path,
                is_active=True
            )
            
            # Deactivate old models
            self.db.execute(text("""
                UPDATE ml_models SET is_active = false 
                WHERE model_type = 'personalization' AND is_active = true
            """))
            
            self.db.add(model_record)
            self.db.commit()
            
            return {
                'success': True,
                'auc': float(auc_score),
                'training_samples': len(X),
                'positive_samples': int(sum(y)),
                'model_path': model_path,
                'feature_names': feature_names
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_model(self, feature_names: List[str]) -> str:
        """Save the trained model to disk"""
        
        model_dir = "/app/models"
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = f"{model_dir}/personalization_v{self.model_version}.pkl"
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': feature_names,
            'version': self.model_version
        }
        
        joblib.dump(model_data, model_path)
        return model_path
    
    def load_model(self, model_path: str = None):
        """Load a saved model"""
        
        if not model_path:
            # Load active model from database
            model_record = self.db.query(MLModel).filter_by(
                model_type='personalization',
                is_active=True
            ).first()
            
            if not model_record or not model_record.model_path:
                return False
                
            model_path = model_record.model_path
        
        if not os.path.exists(model_path):
            return False
        
        try:
            model_data = joblib.load(model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict_read_probability(self, article: Article) -> float:
        """Predict the probability that user will read this article"""
        
        if not self.model or not self.scaler:
            if not self.load_model():
                return 0.5  # Default probability if no model available
        
        try:
            features = self.extract_features(article)
            X = np.array([[features[name] for name in self.feature_names]])
            X_scaled = self.scaler.transform(X)
            
            probability = self.model.predict_proba(X_scaled)[0][1]
            return float(probability)
            
        except Exception as e:
            print(f"Error predicting: {e}")
            return 0.5
    
    def score_articles_batch(self, article_ids: List[int], limit: int = 500) -> Dict[str, Any]:
        """Score a batch of articles with read probability predictions"""
        
        if not self.model:
            if not self.load_model():
                return {'error': 'No trained model available'}
        
        # Get articles
        articles = self.db.query(Article).filter(
            Article.id.in_(article_ids[:limit])
        ).all()
        
        predictions_created = 0
        errors = 0
        
        # Get active model
        model_record = self.db.query(MLModel).filter_by(
            model_type='personalization',
            is_active=True
        ).first()
        
        if not model_record:
            return {'error': 'No active model found in database'}
        
        for article in articles:
            try:
                # Check if prediction already exists
                existing = self.db.query(Prediction).filter_by(
                    article_id=article.id,
                    model_id=model_record.id
                ).first()
                
                if existing:
                    continue  # Skip if already scored
                
                # Predict
                score = self.predict_read_probability(article)
                features = self.extract_features(article)
                
                # Store prediction
                prediction = Prediction(
                    article_id=article.id,
                    model_id=model_record.id,
                    score=score,
                    features=features
                )
                
                self.db.add(prediction)
                predictions_created += 1
                
            except Exception as e:
                print(f"Error scoring article {article.id}: {e}")
                errors += 1
        
        self.db.commit()
        
        return {
            'predictions_created': predictions_created,
            'errors': errors,
            'total_processed': len(articles)
        }