# Förslag för automatisk reklamdetektering i RSS Intelligence

## Identifierade reklamartiklar
1. **TradingView Ideas** - "Cryptocurrency & Digital Assets" (Score: 98)
2. **Press releases** - Event marketing och företagsmeddelanden  
3. **Finextra Research** - Webbinar/event promotion (redan spam-filtrerade)

## Detekteringsregler som kan implementeras

### 1. URL-baserad detektering
```python
PROMOTIONAL_DOMAINS = [
    'tradingview.com/chart/',  # Trading promotion
    'finextra.com/event-info/',  # Event marketing
]

PROMOTIONAL_URL_PATTERNS = [
    r'/press-releases?/',
    r'/events?/',
    r'/webinars?/',
    r'/chart/.+[A-Z]{2,}-.+',  # TradingView chart patterns
]
```

### 2. Titel-baserad detektering
```python
PROMOTIONAL_TITLE_PATTERNS = [
    r'press release',
    r'webinar:',
    r'event:',
    r'register now',
    r'join us',
    r'free trial',
    r'cryptocurrency & digital assets',  # Generic promotional titles
    r'trading (ideas?|strategies?)',
]
```

### 3. Käll-baserad detektering
```python
PROMOTIONAL_SOURCES = [
    'TradingView Ideas',
    'PR Newswire', 
    'Business Wire',
    'MarketWatch Press Release'
]

# Finextra Research redan hanterat via event-URL patterns
```

### 4. Innehåll-baserad detektering
```python
PROMOTIONAL_CONTENT_KEYWORDS = [
    'register for',
    'sign up now',
    'limited time offer',
    'exclusive access',
    'contact us for demo',
    'request pricing',
    'schedule consultation'
]
```

## Implementation förslag

### Backend (/backend/app/scoring.py)
```python
def detect_promotional_content(article):
    """Detect promotional/advertising content"""
    spam_score = 0
    reasons = []
    
    # URL checks
    if any(domain in article.url for domain in PROMOTIONAL_DOMAINS):
        spam_score += 50
        reasons.append("promotional_domain")
    
    # Title checks  
    if any(re.search(pattern, article.title, re.I) for pattern in PROMOTIONAL_TITLE_PATTERNS):
        spam_score += 30
        reasons.append("promotional_title")
        
    # Source checks
    if article.source in PROMOTIONAL_SOURCES:
        spam_score += 25
        reasons.append("promotional_source")
    
    return spam_score, reasons
```

### Database update
```sql
-- Mark identified promotional articles
UPDATE articles 
SET score_total = -999, 
    flags = jsonb_set(flags, '{spam}', 'true') ||
            jsonb_set(flags, '{reason}', '"promotional_content"') ||
            jsonb_set(flags, '{auto_detected}', 'true')
WHERE source = 'TradingView Ideas' 
   OR url LIKE '%/press-releases/%'
   OR url LIKE '%finextra.com/event-info/%';
```

## Rekommendation
1. **Implementera URL-baserad detektering först** - enklast och mest effektivt
2. **Lägg till käll-baserad filtering** för kända promotional källor
3. **Använd thumbs down-data** för att träna ML-modeller
4. **Regelbunden översyn** av nya promotional patterns