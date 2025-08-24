#!/usr/bin/env python3
"""
Production script för att uppdatera alla befintliga artiklar med förbättrad bildextrahering
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import SessionLocal
from app.images2 import ImageExtractor, ImageCandidate

# Konfigurera loggning
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/image_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionImageUpdater:
    def __init__(self, batch_size: int = 50, max_articles: Optional[int] = None):
        self.batch_size = batch_size
        self.max_articles = max_articles
        self.extractor = ImageExtractor()
        self.stats = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    async def get_articles_needing_images(self, db: Session, limit: int) -> List[Dict]:
        """Hämta artiklar som behöver bilduppdatering"""
        # Prioritera artiklar utan bilder från de senaste 30 dagarna
        result = db.execute(text("""
            SELECT id, title, url, source, published_at, has_image, image_src_url
            FROM articles 
            WHERE url IS NOT NULL 
            AND (has_image = false OR image_src_url IS NULL)
            AND published_at > NOW() - INTERVAL '30 days'
            AND source IN (
                'TechCrunch AI', 'Wired', 'The Verge', 'Ars Technica', 
                'OpenAI Blog', 'Google AI Blog', 'Meta AI', 'DeepMind'
            )
            ORDER BY published_at DESC
            LIMIT :limit
        """), {"limit": limit})
        
        articles = []
        for row in result.fetchall():
            articles.append({
                'id': row[0],
                'title': row[1],
                'url': row[2], 
                'source': row[3],
                'published_at': row[4],
                'has_image': row[5],
                'current_image_url': row[6]
            })
        
        return articles
    
    async def extract_and_update_image(self, db: Session, article: Dict) -> bool:
        """Extrahera bild för en artikel och uppdatera databasen"""
        try:
            # Hämta page HTML
            session = await self.extractor.get_session()
            response = await session.get(article['url'], timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} för artikel {article['id']}: {article['url']}")
                return False
            
            page_html = response.text
            
            # Extrahera bild
            image = await self.extractor.extract_primary_image(
                entry={
                    'link': article['url'],
                    'title': article['title']
                },
                page_html=page_html
            )
            
            if image:
                # Uppdatera databas med bildinformation
                db.execute(text("""
                    UPDATE articles 
                    SET 
                        has_image = true,
                        image_src_url = :image_url,
                        top_image_url = :image_url,
                        image_width = :width,
                        image_height = :height,
                        image_stage = :stage,
                        image_reason = :reason
                    WHERE id = :article_id
                """), {
                    "article_id": article['id'],
                    "image_url": image.url,
                    "width": image.width,
                    "height": image.height,
                    "stage": "extracted",
                    "reason": f"source:{image.source_type},conf:{image.confidence:.2f}"
                })
                
                db.commit()
                
                logger.info(f"✓ Uppdaterad artikel {article['id']}: {image.url[:80]}... (källa: {image.source_type})")
                return True
            else:
                # Markera som behandlad men utan bild
                db.execute(text("""
                    UPDATE articles 
                    SET 
                        image_stage = :stage,
                        image_reason = :reason
                    WHERE id = :article_id
                """), {
                    "article_id": article['id'],
                    "stage": "processed", 
                    "reason": "no_image_found"
                })
                
                db.commit()
                logger.info(f"✗ Ingen bild hittades för artikel {article['id']}")
                return False
                
        except Exception as e:
            error_msg = f"Fel vid bearbetning av artikel {article['id']}: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            
            # Markera som misslyckad
            try:
                db.execute(text("""
                    UPDATE articles 
                    SET 
                        image_stage = :stage,
                        image_reason = :reason
                    WHERE id = :article_id
                """), {
                    "article_id": article['id'],
                    "stage": "failed",
                    "reason": f"error:{str(e)[:100]}"
                })
                db.commit()
            except Exception as db_error:
                logger.error(f"Kunde inte uppdatera fel-status för artikel {article['id']}: {db_error}")
            
            return False
    
    async def process_batch(self, articles: List[Dict]) -> Dict:
        """Bearbeta en batch av artiklar"""
        batch_stats = {'success': 0, 'failed': 0}
        
        db = SessionLocal()
        try:
            for article in articles:
                success = await self.extract_and_update_image(db, article)
                
                if success:
                    batch_stats['success'] += 1
                    self.stats['success'] += 1
                else:
                    batch_stats['failed'] += 1
                    self.stats['failed'] += 1
                
                self.stats['processed'] += 1
                
                # Liten paus mellan requests
                await asyncio.sleep(0.1)
        
        finally:
            db.close()
        
        return batch_stats
    
    async def run_production_update(self):
        """Kör produktionsuppdatering av alla artiklar"""
        logger.info("🚀 Startar produktionsuppdatering av bildextrahering")
        start_time = time.time()
        
        db = SessionLocal()
        try:
            # Räkna totalt antal artiklar som behöver uppdatering
            result = db.execute(text("""
                SELECT COUNT(*) FROM articles 
                WHERE url IS NOT NULL 
                AND (has_image = false OR image_src_url IS NULL)
                AND published_at > NOW() - INTERVAL '30 days'
            """))
            total_articles = result.scalar()
            
            if self.max_articles:
                total_articles = min(total_articles, self.max_articles)
            
            logger.info(f"📊 Totalt {total_articles} artiklar att bearbeta")
            
            # Bearbeta i batches
            processed = 0
            while processed < total_articles:
                remaining = min(self.batch_size, total_articles - processed)
                
                # Hämta nästa batch
                articles = await self.get_articles_needing_images(db, remaining)
                
                if not articles:
                    logger.info("Inga fler artiklar att bearbeta")
                    break
                
                logger.info(f"🔄 Bearbetar batch {processed//self.batch_size + 1}: artiklar {processed+1}-{processed+len(articles)} av {total_articles}")
                
                # Bearbeta batch
                batch_stats = await self.process_batch(articles)
                processed += len(articles)
                
                # Logga progress
                elapsed = time.time() - start_time
                rate = self.stats['processed'] / elapsed if elapsed > 0 else 0
                success_rate = (self.stats['success'] / self.stats['processed'] * 100) if self.stats['processed'] > 0 else 0
                
                logger.info(f"📈 Progress: {processed}/{total_articles} ({processed/total_articles*100:.1f}%) | "
                          f"Framgång: {success_rate:.1f}% | Hastighet: {rate:.1f} artiklar/sek")
                
                # Paus mellan batches
                if processed < total_articles:
                    await asyncio.sleep(2)
        
        finally:
            db.close()
        
        # Slutrapport
        elapsed_time = time.time() - start_time
        logger.info("🏁 Produktionsuppdatering slutförd!")
        logger.info(f"📊 SLUTSTATISTIK:")
        logger.info(f"   Bearbetade artiklar: {self.stats['processed']}")
        logger.info(f"   Framgångsrika: {self.stats['success']} ({self.stats['success']/max(1,self.stats['processed'])*100:.1f}%)")
        logger.info(f"   Misslyckade: {self.stats['failed']}")
        logger.info(f"   Total tid: {elapsed_time:.1f} sekunder")
        logger.info(f"   Genomsnittlig hastighet: {self.stats['processed']/elapsed_time:.2f} artiklar/sek")
        
        if self.stats['errors']:
            logger.warning(f"⚠️  {len(self.stats['errors'])} fel inträffade:")
            for error in self.stats['errors'][-5:]:  # Visa de senaste 5 felen
                logger.warning(f"   {error}")

async def main():
    """Huvudfunktion för produktionsuppdatering"""
    import sys
    
    # Kommandoradsparametrar
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    max_articles = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    updater = ProductionImageUpdater(batch_size=batch_size, max_articles=max_articles)
    await updater.run_production_update()

if __name__ == "__main__":
    asyncio.run(main())