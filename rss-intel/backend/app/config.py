from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://rss:changeme@postgres:5432/rssintel"
    
    # FreshRSS
    freshrss_base_url: str = "http://freshrss"
    freshrss_api_user: str = "ai"
    freshrss_api_pass: str = "strongpassword"
    
    # RSSHub
    rsshub_base_url: str = "http://rsshub:1200"
    
    # Weaviate
    weaviate_url: str = "http://weaviate:8080"
    
    # Backend
    backend_port: int = 8000
    
    # Scoring
    scoring_half_life_hours: float = 36
    scoring_star_threshold: int = 80
    scoring_interest_threshold: int = 60
    
    # Scheduler
    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 5  # Run every 5 minutes
    
    # Content Extraction
    content_extraction_enabled: bool = True
    content_extraction_min_score: int = 0  # Extract all articles
    content_extraction_batch_size: int = 50  # Increase batch size
    content_extraction_concurrent: int = 10  # More concurrent requests
    content_extraction_rate_limit: float = 2.0  # Faster rate limit
    content_extraction_interval_minutes: int = 30  # for standalone worker
    
    # Paths
    config_dir: str = "/app/config"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env

settings = Settings()