#!/usr/bin/env python3
import asyncio
import aiohttp
import time
from datetime import datetime

async def extract_articles():
    """Extract content from all pending articles in batches"""
    async with aiohttp.ClientSession() as session:
        batch_size = 20
        batch_num = 1
        
        while True:
            try:
                print(f"\n[{datetime.now()}] Starting batch {batch_num}...")
                
                # Get list of pending article IDs
                async with session.get('http://localhost:8000/items?page_size=50') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Find articles that need extraction (pending status)
                        # Since API doesn't return extraction_status, we'll extract all
                        article_ids = [item['id'] for item in data['items'][:batch_size]]
                        
                        if not article_ids:
                            print("No articles to process, waiting...")
                            await asyncio.sleep(300)  # Wait 5 minutes
                            continue
                        
                        print(f"Processing {len(article_ids)} articles: {article_ids[:5]}...")
                        
                        # Extract content for batch
                        extract_data = article_ids
                        async with session.post(
                            'http://localhost:8000/extraction/batch',
                            json=extract_data,
                            headers={'Content-Type': 'application/json'}
                        ) as extract_resp:
                            if extract_resp.status == 200:
                                result = await extract_resp.json()
                                print(f"✅ Batch {batch_num} completed: {result}")
                                
                                if result['total_processed'] == 0:
                                    print("No articles were processed, taking a longer break...")
                                    await asyncio.sleep(600)  # 10 minutes
                                else:
                                    await asyncio.sleep(120)  # 2 minutes between batches
                            else:
                                error_text = await extract_resp.text()
                                print(f"❌ Extraction failed: {error_text}")
                                await asyncio.sleep(300)  # 5 minutes on error
                    else:
                        print(f"❌ Failed to get articles: {resp.status}")
                        await asyncio.sleep(300)
                
                batch_num += 1
                
            except Exception as e:
                print(f"❌ Error in batch {batch_num}: {e}")
                await asyncio.sleep(300)  # 5 minutes on error

if __name__ == "__main__":
    print("🚀 Starting automatic content extraction...")
    print("This will run continuously, extracting content from articles.")
    print("Press Ctrl+C to stop.")
    
    try:
        asyncio.run(extract_articles())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")