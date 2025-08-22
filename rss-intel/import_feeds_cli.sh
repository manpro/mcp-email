#!/bin/bash

echo "🚀 Importing RSS feeds to FreshRSS..."
echo "========================================"

# Counter variables
TOTAL=0
SUCCESS=0

# Function to add a feed
add_feed() {
    local url="$1"
    local title="$2"
    
    TOTAL=$((TOTAL + 1))
    
    echo -n "Adding: $title... "
    
    # Use FreshRSS CLI to add the feed
    docker-compose exec -T freshrss ./cli/add-feed.php \
        --user admin \
        --feed-url "$url" \
        --title "$title" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "⏭️  (skipped/exists)"
    fi
    
    # Small delay
    sleep 0.2
}

echo ""
echo "📡 Importing RSSHub routes..."
echo "----------------------------------------"

# RSSHub routes - AI & ML
add_feed "http://rsshub:1200/twitter/user/OpenAI.rss" "Twitter: OpenAI"
add_feed "http://rsshub:1200/twitter/user/AnthropicAI.rss" "Twitter: Anthropic"
add_feed "http://rsshub:1200/github/trending/daily/python.rss" "GitHub Trending: Python"
add_feed "http://rsshub:1200/github/trending/daily/machine-learning.rss" "GitHub Trending: ML"
add_feed "http://rsshub:1200/reddit/r/MachineLearning/hot.rss" "Reddit: r/MachineLearning"
add_feed "http://rsshub:1200/reddit/r/artificial/hot.rss" "Reddit: r/artificial"
add_feed "http://rsshub:1200/producthunt/today.rss" "Product Hunt: Today"

# RSSHub routes - Crypto
add_feed "http://rsshub:1200/twitter/user/VitalikButerin.rss" "Twitter: Vitalik Buterin"
add_feed "http://rsshub:1200/twitter/user/cz_binance.rss" "Twitter: CZ Binance"
add_feed "http://rsshub:1200/reddit/r/CryptoCurrency/hot.rss" "Reddit: r/CryptoCurrency"
add_feed "http://rsshub:1200/reddit/r/ethereum/hot.rss" "Reddit: r/ethereum"
add_feed "http://rsshub:1200/reddit/r/Bitcoin/hot.rss" "Reddit: r/Bitcoin"

# RSSHub routes - Tech
add_feed "http://rsshub:1200/hackernews/best.rss" "Hacker News: Best"
add_feed "http://rsshub:1200/reddit/r/programming/hot.rss" "Reddit: r/programming"
add_feed "http://rsshub:1200/reddit/r/technology/hot.rss" "Reddit: r/technology"
add_feed "http://rsshub:1200/github/trending/daily.rss" "GitHub Trending: All"

# RSSHub routes - Fintech
add_feed "http://rsshub:1200/reddit/r/fintech/top/week.rss" "Reddit: r/fintech"
add_feed "http://rsshub:1200/twitter/user/Visa.rss" "Twitter: Visa"
add_feed "http://rsshub:1200/twitter/user/Mastercard.rss" "Twitter: Mastercard"

echo ""
echo "📰 Importing native RSS feeds..."
echo "----------------------------------------"

# Payments & Fintech
add_feed "https://www.finextra.com/rss/headlines.aspx" "Finextra Headlines"
add_feed "https://www.finextra.com/rss/payments.aspx" "Finextra Payments"
add_feed "https://www.finextra.com/rss/cards.aspx" "Finextra Cards"
add_feed "https://www.finextra.com/rss/crypto.aspx" "Finextra Crypto"
add_feed "https://www.pymnts.com/feed/" "PYMNTS"
add_feed "https://www.thepaypers.com/rss/news" "The Paypers"
add_feed "https://www.paymentsjournal.com/feed/" "Payments Journal"
add_feed "https://www.bankingtech.com/feed/" "Banking Tech"
add_feed "https://www.fintechfutures.com/feed/" "Fintech Futures"

# Swedish Finance
add_feed "https://www.riksbank.se/sv/press-och-publicerat/nyheter/rss/" "Riksbanken"
add_feed "https://www.fi.se/sv/om-fi/nyheter/rss.xml" "Finansinspektionen"

