#!/usr/bin/env python3
"""
Test RSS content extraction
"""

import httpx
import feedparser

# Test Ars Technica feed (usually has longer content)
feed_url = "https://arstechnica.com/feed/"
print(f"Fetching: {feed_url}")

response = httpx.get(feed_url, timeout=30, follow_redirects=True)
feed = feedparser.parse(response.text)

print(f"Found {len(feed.entries)} entries")

# Check first entry
if feed.entries:
    entry = feed.entries[0]
    print(f"\nFirst entry:")
    print(f"  Title: {entry.get('title', 'No title')}")
    print(f"  Available fields: {list(entry.keys())}")
    
    # Check different content fields
    summary = entry.get('summary', '')
    description = entry.get('description', '')
    content = entry.get('content', [])
    
    print(f"\n  Summary (full): {summary}")
    print(f"  Description (full): {description}")
    print(f"  Content: {content}")
    
    # Check for content entries
    if hasattr(entry, 'content') and entry.content:
        print(f"  Content entries: {len(entry.content)}")
        for i, c in enumerate(entry.content):
            print(f"    Content {i} (full): {c.value if hasattr(c, 'value') else c}")
            
    # Also check for other potential content fields
    other_fields = ['subtitle', 'content_encoded', 'fulltext', 'text']
    for field in other_fields:
        if field in entry:
            print(f"  {field}: {entry[field]}")