"""
Story clustering for RSS Intelligence
Groups related articles into stories to reduce duplicates
"""
import hashlib
import re
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from .store import Article, ArticleStore


class URLCanonicalizer:
    """Canonicalize URLs to detect exact duplicates"""
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for deduplication"""
        if not url:
            return ""
            
        # Remove common tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source', 'origin', '_ga', 'mc_cid', 'mc_eid',
            'mkt_tok', 'trk', 'trkCampaign', 'icid', 'ncid', 'cmpid', 'cmp'
        }
        
        try:
            parsed = urlparse(url.lower().strip())
            
            # Remove www prefix
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Clean query parameters
            query_params = parse_qs(parsed.query)
            clean_params = {k: v for k, v in query_params.items() 
                          if k not in tracking_params}
            
            # Sort parameters for consistency
            if clean_params:
                query_string = '&'.join(f"{k}={'&'.join(sorted(v))}" 
                                      for k in sorted(clean_params.keys()))
            else:
                query_string = ''
            
            # Remove trailing slashes and common extensions
            path = parsed.path.rstrip('/')
            if path.endswith('/index.html') or path.endswith('/index.php'):
                path = path.rsplit('/', 1)[0]
            
            # Reconstruct URL
            canonical = f"{parsed.scheme}://{domain}{path}"
            if query_string:
                canonical += f"?{query_string}"
                
            return canonical
            
        except Exception:
            return url.lower().strip()


class ContentHasher:
    """Generate content hashes for near-duplicate detection"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text for hashing"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove non-alphanumeric except spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Convert to lowercase
        text = text.lower().strip()
        
        return text
    
    @staticmethod
    def content_hash(title: str, content: str) -> str:
        """Generate SHA1 hash of cleaned content"""
        clean_title = ContentHasher.clean_text(title)
        clean_content = ContentHasher.clean_text(content)
        
        # Combine title and content
        combined = f"{clean_title} {clean_content}".strip()
        
        if not combined:
            return ""
        
        return hashlib.sha1(combined.encode('utf-8')).hexdigest()