# Crypto & Blockchain
add_feed "https://cointelegraph.com/rss" "Cointelegraph"
add_feed "https://www.coindesk.com/arc/outboundfeeds/rss/" "CoinDesk"
add_feed "https://bitcoinmagazine.com/.rss/full/" "Bitcoin Magazine"
add_feed "https://decrypt.co/feed" "Decrypt"
add_feed "https://www.theblockcrypto.com/rss.xml" "The Block"
add_feed "https://cryptonews.com/news/feed/" "CryptoNews"
add_feed "https://blockchain.news/rss" "Blockchain News"
add_feed "https://bitcoinist.com/feed/" "Bitcoinist"
add_feed "https://www.newsbtc.com/feed/" "NewsBTC"

# AI & Machine Learning
add_feed "https://openai.com/blog/rss.xml" "OpenAI Blog"
add_feed "https://www.anthropic.com/rss.xml" "Anthropic Blog"
add_feed "https://deepmind.google/blog/rss.xml" "DeepMind Blog"
add_feed "https://ai.googleblog.com/feeds/posts/default" "Google AI Blog"
add_feed "https://blogs.nvidia.com/feed/" "NVIDIA Blog"
add_feed "https://huggingface.co/blog/feed.xml" "Hugging Face Blog"
add_feed "https://www.technologyreview.com/topic/artificial-intelligence/feed" "MIT Tech Review AI"
add_feed "https://venturebeat.com/ai/feed/" "VentureBeat AI"
add_feed "https://www.artificialintelligence-news.com/feed/" "AI News"
add_feed "https://www.marktechpost.com/feed/" "MarkTechPost"

# Major Tech News
add_feed "https://techcrunch.com/feed/" "TechCrunch"
add_feed "https://www.techmeme.com/feed.xml" "Techmeme"
add_feed "https://www.theverge.com/rss/index.xml" "The Verge"
add_feed "https://arstechnica.com/feed/" "Ars Technica"
add_feed "https://www.wired.com/feed/rss" "Wired"
add_feed "https://feeds.feedburner.com/TechCrunch/startups" "TechCrunch Startups"
add_feed "https://feeds.feedburner.com/TechCrunch/fundings-exits" "TechCrunch Fundings"
add_feed "https://thenextweb.com/feed" "The Next Web"
add_feed "https://www.engadget.com/rss.xml" "Engadget"

# Business & Finance Tech
add_feed "https://feeds.bloomberg.com/technology/news.rss" "Bloomberg Tech"
add_feed "https://feeds.reuters.com/reuters/technologyNews" "Reuters Tech"
add_feed "https://www.ft.com/technology?format=rss" "Financial Times Tech"
add_feed "https://www.wsj.com/xml/rss/3_7455.xml" "WSJ Tech"

# Developer & Open Source
add_feed "https://github.blog/feed/" "GitHub Blog"
add_feed "https://stackoverflow.blog/feed/" "Stack Overflow Blog"
add_feed "https://news.ycombinator.com/rss" "Hacker News"
add_feed "https://lobste.rs/rss" "Lobsters"

# Company Blogs (Payments)
add_feed "https://stripe.com/blog/feed.rss" "Stripe Blog"
add_feed "https://www.adyen.com/blog/rss.xml" "Adyen Blog"
add_feed "https://blog.klarna.com/feed/" "Klarna Blog"
add_feed "https://squareup.com/blog/rss" "Square Blog"
add_feed "https://www.paypal.com/stories/rss" "PayPal Stories"

# Nordic Tech & Finance
add_feed "https://techsavvy.media/feed/" "Tech Savvy Media"
add_feed "https://nordic9.com/feed/" "Nordic 9"
add_feed "https://www.breakit.se/feed/rss" "Breakit"

echo ""
echo "========================================"
echo "📊 Import Summary:"
echo "   Total feeds processed: $TOTAL"
echo "   Successfully imported: $SUCCESS"
echo "   Skipped/Already exists: $((TOTAL - SUCCESS))"
echo ""

if [ $SUCCESS -gt 0 ]; then
    echo "✨ Success! $SUCCESS feeds imported to FreshRSS"
    echo ""
    echo "🔄 Refreshing all feeds for admin user..."
    docker-compose exec -T freshrss ./cli/actualize-user.php --user admin
    
    echo ""
    echo "📈 Triggering scoring engine..."
    curl -X POST http://localhost:8000/refresh 2>/dev/null
    
    echo ""
    echo "✅ Done! Your feeds are now being processed."
    echo "   Visit http://localhost:3001 to view scored articles"
else
    echo "ℹ️  All feeds already exist or no new feeds imported"
fi