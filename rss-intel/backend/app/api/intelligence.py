#!/usr/bin/env python3
"""
Intelligence API Router

REST API endpoints for RSS Intelligence advanced AI features:
- Trend detection and analysis
- Content classification and categorization
- Sentiment analysis
- Keyword extraction and tagging
- Content quality assessment
- Similarity detection and duplicate identification
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..deps import get_db
from ..store import Article
from ..intelligence import (
    trend_detector, continuous_trend_detection, get_current_trends,
    content_classifier, classify_content_batch,
    sentiment_analyzer, analyze_sentiment_batch,
    keyword_extractor, extract_keywords_batch,
    quality_scorer, score_content_quality,
    similarity_detector, detect_similar_content,
    spam_detector
)

router = APIRouter()

# Trend Detection Endpoints
@router.get("/trends/current")
async def get_active_trends(
    limit: int = Query(20, le=50, description="Maximum number of trends to return"),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0, description="Minimum trend confidence")
):
    """Get currently active trends with high confidence."""
    try:
        trends = get_current_trends(limit=limit, min_confidence=min_confidence)
        return {
            "trends": [
                {
                    "name": trend.name,
                    "confidence": trend.confidence,
                    "article_count": trend.article_count,
                    "keywords": trend.keywords,
                    "sources": trend.sources,
                    "first_seen": trend.first_seen.isoformat() if trend.first_seen else None,
                    "last_updated": trend.last_updated.isoformat() if trend.last_updated else None,
                    "trend_type": trend.trend_type,
                    "growth_rate": trend.growth_rate
                }
                for trend in trends
            ],
            "total": len(trends),
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")

@router.post("/trends/detect")
async def detect_trends_in_articles(
    article_ids: List[int],
    db: Session = Depends(get_db)
):
    """Detect trends in a specific set of articles."""
    try:
        # Get articles from database
        articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")
        
        # Convert to trend detection format
        content_items = [
            {
                "id": str(article.id),
                "title": article.title,
                "content": article.content or "",
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at
            }
            for article in articles
        ]
        
        # Run trend detection
        trends = trend_detector.detect_trends(content_items)
        
        return {
            "detected_trends": [
                {
                    "name": trend.name,
                    "confidence": trend.confidence,
                    "article_count": trend.article_count,
                    "keywords": trend.keywords,
                    "sources": trend.sources,
                    "trend_type": trend.trend_type,
                    "growth_rate": trend.growth_rate
                }
                for trend in trends
            ],
            "analyzed_articles": len(articles),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend detection failed: {str(e)}")

# Content Classification Endpoints
@router.get("/classify/{article_id}")
async def classify_article_content(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Classify a single article's content into categories."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Classify content
        result = content_classifier.classify_content(
            title=article.title,
            content=article.content or "",
            url=article.url,
            source=article.source
        )
        
        return {
            "article_id": article_id,
            "primary_category": result.primary_category.name,
            "confidence": result.confidence,
            "all_categories": [
                {
                    "category": cat_score.category.name,
                    "score": cat_score.score,
                    "confidence": cat_score.confidence
                }
                for cat_score in result.category_scores
            ],
            "classification_reasons": result.classification_reasons,
            "analysis_timestamp": result.analysis_timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@router.post("/classify/batch")
async def classify_multiple_articles(
    article_ids: List[int],
    db: Session = Depends(get_db)
):
    """Classify multiple articles in batch."""
    try:
        articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")
        
        # Prepare content items
        content_items = [
            {
                "id": str(article.id),
                "title": article.title,
                "content": article.content or "",
                "url": article.url,
                "source": article.source
            }
            for article in articles
        ]
        
        # Run batch classification
        results = classify_content_batch(content_items)
        
        return {
            "classifications": [
                {
                    "article_id": int(result.content_id),
                    "primary_category": result.primary_category.name,
                    "confidence": result.confidence,
                    "top_categories": [
                        {
                            "category": cat_score.category.name,
                            "score": cat_score.score
                        }
                        for cat_score in result.category_scores[:3]
                    ]
                }
                for result in results
            ],
            "processed_articles": len(results),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch classification failed: {str(e)}")

# Sentiment Analysis Endpoints
@router.get("/sentiment/{article_id}")
async def analyze_article_sentiment(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Analyze sentiment of a single article."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Analyze sentiment
        result = sentiment_analyzer.analyze_sentiment(
            title=article.title,
            content=article.content or "",
            source=article.source
        )
        
        return {
            "article_id": article_id,
            "overall_sentiment": {
                "polarity": result.overall_sentiment.polarity,
                "subjectivity": result.overall_sentiment.subjectivity,
                "confidence": result.overall_sentiment.confidence,
                "label": result.overall_sentiment.label
            },
            "title_sentiment": {
                "polarity": result.title_sentiment.polarity,
                "subjectivity": result.title_sentiment.subjectivity,
                "confidence": result.title_sentiment.confidence,
                "label": result.title_sentiment.label
            } if result.title_sentiment else None,
            "content_sentiment": {
                "polarity": result.content_sentiment.polarity,
                "subjectivity": result.content_sentiment.subjectivity,
                "confidence": result.content_sentiment.confidence,
                "label": result.content_sentiment.label
            } if result.content_sentiment else None,
            "emotions": {
                emotion: score for emotion, score in result.emotions.items()
            },
            "context_factors": result.context_factors,
            "analysis_timestamp": result.analysis_timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")

# Keyword Extraction Endpoints
@router.get("/keywords/{article_id}")
async def extract_article_keywords(
    article_id: int,
    max_keywords: int = Query(20, le=50, description="Maximum keywords to extract"),
    db: Session = Depends(get_db)
):
    """Extract keywords from a single article."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Extract keywords
        result = keyword_extractor.extract_keywords(
            title=article.title,
            content=article.content or "",
            url=article.url,
            max_keywords=max_keywords
        )
        
        return {
            "article_id": article_id,
            "keywords": [
                {
                    "keyword": kw.keyword,
                    "score": kw.score,
                    "method": kw.method,
                    "category": kw.category,
                    "confidence": kw.confidence
                }
                for kw in result.keywords
            ],
            "entities": result.entities,
            "key_phrases": result.key_phrases,
            "content_tags": result.content_tags,
            "extraction_methods": result.extraction_methods,
            "analysis_timestamp": result.analysis_timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keyword extraction failed: {str(e)}")

# Quality Assessment Endpoints
@router.get("/quality/{article_id}")
async def assess_article_quality(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Assess the quality of a single article."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Assess quality
        result = quality_scorer.score_content_quality(
            title=article.title,
            content=article.content or "",
            source_url=article.url,
            author="",  # Could be extracted if available
            publish_date=article.published_at
        )
        
        return {
            "article_id": article_id,
            "overall_score": result.overall_score,
            "quality_grade": result.quality_grade,
            "quality_dimensions": [
                {
                    "dimension": score.dimension,
                    "score": score.score,
                    "indicators": score.indicators,
                    "confidence": score.confidence
                }
                for score in result.quality_scores
            ],
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "recommendations": result.recommendations,
            "analysis_timestamp": result.analysis_timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality assessment failed: {str(e)}")

# Similarity Detection Endpoints
@router.get("/similarity/{article_id}")
async def find_similar_articles(
    article_id: int,
    similarity_types: List[str] = Query(
        default=["duplicate", "near_duplicate", "related"], 
        description="Types of similarity to detect"
    ),
    db: Session = Depends(get_db)
):
    """Find articles similar to the specified article."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Ensure article is in similarity detector
        similarity_detector.add_content(
            content_id=str(article.id),
            title=article.title,
            content=article.content or "",
            url=article.url
        )
        
        # Find similar content
        result = similarity_detector.detect_similar_content(
            content_id=str(article.id),
            similarity_types=similarity_types
        )
        
        return {
            "article_id": article_id,
            "similar_matches": [
                {
                    "similar_article_id": int(match.content_id_2),
                    "similarity_score": match.similarity_score,
                    "similarity_type": match.similarity_type,
                    "matching_elements": match.matching_elements,
                    "confidence": match.confidence
                }
                for match in result.similar_matches
            ],
            "duplicate_matches": [
                {
                    "duplicate_article_id": int(match.content_id_2),
                    "similarity_score": match.similarity_score,
                    "matching_elements": match.matching_elements,
                    "confidence": match.confidence
                }
                for match in result.duplicate_matches
            ],
            "related_matches": [
                {
                    "related_article_id": int(match.content_id_2),
                    "similarity_score": match.similarity_score,
                    "similarity_type": match.similarity_type,
                    "matching_elements": match.matching_elements,
                    "confidence": match.confidence
                }
                for match in result.related_matches
            ],
            "total_matches_found": result.total_matches_found,
            "analysis_timestamp": result.analysis_timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity detection failed: {str(e)}")

@router.post("/similarity/add-articles")
async def add_articles_to_similarity_index(
    article_ids: List[int],
    db: Session = Depends(get_db)
):
    """Add multiple articles to the similarity detection index."""
    try:
        articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")
        
        added_count = 0
        for article in articles:
            try:
                similarity_detector.add_content(
                    content_id=str(article.id),
                    title=article.title,
                    content=article.content or "",
                    url=article.url
                )
                added_count += 1
            except Exception as e:
                print(f"Failed to add article {article.id} to similarity index: {e}")
        
        return {
            "message": f"Added {added_count} articles to similarity index",
            "requested": len(article_ids),
            "added": added_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add articles: {str(e)}")

# Combined Analysis Endpoints
@router.get("/analyze/{article_id}")
async def comprehensive_article_analysis(
    article_id: int,
    include_trends: bool = Query(True, description="Include trend analysis"),
    include_classification: bool = Query(True, description="Include content classification"),
    include_sentiment: bool = Query(True, description="Include sentiment analysis"),
    include_keywords: bool = Query(True, description="Include keyword extraction"),
    include_quality: bool = Query(True, description="Include quality assessment"),
    include_similarity: bool = Query(False, description="Include similarity detection"),
    db: Session = Depends(get_db)
):
    """Perform comprehensive AI analysis on a single article."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        analysis_result = {}
        
        # Classification
        if include_classification:
            try:
                classification = content_classifier.classify_content(
                    title=article.title,
                    content=article.content or "",
                    url=article.url,
                    source=article.source
                )
                analysis_result["classification"] = {
                    "primary_category": classification.primary_category.name,
                    "confidence": classification.confidence,
                    "top_categories": [
                        {"category": cs.category.name, "score": cs.score}
                        for cs in classification.category_scores[:3]
                    ]
                }
            except Exception as e:
                analysis_result["classification"] = {"error": str(e)}
        
        # Sentiment Analysis
        if include_sentiment:
            try:
                sentiment = sentiment_analyzer.analyze_sentiment(
                    title=article.title,
                    content=article.content or "",
                    source=article.source
                )
                analysis_result["sentiment"] = {
                    "overall_sentiment": {
                        "polarity": sentiment.overall_sentiment.polarity,
                        "label": sentiment.overall_sentiment.label,
                        "confidence": sentiment.overall_sentiment.confidence
                    },
                    "top_emotions": [
                        {"emotion": emotion, "score": score}
                        for emotion, score in sorted(sentiment.emotions.items(), key=lambda x: x[1], reverse=True)[:3]
                        if score > 0.1
                    ]
                }
            except Exception as e:
                analysis_result["sentiment"] = {"error": str(e)}
        
        # Keyword Extraction
        if include_keywords:
            try:
                keywords = keyword_extractor.extract_keywords(
                    title=article.title,
                    content=article.content or "",
                    url=article.url,
                    max_keywords=15
                )
                analysis_result["keywords"] = {
                    "top_keywords": [
                        {"keyword": kw.keyword, "score": kw.score, "method": kw.method}
                        for kw in keywords.keywords[:10]
                    ],
                    "entities": keywords.entities[:5],
                    "key_phrases": keywords.key_phrases[:5]
                }
            except Exception as e:
                analysis_result["keywords"] = {"error": str(e)}
        
        # Quality Assessment
        if include_quality:
            try:
                quality = quality_scorer.score_content_quality(
                    title=article.title,
                    content=article.content or "",
                    source_url=article.url,
                    publish_date=article.published_at
                )
                analysis_result["quality"] = {
                    "overall_score": quality.overall_score,
                    "grade": quality.quality_grade,
                    "top_strengths": quality.strengths[:3],
                    "main_weaknesses": quality.weaknesses[:3]
                }
            except Exception as e:
                analysis_result["quality"] = {"error": str(e)}
        
        # Similarity Detection (optional, more expensive)
        if include_similarity:
            try:
                # Add to index first
                similarity_detector.add_content(
                    content_id=str(article.id),
                    title=article.title,
                    content=article.content or "",
                    url=article.url
                )
                
                similarity = similarity_detector.detect_similar_content(
                    content_id=str(article.id),
                    similarity_types=["duplicate", "related"]
                )
                analysis_result["similarity"] = {
                    "duplicate_count": len(similarity.duplicate_matches),
                    "related_count": len(similarity.related_matches),
                    "top_similar": [
                        {"article_id": int(match.content_id_2), "score": match.similarity_score, "type": match.similarity_type}
                        for match in similarity.similar_matches[:3]
                    ]
                }
            except Exception as e:
                analysis_result["similarity"] = {"error": str(e)}
        
        return {
            "article_id": article_id,
            "article_title": article.title,
            "article_source": article.source,
            "analysis": analysis_result,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")

# Spam Detection Endpoints
@router.post("/spam/detect")
async def detect_spam_content(
    title: str,
    content: str,
    source: Optional[str] = None
):
    """Detect spam, promotional content, and quality issues."""
    try:
        result = spam_detector.detect_spam(title, content, source)
        
        return {
            "is_spam": result.is_spam,
            "spam_probability": result.spam_probability,
            "recommendation": result.recommendation,
            "content_score": result.content_score,
            "title_content_coherence": result.title_content_coherence,
            "spam_signals": [
                {
                    "type": signal.type,
                    "confidence": signal.confidence,
                    "reason": signal.reason,
                    "evidence": signal.evidence
                }
                for signal in result.spam_signals
            ],
            "quality_issues": [
                {
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "description": issue.description,
                    "confidence": issue.confidence,
                    "affected_sections": issue.affected_sections
                }
                for issue in result.quality_issues
            ],
            "summary": spam_detector.get_spam_summary(result),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spam detection failed: {str(e)}")

@router.get("/spam/analyze/{article_id}")
async def analyze_article_spam(
    article_id: int,
    db: Session = Depends(get_db)
):
    """Analyze spam probability and quality issues for existing article."""
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        result = spam_detector.detect_spam(
            title=article.title,
            content=article.content or "",
            source=article.source
        )
        
        return {
            "article_id": article_id,
            "is_spam": result.is_spam,
            "spam_probability": result.spam_probability,
            "recommendation": result.recommendation,
            "content_score": result.content_score,
            "title_content_coherence": result.title_content_coherence,
            "spam_signals": [
                {
                    "type": signal.type,
                    "confidence": signal.confidence,
                    "reason": signal.reason,
                    "evidence_count": len(signal.evidence)
                }
                for signal in result.spam_signals
            ],
            "quality_issues_count": len(result.quality_issues),
            "summary": spam_detector.get_spam_summary(result),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Article spam analysis failed: {str(e)}")

@router.post("/spam/batch-analyze")
async def batch_analyze_spam(
    article_ids: List[int],
    db: Session = Depends(get_db)
):
    """Analyze spam probability for multiple articles."""
    try:
        if len(article_ids) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 articles per batch")
        
        articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
        
        results = []
        for article in articles:
            result = spam_detector.detect_spam(
                title=article.title,
                content=article.content or "",
                source=article.source
            )
            
            results.append({
                "article_id": article.id,
                "is_spam": result.is_spam,
                "spam_probability": result.spam_probability,
                "recommendation": result.recommendation,
                "content_score": result.content_score,
                "signal_count": len(result.spam_signals),
                "issue_count": len(result.quality_issues)
            })
        
        # Summary statistics
        total_articles = len(results)
        spam_count = sum(1 for r in results if r["is_spam"])
        avg_spam_prob = sum(r["spam_probability"] for r in results) / total_articles if total_articles > 0 else 0
        avg_content_score = sum(r["content_score"] for r in results) / total_articles if total_articles > 0 else 0
        
        return {
            "results": results,
            "summary": {
                "total_articles": total_articles,
                "spam_detected": spam_count,
                "spam_rate": spam_count / total_articles if total_articles > 0 else 0,
                "average_spam_probability": avg_spam_prob,
                "average_content_score": avg_content_score
            },
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch spam analysis failed: {str(e)}")

# System Status Endpoints
@router.get("/status")
async def get_intelligence_system_status():
    """Get status of all intelligence components."""
    try:
        return {
            "trend_detector": {
                "active": True,
                "current_trends_count": len(get_current_trends(limit=100)),
            },
            "content_classifier": {
                "active": True,
                "available_categories": [cat.name for cat in content_classifier.categories],
            },
            "sentiment_analyzer": {
                "active": True,
                "supported_emotions": ["joy", "anger", "fear", "sadness", "surprise", "trust", "disgust", "anticipation"]
            },
            "keyword_extractor": {
                "active": True,
                "extraction_methods": ["tfidf", "textrank", "pattern_based", "entity_recognition"]
            },
            "quality_scorer": {
                "active": True,
                "quality_dimensions": ["readability", "informativeness", "credibility", "engagement", "technical_accuracy", "source_reliability"]
            },
            "similarity_detector": {
                "active": True,
                "indexed_content_count": len(similarity_detector.content_fingerprints),
                "similarity_types": ["duplicate", "near_duplicate", "related", "semantic"]
            },
            "spam_detector": {
                "active": True,
                "detection_types": ["promotional_content", "future_events_spam", "thin_content", "title_mismatch", "clickbait"],
                "quality_assessments": ["title_coherence", "content_quality", "readability", "spam_probability"]
            },
            "system_timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")