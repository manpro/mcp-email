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
    
    # Backend
    backend_port: int = 8000
    
    # Scoring
    scoring_half_life_hours: float = 36
    scoring_star_threshold: int = 80
    scoring_interest_threshold: int = 60
    
    # Scheduler
    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 10
    
    # Paths
    config_dir: str = "/app/config"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env

settings = Settings()