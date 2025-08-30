#!/usr/bin/env python3
"""
AI-Powered Text Formatter

Uses OpenAI GPT-4o-mini to intelligently format raw text content 
into well-structured, readable HTML with proper paragraphs, 
headings, and formatting.
"""

import os
import re
import asyncio
from typing import Optional
import openai
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def format_article_content(raw_text: str, title: str = "") -> str:
    """
    Format raw article text using AI to create readable HTML structure.
    
    Args:
        raw_text: The raw, unformatted article text
        title: Optional article title for context
        
    Returns:
        Well-formatted HTML content with proper paragraphs and structure
    """
    if not raw_text or len(raw_text.strip()) < 50:
        return raw_text
    
    try:
        # Create prompt for AI formatting
        prompt = f"""Please format the following article text into clean, readable HTML. 
        
Rules:
- Create proper <p> tags for paragraphs  
- Add <h2> or <h3> tags for any section headings you identify
- Use <blockquote> for quotes
- Use <ul>/<li> for lists when appropriate
- Keep all original content, just add proper HTML structure
- Don't add any meta information or wrapper tags
- Focus on readability and proper paragraph breaks

{f'Article title: {title}' if title else ''}

Raw text to format:
{raw_text}"""

        # Call OpenAI API
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert text formatter. Format text into clean, readable HTML structure."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        )
        
        formatted_html = response.choices[0].message.content.strip()
        
        # Clean up any markdown artifacts or unwanted tags
        formatted_html = re.sub(r'```html\s*', '', formatted_html)
        formatted_html = re.sub(r'```\s*$', '', formatted_html)
        formatted_html = re.sub(r'^html\s*', '', formatted_html)
        
        logger.info(f"Successfully formatted article content using OpenAI ({len(raw_text)} -> {len(formatted_html)} chars)")
        return formatted_html
        
    except Exception as e:
        logger.error(f"Failed to format article content with OpenAI: {e}")
        # Fallback: basic paragraph formatting
        return fallback_format(raw_text)


def fallback_format(text: str) -> str:
    """Fallback formatting when AI is unavailable."""
    if not text:
        return text
    
    # Split by double newlines for paragraphs
    paragraphs = text.split('\n\n')
    
    # If no double newlines, try single newlines with length filter
    if len(paragraphs) == 1:
        lines = text.split('\n')
        paragraphs = []
        current_para = ""
        
        for line in lines:
            line = line.strip()
            if len(line) > 50:  # Likely a paragraph
                if current_para:
                    paragraphs.append(current_para)
                current_para = line
            else:
                current_para += " " + line if current_para else line
        
        if current_para:
            paragraphs.append(current_para)
    
    # Convert to HTML paragraphs
    html_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if len(para) > 10:  # Filter out very short paragraphs
            html_paragraphs.append(f"<p>{para}</p>")
    
    return '\n\n'.join(html_paragraphs)