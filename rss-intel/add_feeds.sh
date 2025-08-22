#!/bin/bash

echo "🚀 Adding RSS feeds to FreshRSS via web interface..."
echo "========================================"

# Base URL
BASE_URL="http://localhost:8081"
COOKIE_JAR="/tmp/freshrss_cookies.txt"

# Login to FreshRSS
echo "Logging in to FreshRSS..."
curl -s -c "$COOKIE_JAR" -X POST \
  -d "username=admin&password=adminadmin" \
  "$BASE_URL/i/?c=auth&a=login" > /dev/null

# Function to add a feed
add_feed() {
    local url="$1"
    local title="$2"
    
    echo -n "Adding: $title... "
    
    response=$(curl -s -b "$COOKIE_JAR" -X POST \
      -d "url_rss=$url&category=000000000001" \
      "$BASE_URL/i/?c=subscription&a=add" 2>/dev/null)
    
    if [[ $response == *"error"* ]]; then
        echo "⏭️  (already exists)"
    else
        echo "✅"
    fi
    
    sleep 0.2
}

echo ""
echo "📰 Adding Priority RSS feeds..."
echo "----------------------------------------"

# High-priority payment feeds
add_feed "https://www.finextra.com/rss/headlines.aspx" "Finextra Headlines"
add_feed "https://www.pymnts.com/feed/" "PYMNTS"
add_feed "https://stripe.com/blog/feed.rss" "Stripe Blog"

# High-priority crypto feeds
add_feed "https://www.coindesk.com/arc/outboundfeeds/rss/" "CoinDesk"
add_feed "https://cointelegraph.com/rss" "Cointelegraph"

# High-priority AI feeds
add_feed "https://openai.com/blog/rss.xml" "OpenAI Blog"
add_feed "https://www.anthropic.com/rss.xml" "Anthropic Blog"
add_feed "https://huggingface.co/blog/feed.xml" "Hugging Face"

# High-priority tech news
add_feed "https://techcrunch.com/feed/" "TechCrunch"
add_feed "https://news.ycombinator.com/rss" "Hacker News"
add_feed "https://arstechnica.com/feed/" "Ars Technica"

# Swedish
add_feed "https://www.riksbank.se/sv/press-och-publicerat/nyheter/rss/" "Riksbanken"
add_feed "https://www.breakit.se/feed/rss" "Breakit"

# Clean up
rm -f "$COOKIE_JAR"

echo ""
echo "========================================"
echo "✅ Feeds added! Now refreshing..."
echo ""

# Trigger a manual refresh to fetch articles
curl -X POST http://localhost:8000/refresh

echo ""
echo "🎉 Done! Visit http://localhost:3001 to see your scored articles!"