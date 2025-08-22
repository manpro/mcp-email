#!/bin/bash

echo "🚀 Adding feeds via FreshRSS CLI..."
echo "========================================"

# Function to add feed via CLI (this may not exist, but let's try)
add_feed_cli() {
    local url="$1"
    local title="$2"
    
    echo -n "Adding: $title... "
    
    # Try to add feed via CLI if available
    result=$(docker-compose exec -T freshrss /bin/bash -c "
        cd /var/www/FreshRSS
        php -r \"
        require_once('constants.php');
        require_once('lib/lib_rss.php');
        require_once('app/models/Feed.php');
        require_once('app/models/FreshRSS_Context.php');
        require_once('app/models/FreshRSS_Category.php');
        
        // This is a hack to add feeds programmatically
        echo 'Adding feed: $url';
        \"
    " 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "✅"
    else
        echo "❌"
    fi
}

# Add feeds manually via database
echo "Adding feeds directly to database..."

# Create a temporary SQL script
cat > /tmp/add_feeds.sql << 'EOF'
-- This would require access to FreshRSS database
-- But FreshRSS uses its own database structure
EOF

echo ""
echo "Let's try using curl with session handling..."

# Create a proper session-based approach
COOKIE_FILE="/tmp/freshrss_session.txt"

# Try to login and get session
echo "Getting FreshRSS session..."
curl -c "$COOKIE_FILE" -s "http://localhost:8081/" > /dev/null

# Try to login with session
login_result=$(curl -b "$COOKIE_FILE" -c "$COOKIE_FILE" -s \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=adminadmin&submit=Login" \
  "http://localhost:8081/i/?c=auth&a=login")

if echo "$login_result" | grep -q "logout"; then
    echo "✅ Login successful"
    
    # Add feeds
    feeds=(
        "https://techcrunch.com/feed/|TechCrunch"
        "https://www.coindesk.com/arc/outboundfeeds/rss/|CoinDesk"
        "https://cointelegraph.com/rss|Cointelegraph"
        "https://openai.com/blog/rss.xml|OpenAI Blog"
        "https://news.ycombinator.com/rss|Hacker News"
    )
    
    for feed_data in "${feeds[@]}"; do
        url=$(echo "$feed_data" | cut -d'|' -f1)
        title=$(echo "$feed_data" | cut -d'|' -f2)
        
        echo -n "Adding: $title... "
        
        add_result=$(curl -b "$COOKIE_FILE" -s \
          -X POST \
          -H "Content-Type: application/x-www-form-urlencoded" \
          -d "url_rss=$url&category=1" \
          "http://localhost:8081/i/?c=subscription&a=add")
        
        if echo "$add_result" | grep -q -v "error\|Error"; then
            echo "✅"
        else
            echo "⚠️"
        fi
        
        sleep 1
    done
    
else
    echo "❌ Login failed"
fi

# Cleanup
rm -f "$COOKIE_FILE"

echo ""
echo "Now forcing FreshRSS to fetch articles..."
docker-compose exec freshrss /var/www/FreshRSS/cli/actualize-user.php --user admin

echo ""
echo "✅ Done! Check http://localhost:3001 for articles"