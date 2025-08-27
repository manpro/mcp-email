#!/usr/bin/env python3
"""
Run spam detection on existing articles to test the new filtering system
"""
import os
import sys
from datetime import datetime

# Add the app directory to Python path
sys.path.append('/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.scoring import ScoringEngine

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rss:changeme@postgres:5432/rssintel")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def analyze_articles_for_spam():
    """Analyze existing articles for spam patterns"""
    db = SessionLocal()
    
    try:
        # Get all articles with title and content
        articles = db.execute(text("""
            SELECT id, title, content, url, source, published_at,
                   COALESCE(score_total, 0) as current_score
            FROM articles 
            WHERE title IS NOT NULL
            ORDER BY published_at DESC
            LIMIT 1000
        """)).fetchall()
        
        print(f"Analyzing {len(articles)} articles for spam patterns...")
        
        score_engine = ScoringEngine()
        spam_detected = 0
        high_spam_risk = 0
        total_processed = 0
        
        spam_articles = []
        all_penalties = []
        
        for article in articles:
            try:
                # Create a mock article object
                class MockArticle:
                    def __init__(self, row):
                        self.id = row.id
                        self.title = row.title or ""
                        self.content = row.content or ""
                        self.url = row.url
                        self.source = row.source
                        self.published_at = row.published_at
                        self.current_score = row.current_score
                
                mock_article = MockArticle(article)
                
                # Calculate quality penalty (our spam detection)
                penalty = score_engine._calculate_quality_penalty(
                    mock_article.title, 
                    mock_article.content or "", 
                    mock_article.source or "unknown",
                    mock_article.published_at
                )
                
                # Consider it spam if penalty >= 10 (very low threshold for analysis)
                is_spam = penalty >= 10
                is_high_risk = penalty >= 5
                
                if is_spam:
                    spam_detected += 1
                    spam_articles.append({
                        'id': article.id,
                        'title': article.title,
                        'url': article.url,
                        'source': article.source,
                        'penalty': penalty,
                        'current_score': article.current_score
                    })
                elif is_high_risk:
                    high_spam_risk += 1
                
                # Track all penalties for analysis
                if penalty > 0:
                    all_penalties.append({
                        'id': article.id,
                        'title': article.title[:50] + "..." if len(article.title) > 50 else article.title,
                        'penalty': penalty,
                        'source': article.source
                    })
                
                total_processed += 1
                
                if total_processed % 100 == 0:
                    print(f"Processed {total_processed} articles...")
                    
            except Exception as e:
                print(f"Error processing article {article.id}: {e}")
                continue
        
        # Results summary
        print(f"\n=== SPAM DETECTION RESULTS ===")
        print(f"Total articles analyzed: {total_processed}")
        print(f"Spam detected (penalty ≥10): {spam_detected} ({spam_detected/total_processed*100:.1f}%)")
        print(f"High spam risk (penalty ≥5): {high_spam_risk} ({high_spam_risk/total_processed*100:.1f}%)")
        print(f"Clean articles: {total_processed - spam_detected - high_spam_risk}")
        
        # Show top spam articles
        if spam_articles:
            print(f"\n=== TOP SPAM ARTICLES ===")
            spam_articles.sort(key=lambda x: x['penalty'], reverse=True)
            for i, article in enumerate(spam_articles[:10]):
                print(f"{i+1}. [Penalty: {article['penalty']}] {article['title'][:80]}...")
                print(f"   Source: {article['source']} | Current Score: {article['current_score']}")
                print(f"   URL: {article['url']}")
                print()
        
        # Show penalty distribution
        if all_penalties:
            print(f"\n=== PENALTY DISTRIBUTION ===")
            all_penalties.sort(key=lambda x: x['penalty'], reverse=True)
            print(f"Articles with any penalty: {len(all_penalties)}")
            
            # Show top 20 penalties
            print(f"\nTop 20 penalties found:")
            for i, article in enumerate(all_penalties[:20]):
                print(f"{i+1}. [Penalty: {article['penalty']}] {article['title']}")
                print(f"   Source: {article['source']}")
                print()
        
        # Update database with spam flags for demonstration
        if spam_articles:
            print(f"\n=== UPDATING DATABASE ===")
            for article in spam_articles:
                try:
                    # Update ml_metadata to mark as spam-detected
                    db.execute(text("""
                        UPDATE articles 
                        SET ml_metadata = COALESCE(ml_metadata, '{}'::jsonb) || 
                                         '{"spam_detected": true, "spam_penalty": :penalty, "detection_date": :date}'::jsonb
                        WHERE id = :article_id
                    """), {
                        "article_id": article['id'],
                        "penalty": article['penalty'],
                        "date": datetime.now().isoformat()
                    })
                except Exception as e:
                    print(f"Error updating article {article['id']}: {e}")
            
            db.commit()
            print(f"Updated {len(spam_articles)} articles with spam detection flags")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    analyze_articles_for_spam()