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
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"  # Cost-effective model for Q&A
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1  # Low temperature for factual responses
    
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
    
    # Image Proxy
    image_proxy_cache_dir: str = "/data/image-cache"
    image_proxy_max_bytes: int = 5242880  # 5MB
    image_proxy_timeout_sec: int = 8
    image_proxy_connect_sec: int = 3
    image_proxy_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119"
    image_proxy_send_referer: bool = True
    image_min_width: int = 320
    image_min_height: int = 180
    image_aspect_min: float = 0.4
    image_aspect_max: float = 3.0
    image_enable_revalidation: bool = True
    image_revalidate_after_hours: int = 168  # 7 days
    image_playwright_enabled: bool = True
    image_playwright_max_concurrency: int = 1
    image_domain_rules_path: str = "/app/config/image_rules.yml"
    
    # Paths
    config_dir: str = "/app/config"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env

settings = Settings()