class SimpleSimHash:
    """Simple SimHash implementation for near-duplicate detection"""
    
    @staticmethod
    def get_features(text: str) -> Set[str]:
        """Extract features (words and bigrams) from text"""
        if not text:
            return set()
        
        words = ContentHasher.clean_text(text).split()
        features = set(words)  # Unigrams
        
        # Add bigrams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            features.add(bigram)
        
        return features
    
    @staticmethod
    def simhash(text: str) -> int:
        """Generate SimHash for text"""
        features = SimpleSimHash.get_features(text)
        
        if not features:
            return 0
        
        # 32-bit hash to avoid PostgreSQL bigint overflow
        hashbits = 32
        v = [0] * hashbits
        
        for feature in features:
            # Hash feature to get bits
            h = abs(hash(feature))  # Use abs to avoid negative values
            for i in range(hashbits):
                bit = (h >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Convert to final hash, ensure it fits in PostgreSQL bigint
        fingerprint = 0
        for i in range(hashbits):
            if v[i] > 0:
                fingerprint |= (1 << i)
        
        # Ensure the value fits in PostgreSQL bigint range (-9223372036854775808 to 9223372036854775807)
        return fingerprint & 0x7FFFFFFF  # Limit to 31 bits to be safe
    
    @staticmethod
    def hamming_distance(hash1: int, hash2: int) -> int:
        """Calculate Hamming distance between two hashes"""
        return bin(hash1 ^ hash2).count('1')
    
    @staticmethod
    def similarity(hash1: int, hash2: int) -> float:
        """Calculate similarity (0-1) between two hashes"""
        distance = SimpleSimHash.hamming_distance(hash1, hash2)
        return 1.0 - (distance / 32.0)  # Changed to 32 bits


class StoryClustering:
    """Main clustering logic for grouping articles into stories"""
    
    def __init__(self, db: Session):
        self.db = db
        self.store = ArticleStore(db)
        self.url_canonicalizer = URLCanonicalizer()
        self.content_hasher = ContentHasher()
        self.simhasher = SimpleSimHash()
    
    def find_or_create_story(self, article: Article) -> Optional[int]:
        """Find existing story or create new one for article"""
        
        # 1. Exact URL matching
        canonical_url = self.url_canonicalizer.normalize_url(article.url)
        if canonical_url:
            existing = self.db.execute(
                text("SELECT story_id FROM articles WHERE canonical_url = :url AND story_id IS NOT NULL LIMIT 1"),
                {"url": canonical_url}
            ).scalar()
            if existing:
                return existing
        
        # 2. Content hash matching
        content_hash = self.content_hasher.content_hash(article.title, article.content or "")
        if content_hash:
            existing = self.db.execute(
                text("SELECT story_id FROM articles WHERE content_hash = :hash AND story_id IS NOT NULL LIMIT 1"),
                {"hash": content_hash}
            ).scalar()
            if existing:
                return existing
        
        # 3. SimHash matching (for articles from last 3 days)
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        article_simhash = self.simhasher.simhash(f"{article.title} {article.content or ''}")
        
        # Get recent articles for similarity comparison
        recent_articles = self.db.execute(
            text("""
                SELECT id, story_id, title, content, simhash 
                FROM articles 
                WHERE published_at >= :since 
                AND story_id IS NOT NULL 
                AND simhash IS NOT NULL
                ORDER BY published_at DESC 
                LIMIT 500
            """),
            {"since": three_days_ago}
        ).fetchall()
        
        best_similarity = 0.0
        best_story_id = None
        similarity_threshold = 0.85  # 85% similarity threshold
        
        for row in recent_articles:
            if row.simhash:
                similarity = self.simhasher.similarity(article_simhash, row.simhash)
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_story_id = row.story_id
        
        if best_story_id:
            return best_story_id
        
        # 4. Create new story
        return self.create_story(article, canonical_url, content_hash, article_simhash)
    
    def create_story(self, article: Article, canonical_url: str, content_hash: str, simhash: int) -> int:
        """Create a new story for the article"""
        
        import json
        
        # Use raw SQL with proper JSON parameter binding
        sources_data = [{"url": article.url, "site": article.source, "ts": article.published_at.isoformat()}]
        sources_json = json.dumps(sources_data)
        
        result = self.db.execute(
            text("""
                INSERT INTO stories (canonical_title, first_seen, last_seen, confidence, best_image, sources)
                VALUES (:title, :first_seen, :last_seen, :confidence, :image, CAST(:sources AS jsonb))
                RETURNING id
            """),
            {
                "title": article.title,
                "first_seen": article.published_at,
                "last_seen": article.published_at,
                "confidence": 1.0,
                "image": article.image_proxy_path,
                "sources": sources_json
            }
        )
        
        story_id = result.scalar()
        
        # Update article with story info
        self.db.execute(
            text("""
                UPDATE articles 
                SET story_id = :story_id, canonical_url = :canonical_url, 
                    content_hash = :content_hash, simhash = :simhash
                WHERE id = :article_id
            """),
            {
                "story_id": story_id,
                "canonical_url": canonical_url,
                "content_hash": content_hash,
                "simhash": simhash,
                "article_id": article.id
            }
        )
        
        self.db.commit()
        return story_id
    
    def update_story(self, story_id: int, article: Article, canonical_url: str, content_hash: str, simhash: int):
        """Update existing story with new article"""
        
        # Update article
        self.db.execute(
            text("""
                UPDATE articles 
                SET story_id = :story_id, canonical_url = :canonical_url,
                    content_hash = :content_hash, simhash = :simhash
                WHERE id = :article_id
            """),
            {
                "story_id": story_id,
                "canonical_url": canonical_url,
                "content_hash": content_hash,
                "simhash": simhash,
                "article_id": article.id
            }
        )
        
        # Update story metadata using raw SQL with proper JSON handling
        import json
        new_source = {"url": article.url, "site": article.source, "ts": article.published_at.isoformat()}
        new_source_json = json.dumps(new_source)
        
        self.db.execute(
            text("""
                UPDATE stories 
                SET last_seen = GREATEST(last_seen, :published_at),
                    sources = sources || CAST(:new_source AS jsonb)
                WHERE id = :story_id
            """),
            {
                "story_id": story_id,
                "published_at": article.published_at,
                "new_source": new_source_json
            }
        )
        
        self.db.commit()
    
    def cluster_article(self, article_id: int) -> Optional[int]:
        """Cluster a single article"""
        
        # Get article
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None
        
        # Skip if already clustered
        if article.story_id:
            return article.story_id
        
        # Find or create story
        story_id = self.find_or_create_story(article)
        
        if story_id:
            canonical_url = self.url_canonicalizer.normalize_url(article.url)
            content_hash = self.content_hasher.content_hash(article.title, article.content or "")
            simhash = self.simhasher.simhash(f"{article.title} {article.content or ''}")
            
            self.update_story(story_id, article, canonical_url, content_hash, simhash)
        
        return story_id
    
    def cluster_all_unclustered(self, limit: int = 100) -> Dict[str, int]:
        """Cluster all unclustered articles"""
        
        # Get unclustered articles
        unclustered = self.db.execute(
            text("""
                SELECT id FROM articles 
                WHERE story_id IS NULL 
                ORDER BY published_at DESC 
                LIMIT :limit
            """),
            {"limit": limit}
        ).fetchall()
        
        clustered = 0
        new_stories = 0
        errors = 0
        
        for row in unclustered:
            try:
                story_id = self.cluster_article(row.id)
                if story_id:
                    clustered += 1
                    # Check if it's a new story (only one article)
                    article_count = self.db.execute(
                        text("SELECT COUNT(*) FROM articles WHERE story_id = :story_id"),
                        {"story_id": story_id}
                    ).scalar()
                    if article_count == 1:
                        new_stories += 1
            except Exception as e:
                print(f"Error clustering article {row.id}: {e}")
                errors += 1
        
        return {
            "processed": len(unclustered),
            "clustered": clustered,
            "new_stories": new_stories,
            "errors": errors
        }


def cluster_articles_batch(db: Session, limit: int = 100) -> Dict[str, int]:
    """Batch cluster articles - for use in scheduler"""
    clustering = StoryClustering(db)
    return clustering.cluster_all_unclustered(limit)