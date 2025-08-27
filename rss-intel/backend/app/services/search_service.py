"""
Advanced Search Service for RSS Intelligence
Provides semantic search, filtering, and search analytics
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.dialects.postgresql import TSVECTOR
import json
import numpy as np
from dataclasses import dataclass

from ..store import Article
# from ..store import SpamReport  # Disabled - model removed
from ..intelligence import similarity_detector
from ..intelligence.semantic_search import semantic_search_engine, SemanticSearchResult
from .search_cache_service import get_search_cache

logger = logging.getLogger(__name__)

@dataclass
class SearchFilter:
    """Search filter configuration"""
    sources: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_image: Optional[bool] = None
    is_starred: Optional[bool] = None
    labels: Optional[List[str]] = None
    exclude_spam: bool = True
    content_quality_min: Optional[float] = None
    sentiment: Optional[str] = None  # 'positive', 'negative', 'neutral'
    word_count_min: Optional[int] = None
    word_count_max: Optional[int] = None
    language: Optional[str] = None

@dataclass  
class SearchResult:
    """Search result with metadata"""
    article: Article
    relevance_score: float
    match_highlights: List[str]
    match_reason: str  # 'title', 'content', 'semantic', 'category'

@dataclass
class SearchResponse:
    """Complete search response"""
    results: List[SearchResult]
    total_count: int
    search_time_ms: float
    filters_applied: Dict[str, Any]
    suggestions: List[str]
    facets: Dict[str, Dict[str, int]]

class AdvancedSearchService:
    """Advanced search service with semantic capabilities"""
    
    def __init__(self, db: Session):
        self.db = db
        self._ensure_semantic_index_populated()
        
    def search(
        self,
        query: str = "",
        filters: SearchFilter = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "relevance",  # 'relevance', 'date', 'score', 'title'
        sort_order: str = "desc",
        enable_semantic: bool = True,
        highlight: bool = True
    ) -> SearchResponse:
        """
        Advanced search with multiple search methods and filtering
        """
        start_time = datetime.now()
        
        if filters is None:
            filters = SearchFilter()
        
        # Check cache first
        cache_service = get_search_cache()
        cache_key = None
        
        if cache_service and query.strip():  # Only cache actual searches
            search_params = {
                'page': page,
                'page_size': page_size,
                'sort_by': sort_by,
                'sort_order': sort_order,
                'enable_semantic': enable_semantic,
                'highlight': highlight
            }
            cache_key = cache_service.generate_search_key(
                query=query,
                filters=filters.__dict__,
                settings=search_params,
                search_type="semantic" if enable_semantic else "keyword"
            )
            
            # Try to get from cache
            cached_result = cache_service.get_search_results(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for search: {query[:50]}...")
                return cached_result
            
        try:
            # Build base query
            base_query = self.db.query(Article)
            
            # Apply filters first (most restrictive)
            base_query = self._apply_filters(base_query, filters)
            
            # Search logic
            if query.strip():
                if enable_semantic and len(query) > 10:
                    # Use semantic search for longer queries
                    results = self._semantic_search(query, base_query, page, page_size, sort_by, sort_order)
                else:
                    # Use traditional text search for short queries
                    results = self._text_search(query, base_query, page, page_size, sort_by, sort_order, highlight)
            else:
                # No query, just apply filters and sorting
                results = self._filtered_search(base_query, page, page_size, sort_by, sort_order)
            
            # Get total count for pagination
            total_count = self._get_filtered_count(filters, query if query.strip() else None)
            
            # Generate search suggestions
            suggestions = self._generate_suggestions(query, filters)
            
            # Generate facets for filtering UI
            facets = self._generate_facets(filters, query if query.strip() else None)
            
            # Calculate search time
            search_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Build response
            response = SearchResponse(
                results=results,
                total_count=total_count,
                search_time_ms=search_time,
                filters_applied=self._serialize_filters(filters),
                suggestions=suggestions,
                facets=facets
            )
            
            # Cache the response if cache service is available
            if cache_service and cache_key and query.strip():
                try:
                    # Cache for shorter time for frequently changing results
                    ttl = 300 if page == 1 else 600  # 5 min for first page, 10 min for others
                    cache_service.set_search_results(cache_key, response, 'search_results', ttl)
                    logger.debug(f"Cached search result: {query[:50]}...")
                except Exception as cache_error:
                    logger.warning(f"Failed to cache search result: {cache_error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            raise
    
    def _apply_filters(self, query, filters: SearchFilter):
        """Apply all search filters to the base query"""
        
        # Source filtering
        if filters.sources:
            query = query.filter(Article.source.in_(filters.sources))
        
        # Score range filtering    
        if filters.min_score is not None:
            query = query.filter(Article.score >= filters.min_score)
        if filters.max_score is not None:
            query = query.filter(Article.score <= filters.max_score)
            
        # Date range filtering
        if filters.date_from:
            query = query.filter(Article.published_at >= filters.date_from)
        if filters.date_to:
            query = query.filter(Article.published_at <= filters.date_to)
            
        # Image filtering
        if filters.has_image is not None:
            if filters.has_image:
                query = query.filter(Article.image_proxy_path.isnot(None))
            else:
                query = query.filter(Article.image_proxy_path.is_(None))
                
        # Starred filtering
        if filters.is_starred is not None:
            if filters.is_starred:
                query = query.filter(Article.flags.has_key('starred'))
            else:
                query = query.filter(~Article.flags.has_key('starred'))
                
        # Label filtering
        if filters.labels:
            for label in filters.labels:
                query = query.filter(Article.flags.has_key(label))
                
        # Spam filtering
        if filters.exclude_spam:
            query = query.filter(
                or_(
                    Article.spam_detected.is_(None),
                    Article.spam_detected == False
                )
            )
            
        # Content quality filtering
        if filters.content_quality_min is not None:
            query = query.filter(Article.content_quality_score >= filters.content_quality_min)
            
        # Word count filtering (approximate using content length)
        if filters.word_count_min is not None:
            # Rough estimate: average 5 characters per word
            min_chars = filters.word_count_min * 5
            query = query.filter(func.length(Article.content) >= min_chars)
            
        if filters.word_count_max is not None:
            max_chars = filters.word_count_max * 5
            query = query.filter(func.length(Article.content) <= max_chars)
            
        return query
    
    def _text_search(self, query: str, base_query, page: int, page_size: int, 
                    sort_by: str, sort_order: str, highlight: bool) -> List[SearchResult]:
        """Traditional full-text search using PostgreSQL"""
        
        results = []
        search_terms = query.lower().split()
        
        # Create text search conditions
        search_conditions = []
        
        # Title search (higher weight)
        title_conditions = []
        for term in search_terms:
            title_conditions.append(Article.title.ilike(f"%{term}%"))
        
        # Content search
        content_conditions = []
        for term in search_terms:
            content_conditions.append(Article.content.ilike(f"%{term}%"))
            
        # Source search
        source_conditions = []
        for term in search_terms:
            source_conditions.append(Article.source.ilike(f"%{term}%"))
        
        # Build search query with relevance scoring
        search_query = base_query.filter(
            or_(
                and_(*title_conditions),
                and_(*content_conditions),
                and_(*source_conditions)
            )
        )
        
        # Apply sorting
        if sort_by == "relevance":
            # Custom relevance scoring
            search_query = search_query.order_by(
                desc(Article.score),  # Use existing article score as base relevance
                desc(Article.published_at)
            )
        elif sort_by == "date":
            order_func = desc if sort_order == "desc" else asc
            search_query = search_query.order_by(order_func(Article.published_at))
        elif sort_by == "score":
            order_func = desc if sort_order == "desc" else asc
            search_query = search_query.order_by(order_func(Article.score))
        elif sort_by == "title":
            order_func = desc if sort_order == "desc" else asc
            search_query = search_query.order_by(order_func(Article.title))
        
        # Apply pagination
        offset = (page - 1) * page_size
        articles = search_query.offset(offset).limit(page_size).all()
        
        # Build search results
        for article in articles:
            relevance_score = self._calculate_text_relevance(article, search_terms)
            match_highlights = self._extract_highlights(article, search_terms) if highlight else []
            match_reason = self._determine_match_reason(article, search_terms)
            
            results.append(SearchResult(
                article=article,
                relevance_score=relevance_score,
                match_highlights=match_highlights,
                match_reason=match_reason
            ))
        
        return results
    
    def _semantic_search(self, query: str, base_query, page: int, page_size: int,
                        sort_by: str, sort_order: str) -> List[SearchResult]:
        """Semantic search using vector similarity"""
        
        try:
            # Get articles from base query (pre-filtered)
            candidate_articles = base_query.all()
            
            if not candidate_articles:
                return []
            
            # Use semantic search engine for vector-based similarity
            semantic_results = semantic_search_engine.semantic_search(
                query=query,
                top_k=page_size * 3,  # Get more candidates for better ranking
                search_type="hybrid"
            )
            
            # Match semantic results with our candidate articles
            results = []
            article_scores = {}
            
            # Extract article IDs and scores from semantic search results
            for sem_result in semantic_results:
                try:
                    article_id = int(sem_result.content_id)
                    article_scores[article_id] = sem_result.relevance_score
                except (ValueError, AttributeError):
                    continue
            
            # Build results from candidate articles that have semantic similarity scores
            for article in candidate_articles:
                if article.id in article_scores:
                    semantic_score = article_scores[article.id]
                    
                    # Get the original semantic result for additional info
                    matching_semantic_result = None
                    for sem_result in semantic_results:
                        if sem_result.content_id == str(article.id):
                            matching_semantic_result = sem_result
                            break
                    
                    match_explanation = "Semantic vector similarity"
                    if matching_semantic_result:
                        match_explanation = matching_semantic_result.match_explanation
                    
                    results.append(SearchResult(
                        article=article,
                        relevance_score=semantic_score,
                        match_highlights=[],  # Semantic search doesn't have direct highlights
                        match_reason="semantic"
                    ))
            
            # Sort by semantic relevance
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Apply pagination
            offset = (page - 1) * page_size
            return results[offset:offset + page_size]
            
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}, falling back to text search")
            # Fallback to text search
            return self._text_search(query, base_query, page, page_size, sort_by, sort_order, True)
    
    def _filtered_search(self, base_query, page: int, page_size: int, 
                        sort_by: str, sort_order: str) -> List[SearchResult]:
        """Search with only filters applied (no query)"""
        
        # Apply sorting
        if sort_by == "date":
            order_func = desc if sort_order == "desc" else asc
            base_query = base_query.order_by(order_func(Article.published_at))
        elif sort_by == "score":
            order_func = desc if sort_order == "desc" else asc
            base_query = base_query.order_by(order_func(Article.score))
        elif sort_by == "title":
            order_func = desc if sort_order == "desc" else asc
            base_query = base_query.order_by(order_func(Article.title))
        else:
            # Default to date descending for filter-only searches
            base_query = base_query.order_by(desc(Article.published_at))
        
        # Apply pagination
        offset = (page - 1) * page_size
        articles = base_query.offset(offset).limit(page_size).all()
        
        # Build search results (no query-based relevance)
        results = []
        for article in articles:
            results.append(SearchResult(
                article=article,
                relevance_score=article.score or 0,  # Use article score as relevance
                match_highlights=[],
                match_reason="filter"
            ))
        
        return results
    
    def _calculate_text_relevance(self, article: Article, search_terms: List[str]) -> float:
        """Calculate relevance score for text search"""
        score = 0.0
        
        title_text = (article.title or "").lower()
        content_text = (article.content or "").lower()
        source_text = article.source.lower()
        
        # Title matches (highest weight)
        for term in search_terms:
            if term in title_text:
                score += 10.0
                if title_text.startswith(term):
                    score += 5.0  # Bonus for starting with search term
        
        # Content matches
        for term in search_terms:
            content_matches = content_text.count(term)
            score += content_matches * 2.0
            
        # Source matches
        for term in search_terms:
            if term in source_text:
                score += 3.0
                
        # Boost score based on article quality
        if article.score:
            score += article.score * 0.1
            
        return score
    
    def _extract_highlights(self, article: Article, search_terms: List[str]) -> List[str]:
        """Extract highlighted snippets from article content"""
        highlights = []
        content = article.content or ""
        title = article.title or ""
        
        # Title highlights
        for term in search_terms:
            if term.lower() in title.lower():
                highlights.append(f"Title: ...{self._highlight_term(title, term)}...")
                
        # Content highlights  
        for term in search_terms:
            if term.lower() in content.lower():
                snippet = self._extract_snippet(content, term)
                if snippet:
                    highlights.append(f"Content: ...{snippet}...")
                    
        return highlights[:3]  # Limit to 3 highlights
    
    def _highlight_term(self, text: str, term: str, max_length: int = 100) -> str:
        """Highlight search term in text"""
        text_lower = text.lower()
        term_lower = term.lower()
        
        start_pos = text_lower.find(term_lower)
        if start_pos == -1:
            return text[:max_length]
            
        # Extract context around the term
        context_start = max(0, start_pos - 40)
        context_end = min(len(text), start_pos + len(term) + 40)
        
        snippet = text[context_start:context_end]
        
        # Highlight the term
        snippet = snippet.replace(
            text[start_pos:start_pos + len(term)],
            f"**{text[start_pos:start_pos + len(term)]}**"
        )
        
        return snippet
    
    def _extract_snippet(self, content: str, term: str, snippet_length: int = 150) -> str:
        """Extract a snippet around the search term"""
        content_lower = content.lower()
        term_lower = term.lower()
        
        pos = content_lower.find(term_lower)
        if pos == -1:
            return ""
            
        # Get context around the term
        start = max(0, pos - snippet_length // 2)
        end = min(len(content), pos + snippet_length // 2)
        
        snippet = content[start:end]
        
        # Find word boundaries
        if start > 0:
            first_space = snippet.find(' ')
            if first_space > 0:
                snippet = snippet[first_space + 1:]
                
        if end < len(content):
            last_space = snippet.rfind(' ')
            if last_space > 0:
                snippet = snippet[:last_space]
        
        # Highlight the search term
        snippet = snippet.replace(term, f"**{term}**")
        
        return snippet
    
    def _determine_match_reason(self, article: Article, search_terms: List[str]) -> str:
        """Determine why this article matched"""
        title_matches = any(term.lower() in (article.title or "").lower() for term in search_terms)
        content_matches = any(term.lower() in (article.content or "").lower() for term in search_terms)
        source_matches = any(term.lower() in article.source.lower() for term in search_terms)
        
        if title_matches:
            return "title"
        elif content_matches:
            return "content"
        elif source_matches:
            return "source"
        else:
            return "unknown"
    
    def _get_filtered_count(self, filters: SearchFilter, query: Optional[str] = None) -> int:
        """Get total count of articles matching filters and query"""
        count_query = self.db.query(Article)
        count_query = self._apply_filters(count_query, filters)
        
        if query:
            search_terms = query.lower().split()
            search_conditions = []
            
            for term in search_terms:
                search_conditions.extend([
                    Article.title.ilike(f"%{term}%"),
                    Article.content.ilike(f"%{term}%"),
                    Article.source.ilike(f"%{term}%")
                ])
            
            count_query = count_query.filter(or_(*search_conditions))
        
        return count_query.count()
    
    def _generate_suggestions(self, query: str, filters: SearchFilter) -> List[str]:
        """Generate search suggestions based on query and filters"""
        suggestions = []
        
        if not query or len(query) < 3:
            # Popular search terms when no query
            popular_terms = [
                "artificial intelligence", "machine learning", "payments", 
                "fintech", "blockchain", "cryptocurrency", "api", "security"
            ]
            return popular_terms[:5]
        
        # Simple suggestion logic - in practice, use more sophisticated methods
        query_lower = query.lower()
        
        # Technology suggestions
        if any(word in query_lower for word in ["ai", "artificial", "machine"]):
            suggestions.extend(["artificial intelligence", "machine learning", "deep learning"])
            
        # Finance suggestions  
        if any(word in query_lower for word in ["pay", "finance", "money"]):
            suggestions.extend(["payments", "fintech", "financial technology"])
            
        # Add query variations
        if " " in query:
            words = query.split()
            suggestions.append(" ".join(words[::-1]))  # Reverse word order
        
        return suggestions[:5]
    
    def _generate_facets(self, filters: SearchFilter, query: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """Generate facet counts for filtering UI"""
        facets = {}
        
        # Base query with current filters (excluding the facet we're counting)
        base_query = self.db.query(Article)
        
        # Apply query if present
        if query:
            search_terms = query.lower().split()
            search_conditions = []
            for term in search_terms:
                search_conditions.extend([
                    Article.title.ilike(f"%{term}%"),
                    Article.content.ilike(f"%{term}%")
                ])
            base_query = base_query.filter(or_(*search_conditions))
        
        try:
            # Source facets
            source_query = self._apply_filters_except(base_query, filters, exclude=['sources'])
            source_counts = source_query.group_by(Article.source).with_entities(
                Article.source, func.count(Article.id)
            ).order_by(desc(func.count(Article.id))).limit(10).all()
            
            facets['sources'] = {source: count for source, count in source_counts}
            
            # Score range facets
            score_query = self._apply_filters_except(base_query, filters, exclude=['min_score', 'max_score'])
            score_ranges = [
                ("high", 80, None),
                ("medium", 40, 79), 
                ("low", 0, 39),
                ("negative", None, -1)
            ]
            
            facets['score_ranges'] = {}
            for range_name, min_score, max_score in score_ranges:
                range_query = score_query
                if min_score is not None:
                    range_query = range_query.filter(Article.score >= min_score)
                if max_score is not None:
                    range_query = range_query.filter(Article.score <= max_score)
                    
                facets['score_ranges'][range_name] = range_query.count()
            
            # Date facets
            date_query = self._apply_filters_except(base_query, filters, exclude=['date_from', 'date_to'])
            now = datetime.now()
            date_ranges = [
                ("today", now - timedelta(days=1), now),
                ("this_week", now - timedelta(days=7), now),
                ("this_month", now - timedelta(days=30), now),
                ("this_year", now - timedelta(days=365), now)
            ]
            
            facets['date_ranges'] = {}
            for range_name, start_date, end_date in date_ranges:
                range_query = date_query.filter(
                    and_(
                        Article.published_at >= start_date,
                        Article.published_at <= end_date
                    )
                )
                facets['date_ranges'][range_name] = range_query.count()
                
        except Exception as e:
            logger.error(f"Error generating facets: {e}")
            # Return empty facets on error
            facets = {'sources': {}, 'score_ranges': {}, 'date_ranges': {}}
        
        return facets
    
    def _apply_filters_except(self, query, filters: SearchFilter, exclude: List[str]):
        """Apply all filters except specified ones"""
        
        if 'sources' not in exclude and filters.sources:
            query = query.filter(Article.source.in_(filters.sources))
            
        if 'min_score' not in exclude and filters.min_score is not None:
            query = query.filter(Article.score >= filters.min_score)
        if 'max_score' not in exclude and filters.max_score is not None:
            query = query.filter(Article.score <= filters.max_score)
            
        if 'date_from' not in exclude and filters.date_from:
            query = query.filter(Article.published_at >= filters.date_from)
        if 'date_to' not in exclude and filters.date_to:
            query = query.filter(Article.published_at <= filters.date_to)
            
        if 'has_image' not in exclude and filters.has_image is not None:
            if filters.has_image:
                query = query.filter(Article.image_proxy_path.isnot(None))
            else:
                query = query.filter(Article.image_proxy_path.is_(None))
                
        if 'exclude_spam' not in exclude and filters.exclude_spam:
            query = query.filter(
                or_(
                    Article.spam_detected.is_(None),
                    Article.spam_detected == False
                )
            )
            
        return query
    
    def _serialize_filters(self, filters: SearchFilter) -> Dict[str, Any]:
        """Convert SearchFilter to dictionary for response"""
        return {
            'sources': filters.sources,
            'categories': filters.categories,
            'min_score': filters.min_score,
            'max_score': filters.max_score,
            'date_from': filters.date_from.isoformat() if filters.date_from else None,
            'date_to': filters.date_to.isoformat() if filters.date_to else None,
            'has_image': filters.has_image,
            'is_starred': filters.is_starred,
            'labels': filters.labels,
            'exclude_spam': filters.exclude_spam,
            'content_quality_min': filters.content_quality_min,
            'sentiment': filters.sentiment,
            'word_count_min': filters.word_count_min,
            'word_count_max': filters.word_count_max,
            'language': filters.language
        }
    
    def _ensure_semantic_index_populated(self):
        """Ensure semantic search index is populated with recent articles"""
        try:
            # Check if we have content in the semantic index
            stats = semantic_search_engine.get_stats()
            if stats['total_content_items'] < 100:  # Threshold for re-indexing
                self._populate_semantic_index()
        except Exception as e:
            logger.warning(f"Failed to check semantic index status: {e}")
    
    def _populate_semantic_index(self, limit: int = 1000):
        """Populate semantic search index with recent articles"""
        try:
            logger.info("Populating semantic search index...")
            
            # Get recent articles
            recent_articles = self.db.query(Article).filter(
                and_(
                    Article.content.isnot(None),
                    Article.content != "",
                    Article.title.isnot(None),
                    Article.title != ""
                )
            ).order_by(desc(Article.published_at)).limit(limit).all()
            
            # Add articles to semantic index
            added_count = 0
            for article in recent_articles:
                try:
                    success = semantic_search_engine.add_content(
                        content_id=str(article.id),
                        title=article.title,
                        content=article.content,
                        url=article.url or "",
                        source=article.source,
                        metadata={
                            'score': article.score,
                            'published_at': article.published_at.isoformat() if article.published_at else None,
                            'has_image': bool(article.image_proxy_path)
                        }
                    )
                    if success:
                        added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add article {article.id} to semantic index: {e}")
            
            logger.info(f"Added {added_count} articles to semantic search index")
            
        except Exception as e:
            logger.error(f"Failed to populate semantic index: {e}")
    
    def add_article_to_semantic_index(self, article: Article) -> bool:
        """Add a single article to the semantic search index"""
        try:
            if not article.content or not article.title:
                return False
            
            return semantic_search_engine.add_content(
                content_id=str(article.id),
                title=article.title,
                content=article.content,
                url=article.url or "",
                source=article.source,
                metadata={
                    'score': article.score,
                    'published_at': article.published_at.isoformat() if article.published_at else None,
                    'has_image': bool(article.image_proxy_path)
                }
            )
        except Exception as e:
            logger.error(f"Failed to add article {article.id} to semantic index: {e}")
            return False
    
    def remove_article_from_semantic_index(self, article_id: int) -> bool:
        """Remove an article from the semantic search index"""
        try:
            return semantic_search_engine.remove_content(str(article_id))
        except Exception as e:
            logger.error(f"Failed to remove article {article_id} from semantic index: {e}")
            return False
    
    def get_semantic_search_stats(self) -> Dict[str, Any]:
        """Get semantic search engine statistics"""
        try:
            return semantic_search_engine.get_stats()
        except Exception as e:
            logger.error(f"Failed to get semantic search stats: {e}")
            return {}
    
    def refresh_semantic_index(self, limit: int = 2000):
        """Refresh the semantic search index with recent articles"""
        try:
            logger.info("Refreshing semantic search index...")
            self._populate_semantic_index(limit)
            return True
        except Exception as e:
            logger.error(f"Failed to refresh semantic index: {e}")
            return False