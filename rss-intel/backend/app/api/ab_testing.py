"""A/B Testing API endpoints"""
import logging
from datetime import datetime
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..ab_testing import ABTestingFramework, ExperimentVariant
from ..auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ab", tags=["ab_testing"])

class CreateVariantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(..., ge=0.0, le=1.0)
    params: Dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", max_length=500)

class CreateExperimentRequest(BaseModel):
    experiment_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    variants: List[CreateVariantRequest] = Field(..., min_items=2, max_items=5)
    traffic_allocation: float = Field(default=0.1, ge=0.01, le=1.0)
    target_metric: str = Field(default="engagement_rate", max_length=100)
    min_sample_size: int = Field(default=100, ge=10, le=10000)
    duration_days: int = Field(default=30, ge=1, le=365)

class RecordMetricRequest(BaseModel):
    experiment_id: str
    metric_name: str
    metric_value: float

@router.post("/experiments")
async def create_experiment(
    request: CreateExperimentRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new A/B test experiment"""
    try:
        ab_framework = ABTestingFramework(db)
        
        # Convert request to framework objects
        variants = [
            ExperimentVariant(
                name=v.name,
                weight=v.weight,
                params=v.params,
                description=v.description
            )
            for v in request.variants
        ]
        
        success = ab_framework.create_experiment(
            experiment_id=request.experiment_id,
            name=request.name,
            description=request.description,
            variants=variants,
            traffic_allocation=request.traffic_allocation,
            target_metric=request.target_metric,
            min_sample_size=request.min_sample_size,
            duration_days=request.duration_days,
            created_by=current_user['username']
        )
        
        if success:
            return {
                'status': 'success',
                'experiment_id': request.experiment_id,
                'message': 'Experiment created successfully',
                'next_step': f'Start the experiment with POST /api/ab/experiments/{request.experiment_id}/start'
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create experiment")
            
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/experiments/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Start an A/B test experiment"""
    try:
        ab_framework = ABTestingFramework(db)
        success = ab_framework.start_experiment(experiment_id)
        
        if success:
            return {
                'status': 'success',
                'experiment_id': experiment_id,
                'message': 'Experiment started successfully'
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start experiment")
            
    except Exception as e:
        logger.error(f"Error starting experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/experiments/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Stop an A/B test experiment"""
    try:
        ab_framework = ABTestingFramework(db)
        success = ab_framework.stop_experiment(experiment_id)
        
        if success:
            return {
                'status': 'success',
                'experiment_id': experiment_id,
                'message': 'Experiment stopped successfully'
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to stop experiment")
            
    except Exception as e:
        logger.error(f"Error stopping experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments")
async def list_experiments(
    active_only: bool = Query(default=True, description="Only return active experiments"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List A/B test experiments"""
    try:
        ab_framework = ABTestingFramework(db)
        
        if active_only:
            experiments = ab_framework.get_active_experiments()
        else:
            # Would implement get_all_experiments() method
            experiments = ab_framework.get_active_experiments()
        
        return {
            'experiments': experiments,
            'count': len(experiments),
            'active_only': active_only
        }
        
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments/{experiment_id}/assignment")
async def get_user_assignment(
    experiment_id: str,
    user_id: str = Query(..., description="User ID to get assignment for"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get user's variant assignment for an experiment"""
    try:
        ab_framework = ABTestingFramework(db)
        assignment = ab_framework.get_user_assignment(experiment_id, user_id)
        
        if assignment:
            return {
                'experiment_id': experiment_id,
                'user_id': user_id,
                'assigned': True,
                **assignment
            }
        else:
            return {
                'experiment_id': experiment_id,
                'user_id': user_id,
                'assigned': False,
                'reason': 'User not in experiment or experiment not active'
            }
        
    except Exception as e:
        logger.error(f"Error getting user assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/metrics")
async def record_metric(
    request: RecordMetricRequest,
    user_id: str = Query(..., description="User ID to record metric for"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Record a metric value for a user in an experiment"""
    try:
        ab_framework = ABTestingFramework(db)
        success = ab_framework.record_metric(
            request.experiment_id,
            user_id,
            request.metric_name,
            request.metric_value
        )
        
        if success:
            return {
                'status': 'success',
                'message': 'Metric recorded successfully'
            }
        else:
            return {
                'status': 'skipped',
                'message': 'User not in experiment or metric not recorded'
            }
        
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get statistical results for an A/B test experiment"""
    try:
        ab_framework = ABTestingFramework(db)
        results = ab_framework.get_experiment_results(experiment_id)
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting experiment results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/personalization/{user_id}")
async def get_personalization_params(
    user_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get personalization parameters for a user based on active A/B tests"""
    try:
        ab_framework = ABTestingFramework(db)
        active_experiments = ab_framework.get_active_experiments()
        
        # Get user's assignments and aggregate parameters
        user_params = {
            'boost_factor': 0.3,  # Default
            'personalization_enabled': True,
            'search_alpha': 0.7,
            'experiments': {}
        }
        
        for experiment in active_experiments:
            assignment = ab_framework.get_user_assignment(experiment['id'], user_id)
            if assignment:
                # Merge experiment parameters
                user_params['experiments'][experiment['id']] = {
                    'variant': assignment['variant'],
                    'params': assignment['params']
                }
                
                # Apply experiment parameters
                if 'boost_factor' in assignment['params']:
                    user_params['boost_factor'] = assignment['params']['boost_factor']
                if 'search_alpha' in assignment['params']:
                    user_params['search_alpha'] = assignment['params']['search_alpha']
                if 'personalization_enabled' in assignment['params']:
                    user_params['personalization_enabled'] = assignment['params']['personalization_enabled']
        
        return {
            'user_id': user_id,
            'params': user_params,
            'active_experiments': len(user_params['experiments']),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting personalization params: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def ab_testing_health(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Check health of A/B testing system"""
    try:
        ab_framework = ABTestingFramework(db)
        active_experiments = ab_framework.get_active_experiments()
        
        # Check if tables exist
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1 FROM ab_experiments LIMIT 1"))
            tables_exist = True
        except:
            tables_exist = False
        
        health_score = 1.0 if tables_exist else 0.0
        status = 'healthy' if health_score >= 0.8 else 'unhealthy'
        
        return {
            'status': status,
            'health_score': health_score,
            'checks': {
                'tables_exist': {
                    'status': 'pass' if tables_exist else 'fail',
                    'message': 'A/B testing tables exist' if tables_exist else 'A/B testing tables missing'
                },
                'active_experiments': {
                    'status': 'info',
                    'message': f'{len(active_experiments)} active experiments'
                }
            },
            'active_experiments': len(active_experiments),
            'system_ready': tables_exist
        }
        
    except Exception as e:
        logger.error(f"Error checking A/B testing health: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'health_score': 0.0
        }