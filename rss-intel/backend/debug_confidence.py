#!/usr/bin/env python3
"""
Debug script för att hitta confidence-problemet
"""
import asyncio
import logging
from sqlalchemy import text
from app.deps import SessionLocal
from app.images2 import ImageExtractor

# Konfigurera debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_specific_article():
    """Debug artikel 499 (Google Blog) som ger fel"""
    db = SessionLocal()
    try:
        # Hämta artikel 499
        result = db.execute(text("""
            SELECT id, title, url, source
            FROM articles 
            WHERE id = 499
        """))
        
        row = result.fetchone()
        if not row:
            print("Artikel 499 hittades inte")
            return
            
        article = {
            'id': row[0],
            'title': row[1],
            'url': row[2],
            'source': row[3]
        }
        
        print(f"Debug artikel: {article}")
        
        extractor = ImageExtractor()
        try:
            # Hämta page HTML
            session = await extractor.get_session()
            response = await session.get(article['url'], timeout=15)
            
            if response.status_code != 200:
                print(f"HTTP {response.status_code} för artikel {article['id']}")
                return
            
            page_html = response.text
            print(f"Page HTML length: {len(page_html)}")
            
            # Extrahera bild med debug
            entry = {
                'link': article['url'],
                'title': article['title']
            }
            
            # Kalla extract_primary_image och fånga fel
            try:
                image = await extractor.extract_primary_image(entry=entry, page_html=page_html)
                if image:
                    print(f"Extraherad bild: {image.url}")
                    print(f"Confidence type: {type(image.confidence)}, value: {image.confidence}")
                else:
                    print("Ingen bild extraherad")
            except Exception as e:
                print(f"FEL i extract_primary_image: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"FEL i image extraction: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await extractor.close()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_specific_article())