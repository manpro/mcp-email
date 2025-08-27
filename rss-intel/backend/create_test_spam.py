#!/usr/bin/env python3
"""
Create test spam reports to demonstrate the spam management system
"""
import os
import sys
from datetime import datetime

# Add the app directory to Python path
sys.path.append('/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rss:changeme@postgres:5432/rssintel")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_test_spam_reports():
    """Create some test spam reports for demonstration"""
    db = SessionLocal()
    
    try:
        # Get some random articles
        articles = db.execute(text("""
            SELECT id, title, url, source, published_at
            FROM articles 
            WHERE title IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 5
        """)).fetchall()
        
        if not articles:
            print("No articles found to create spam reports")
            return
        
        print(f"Creating test spam reports for {len(articles)} articles...")
        
        for i, article in enumerate(articles):
            # Insert spam report
            db.execute(text("""
                INSERT INTO spam_reports (article_id, reported_at, source, reason, report_count, metadata)
                VALUES (:article_id, NOW(), :source, :reason, 1, :metadata)
                ON CONFLICT (article_id) DO NOTHING
            """), {
                "article_id": article.id,
                "source": "user_feedback" if i % 2 == 0 else "ml_detection",
                "reason": "promotional_content" if i % 2 == 0 else "advertisement",
                "metadata": '{"test": true, "created_for_demo": true}'
            })
            
            # Update article score to mark as spam
            db.execute(text("""
                UPDATE articles 
                SET score_total = -999
                WHERE id = :article_id
            """), {"article_id": article.id})
            
            print(f"Created spam report for: {article.title[:60]}...")
        
        db.commit()
        
        # Show results
        spam_count = db.execute(text("SELECT COUNT(*) FROM spam_reports")).scalar()
        print(f"\nTotal spam reports in database: {spam_count}")
        
        # Show some details
        reports = db.execute(text("""
            SELECT sr.article_id, sr.source, sr.reason, a.title, a.source as article_source
            FROM spam_reports sr
            JOIN articles a ON sr.article_id = a.id
            ORDER BY sr.reported_at DESC
            LIMIT 10
        """)).fetchall()
        
        print(f"\nRecent spam reports:")
        for report in reports:
            print(f"- [{report.article_source}] {report.title[:50]}... (Reason: {report.reason})")
        
    except Exception as e:
        print(f"Error creating test spam reports: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_spam_reports()