"""A/B Testing framework for personalization parameters"""
import logging
import hashlib
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ExperimentStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

@dataclass
class ExperimentVariant:
    """A/B test variant configuration"""
    name: str
    weight: float
    params: Dict[str, Any]
    description: str

@dataclass 
class Experiment:
    """A/B test experiment definition"""
    id: str
    name: str
    description: str
    status: ExperimentStatus
    variants: List[ExperimentVariant]
    traffic_allocation: float  # 0.0 to 1.0
    start_date: datetime
    end_date: Optional[datetime]
    target_metric: str
    min_sample_size: int
    created_by: str

class ABTestingFramework:
    """Handles A/B testing for personalization parameters"""
    
    def __init__(self, db: Session):
        self.db = db
        self._ensure_experiments_table()
        
    def _ensure_experiments_table(self):
        """Create experiments table if it doesn't exist"""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS ab_experiments (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'draft',
                    variants JSONB NOT NULL,
                    traffic_allocation FLOAT DEFAULT 0.1,
                    start_date TIMESTAMPTZ,
                    end_date TIMESTAMPTZ,
                    target_metric VARCHAR(100),
                    min_sample_size INTEGER DEFAULT 100,
                    created_by VARCHAR(100),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            # Create user assignments table
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS ab_assignments (
                    id SERIAL PRIMARY KEY,
                    experiment_id VARCHAR(50) NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    variant_name VARCHAR(100) NOT NULL,
                    assigned_at TIMESTAMPTZ DEFAULT NOW(),
                    params JSONB,
                    UNIQUE(experiment_id, user_id),
                    FOREIGN KEY (experiment_id) REFERENCES ab_experiments(id) ON DELETE CASCADE
                )
            """))
            
            # Create metrics table
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS ab_metrics (
                    id SERIAL PRIMARY KEY,
                    experiment_id VARCHAR(50) NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    variant_name VARCHAR(100) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value FLOAT NOT NULL,
                    recorded_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (experiment_id) REFERENCES ab_experiments(id) ON DELETE CASCADE
                )
            """))
            
            self.db.commit()
            logger.info("A/B testing tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating A/B testing tables: {e}")
            self.db.rollback()
    
    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        description: str,
        variants: List[ExperimentVariant],
        traffic_allocation: float = 0.1,
        target_metric: str = "engagement_rate",
        min_sample_size: int = 100,
        duration_days: int = 30,
        created_by: str = "system"
    ) -> bool:
        """Create a new A/B test experiment"""
        try:
            # Validate variants
            total_weight = sum(v.weight for v in variants)
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(f"Variant weights must sum to 1.0, got {total_weight}")
            
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=duration_days)
            
            # Convert variants to JSON
            variants_json = [
                {
                    'name': v.name,
                    'weight': v.weight,
                    'params': v.params,
                    'description': v.description
                }
                for v in variants
            ]
            
            import json
            
            self.db.execute(text("""
                INSERT INTO ab_experiments (
                    id, name, description, status, variants, traffic_allocation,
                    start_date, end_date, target_metric, min_sample_size, created_by
                ) VALUES (
                    :id, :name, :description, :status, :variants, :traffic_allocation,
                    :start_date, :end_date, :target_metric, :min_sample_size, :created_by
                )
            """), {
                'id': experiment_id,
                'name': name,
                'description': description,
                'status': ExperimentStatus.DRAFT.value,
                'variants': json.dumps(variants_json),
                'traffic_allocation': traffic_allocation,
                'start_date': start_date,
                'end_date': end_date,
                'target_metric': target_metric,
                'min_sample_size': min_sample_size,
                'created_by': created_by
            })
            
            self.db.commit()
            logger.info(f"Created A/B experiment: {experiment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating experiment {experiment_id}: {e}")
            self.db.rollback()
            return False
    
    def get_user_assignment(self, experiment_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's variant assignment for an experiment"""
        try:
            # Check if user already has assignment
            result = self.db.execute(text("""
                SELECT variant_name, params
                FROM ab_assignments
                WHERE experiment_id = :experiment_id AND user_id = :user_id
            """), {'experiment_id': experiment_id, 'user_id': user_id})
            
            existing = result.fetchone()
            if existing:
                import json
                params = json.loads(existing.params) if isinstance(existing.params, str) else existing.params
                return {
                    'variant': existing.variant_name,
                    'params': params
                }
            
            # Get experiment details
            exp_result = self.db.execute(text("""
                SELECT status, variants, traffic_allocation
                FROM ab_experiments
                WHERE id = :experiment_id
            """), {'experiment_id': experiment_id})
            
            experiment = exp_result.fetchone()
            if not experiment or experiment.status != ExperimentStatus.ACTIVE.value:
                return None
            
            # Check if user should be included in experiment
            user_hash = self._hash_user_experiment(user_id, experiment_id)
            if user_hash > experiment.traffic_allocation:
                return None  # User not in experiment
            
            # Parse variants JSON
            import json
            variants = json.loads(experiment.variants) if isinstance(experiment.variants, str) else experiment.variants
            
            # Assign variant based on hash
            variant = self._assign_variant(user_hash, variants)
            
            # Store assignment
            self.db.execute(text("""
                INSERT INTO ab_assignments (experiment_id, user_id, variant_name, params)
                VALUES (:experiment_id, :user_id, :variant_name, :params)
                ON CONFLICT (experiment_id, user_id) DO NOTHING
            """), {
                'experiment_id': experiment_id,
                'user_id': user_id,
                'variant_name': variant['name'],
                'params': json.dumps(variant['params'])
            })
            
            self.db.commit()
            
            return {
                'variant': variant['name'],
                'params': variant['params']
            }
            
        except Exception as e:
            logger.error(f"Error getting user assignment: {e}")
            return None
    
    def _hash_user_experiment(self, user_id: str, experiment_id: str) -> float:
        """Generate deterministic hash for user-experiment pair"""
        combined = f"{user_id}:{experiment_id}"
        hash_value = hashlib.md5(combined.encode()).hexdigest()
        # Convert to float between 0 and 1
        return int(hash_value[:8], 16) / (16**8)
    
    def _assign_variant(self, user_hash: float, variants: List[Dict]) -> Dict:
        """Assign variant based on user hash and variant weights"""
        cumulative_weight = 0.0
        
        for variant in variants:
            cumulative_weight += variant['weight']
            if user_hash <= cumulative_weight:
                return variant
        
        # Fallback to last variant
        return variants[-1]
    
    def record_metric(
        self,
        experiment_id: str,
        user_id: str,
        metric_name: str,
        metric_value: float
    ) -> bool:
        """Record a metric value for a user in an experiment"""
        try:
            # Get user's variant assignment
            assignment = self.get_user_assignment(experiment_id, user_id)
            if not assignment:
                return False
            
            self.db.execute(text("""
                INSERT INTO ab_metrics (
                    experiment_id, user_id, variant_name, metric_name, metric_value
                ) VALUES (:experiment_id, :user_id, :variant_name, :metric_name, :metric_value)
            """), {
                'experiment_id': experiment_id,
                'user_id': user_id,
                'variant_name': assignment['variant'],
                'metric_name': metric_name,
                'metric_value': metric_value
            })
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
            self.db.rollback()
            return False
    
    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Get statistical results for an experiment"""
        try:
            # Get experiment details
            exp_result = self.db.execute(text("""
                SELECT name, target_metric, variants, min_sample_size, status
                FROM ab_experiments
                WHERE id = :experiment_id
            """), {'experiment_id': experiment_id})
            
            experiment = exp_result.fetchone()
            if not experiment:
                return {'error': 'Experiment not found'}
            
            # Get assignment counts by variant
            assignment_result = self.db.execute(text("""
                SELECT variant_name, COUNT(*) as users
                FROM ab_assignments
                WHERE experiment_id = :experiment_id
                GROUP BY variant_name
            """), {'experiment_id': experiment_id})
            
            assignments = {row.variant_name: row.users for row in assignment_result}
            
            # Get metric results by variant
            metric_result = self.db.execute(text("""
                SELECT 
                    variant_name,
                    COUNT(*) as sample_size,
                    AVG(metric_value) as mean_value,
                    STDDEV(metric_value) as std_dev,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value
                FROM ab_metrics
                WHERE experiment_id = :experiment_id
                AND metric_name = :target_metric
                GROUP BY variant_name
            """), {
                'experiment_id': experiment_id,
                'target_metric': experiment.target_metric
            })
            
            variant_results = {}
            for row in metric_result:
                variant_results[row.variant_name] = {
                    'sample_size': row.sample_size,
                    'mean_value': float(row.mean_value) if row.mean_value else 0.0,
                    'std_dev': float(row.std_dev) if row.std_dev else 0.0,
                    'min_value': float(row.min_value) if row.min_value else 0.0,
                    'max_value': float(row.max_value) if row.max_value else 0.0,
                    'assigned_users': assignments.get(row.variant_name, 0)
                }
            
            # Calculate statistical significance (simplified)
            significance_results = self._calculate_significance(variant_results)
            
            return {
                'experiment_id': experiment_id,
                'experiment_name': experiment.name,
                'target_metric': experiment.target_metric,
                'status': experiment.status,
                'min_sample_size': experiment.min_sample_size,
                'variant_results': variant_results,
                'significance': significance_results,
                'total_users': sum(assignments.values()),
                'has_sufficient_data': all(
                    r.get('sample_size', 0) >= experiment.min_sample_size 
                    for r in variant_results.values()
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting experiment results: {e}")
            return {'error': str(e)}
    
    def _calculate_significance(self, variant_results: Dict) -> Dict[str, Any]:
        """Calculate statistical significance between variants (simplified)"""
        try:
            variants = list(variant_results.keys())
            if len(variants) < 2:
                return {'test': 'insufficient_variants'}
            
            # Simple comparison between first two variants
            # In production, you'd use proper statistical tests like t-test
            v1, v2 = variants[0], variants[1]
            v1_data = variant_results[v1]
            v2_data = variant_results[v2]
            
            if v1_data['sample_size'] == 0 or v2_data['sample_size'] == 0:
                return {'test': 'insufficient_data'}
            
            # Calculate effect size (Cohen's d approximation)
            mean_diff = abs(v1_data['mean_value'] - v2_data['mean_value'])
            pooled_std = ((v1_data['std_dev'] + v2_data['std_dev']) / 2)
            
            if pooled_std == 0:
                effect_size = 0
            else:
                effect_size = mean_diff / pooled_std
            
            # Simplified significance test (normally would use proper statistical test)
            min_effect_size = 0.2  # Small effect size threshold
            is_significant = effect_size > min_effect_size and \
                           min(v1_data['sample_size'], v2_data['sample_size']) >= 30
            
            winner = v1 if v1_data['mean_value'] > v2_data['mean_value'] else v2
            lift = ((max(v1_data['mean_value'], v2_data['mean_value']) / 
                    min(v1_data['mean_value'], v2_data['mean_value'])) - 1) * 100 \
                   if min(v1_data['mean_value'], v2_data['mean_value']) > 0 else 0
            
            return {
                'test': 'simplified_comparison',
                'compared_variants': [v1, v2],
                'effect_size': round(effect_size, 3),
                'is_significant': is_significant,
                'winner': winner if is_significant else None,
                'lift_percent': round(lift, 2),
                'confidence': 'medium' if is_significant else 'low'
            }
            
        except Exception as e:
            logger.error(f"Error calculating significance: {e}")
            return {'test': 'error', 'error': str(e)}
    
    def get_active_experiments(self) -> List[Dict[str, Any]]:
        """Get all active experiments"""
        try:
            result = self.db.execute(text("""
                SELECT id, name, description, traffic_allocation, target_metric,
                       start_date, end_date, variants
                FROM ab_experiments
                WHERE status = 'active'
                AND (end_date IS NULL OR end_date > NOW())
                ORDER BY start_date DESC
            """))
            
            experiments = []
            for row in result:
                experiments.append({
                    'id': row.id,
                    'name': row.name,
                    'description': row.description,
                    'traffic_allocation': row.traffic_allocation,
                    'target_metric': row.target_metric,
                    'start_date': row.start_date.isoformat(),
                    'end_date': row.end_date.isoformat() if row.end_date else None,
                    'variants': [v['name'] for v in row.variants]
                })
            
            return experiments
            
        except Exception as e:
            logger.error(f"Error getting active experiments: {e}")
            return []
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment"""
        try:
            result = self.db.execute(text("""
                UPDATE ab_experiments
                SET status = 'active', updated_at = NOW()
                WHERE id = :experiment_id AND status = 'draft'
            """), {'experiment_id': experiment_id})
            
            rows_affected = result.rowcount
            self.db.commit()
            
            if rows_affected > 0:
                logger.info(f"Started experiment: {experiment_id}")
                return True
            else:
                logger.warning(f"Could not start experiment {experiment_id} - may not exist or not in draft status")
                return False
                
        except Exception as e:
            logger.error(f"Error starting experiment {experiment_id}: {e}")
            self.db.rollback()
            return False
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop an experiment"""
        try:
            result = self.db.execute(text("""
                UPDATE ab_experiments
                SET status = 'completed', updated_at = NOW()
                WHERE id = :experiment_id AND status = 'active'
            """), {'experiment_id': experiment_id})
            
            rows_affected = result.rowcount
            self.db.commit()
            
            if rows_affected > 0:
                logger.info(f"Stopped experiment: {experiment_id}")
                return True
            else:
                logger.warning(f"Could not stop experiment {experiment_id} - may not exist or not active")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping experiment {experiment_id}: {e}")
            self.db.rollback()
            return False