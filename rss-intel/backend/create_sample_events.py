#!/usr/bin/env python3
"""
Create sample user events for ML training
Simulates realistic user behavior patterns
"""

import random
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

from app.deps import get_db
from sqlalchemy import text

def create_sample_events(db, num_events=200):
    """Create sample events based on realistic user behavior"""
    
    # Get available articles
    articles = db.execute(text("""
        SELECT id, title, source, score_total, has_image, published_at
        FROM articles
        ORDER BY published_at DESC
        LIMIT 100
    """)).fetchall()
    
    if not articles:
        print("No articles found!")
        return
    
    print(f"Creating {num_events} sample events for {len(articles)} articles...")
    
    events_created = 0
    
    for _ in range(num_events):
        article = random.choice(articles)
        article_id = article.id
        
        # Simulate user behavior based on article characteristics
        # Higher scores and images increase engagement probability
        base_engagement = 0.3
        if article.score_total and article.score_total > 50:
            base_engagement += 0.3
        if article.has_image:
            base_engagement += 0.2
        if article.source in ['TechCrunch AI', 'Nature AI', 'OpenAI Blog']:
            base_engagement += 0.1
            
        # Random time in last 7 days
        event_time = datetime.utcnow() - timedelta(
            days=random.uniform(0, 7),
            hours=random.uniform(0, 24),
            minutes=random.uniform(0, 60)
        )
        
        # Always create impression event
        db.execute(text("""
            INSERT INTO events (article_id, event_type, created_at)
            VALUES (:article_id, 'impression', :created_at)
        """), {
            'article_id': article_id,
            'created_at': event_time
        })
        events_created += 1
        
        # Decide if user engages based on engagement probability
        if random.random() < base_engagement:
            # User clicks/opens article
            open_event_time = event_time + timedelta(seconds=random.uniform(1, 30))
            
            # Simulate different engagement levels
            engagement_type = random.choices([
                'open',
                'external_click',
                'star'
            ], weights=[0.7, 0.25, 0.05])[0]
            
            if engagement_type == 'open':
                # Reading time based on engagement
                duration_ms = random.randint(5000, 120000)  # 5s to 2min
                visible_ms = int(duration_ms * random.uniform(0.7, 0.9))
                scroll_pct = random.uniform(0.2, 0.9)
                
                db.execute(text("""
                    INSERT INTO events (article_id, event_type, duration_ms, visible_ms, scroll_pct, created_at)
                    VALUES (:article_id, 'open', :duration_ms, :visible_ms, :scroll_pct, :created_at)
                """), {
                    'article_id': article_id,
                    'event_type': 'open',
                    'duration_ms': duration_ms,
                    'visible_ms': visible_ms,
                    'scroll_pct': scroll_pct,
                    'created_at': open_event_time
                })
                events_created += 1
                
            elif engagement_type == 'external_click':
                db.execute(text("""
                    INSERT INTO events (article_id, event_type, created_at)
                    VALUES (:article_id, 'external_click', :created_at)
                """), {
                    'article_id': article_id,
                    'created_at': open_event_time
                })
                events_created += 1
                
            elif engagement_type == 'star':
                db.execute(text("""
                    INSERT INTO events (article_id, event_type, created_at)
                    VALUES (:article_id, 'star', :created_at)
                """), {
                    'article_id': article_id,
                    'created_at': open_event_time
                })
                events_created += 1
        
        # Sometimes add negative signals
        elif random.random() < 0.15:  # 15% chance of explicit dismiss
            dismiss_time = event_time + timedelta(seconds=random.uniform(1, 5))
            db.execute(text("""
                INSERT INTO events (article_id, event_type, created_at)
                VALUES (:article_id, 'dismiss', :created_at)
            """), {
                'article_id': article_id,
                'created_at': dismiss_time
            })
            events_created += 1
    
    db.commit()
    print(f"✅ Created {events_created} sample events")
    
    # Show stats
    stats = db.execute(text("""
        SELECT 
            event_type,
            COUNT(*) as count,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
        FROM events
        GROUP BY event_type
        ORDER BY count DESC
    """)).fetchall()
    
    print("\n📊 Event Distribution:")
    for stat in stats:
        print(f"  {stat.event_type}: {stat.count} ({stat.percentage:.1f}%)")


if __name__ == "__main__":
    db = next(get_db())
    try:
        create_sample_events(db, num_events=300)
    finally:
        db.close()