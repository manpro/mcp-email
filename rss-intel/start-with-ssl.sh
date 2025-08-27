#!/bin/bash

# RSS Intelligence - Start with HTTPS
echo "🚀 Starting RSS Intelligence with HTTPS"
echo "========================================"

# Check if domain is set
if [ -z "$SSL_DOMAIN" ] || [ "$SSL_DOMAIN" = "localhost" ]; then
    echo "⚠️  Warning: SSL_DOMAIN not set or set to localhost"
    echo "   For production, set SSL_DOMAIN=your-domain.com in .env"
    echo "   Currently running in development mode"
fi

# Check if email is set
if [ -z "$SSL_EMAIL" ] || [ "$SSL_EMAIL" = "admin@example.com" ]; then
    echo "⚠️  Warning: SSL_EMAIL not properly set"
    echo "   Set SSL_EMAIL=your-email@domain.com in .env"
fi

# Load environment variables
if [ -f .env ]; then
    source .env
    echo "✅ Loaded .env file"
else
    echo "ℹ️  No .env file found, using defaults"
fi

# Start base services
echo "🔄 Starting base services..."
docker-compose up -d postgres freshrss rsshub backend web weaviate

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 20

# Start nginx
echo "🌐 Starting Nginx reverse proxy..."
docker-compose up -d nginx

# Setup SSL if domain is not localhost
if [ "$SSL_DOMAIN" != "localhost" ] && [ -n "$SSL_DOMAIN" ]; then
    echo "🔒 Setting up SSL certificate..."
    docker-compose --profile ssl up -d certbot
    
    # Wait for certificate generation
    echo "⏳ Waiting for SSL certificate generation..."
    docker-compose logs -f certbot &
    LOGS_PID=$!
    
    # Wait for certbot to complete
    while docker-compose ps certbot | grep -q "Up"; do
        sleep 5
    done
    
    kill $LOGS_PID 2>/dev/null || true
    
    # Check if certificate was generated
    if docker exec rss-nginx test -f "/etc/letsencrypt/live/$SSL_DOMAIN/fullchain.pem"; then
        echo "✅ SSL certificate generated successfully!"
        echo "🔒 HTTPS is now active at: https://$SSL_DOMAIN"
        
        # Restart nginx with SSL configuration
        docker-compose restart nginx
        
        # Set up automatic renewal
        echo "⏰ Setting up automatic certificate renewal..."
        (crontab -l 2>/dev/null; echo "0 3 * * * cd $(pwd) && docker-compose exec nginx /usr/local/bin/renew-ssl.sh") | crontab -
        echo "✅ Automatic renewal configured (runs daily at 3 AM)"
        
    else
        echo "❌ SSL certificate generation failed"
        echo "🔧 Running in HTTP mode. Check the logs above for issues."
        echo "💡 Try setting SSL_STAGING=1 first to test with staging server"
    fi
else
    echo "ℹ️  Running in development mode (HTTP only)"
    echo "🌐 Access at: http://localhost"
fi

echo ""
echo "🎉 RSS Intelligence is running!"
echo "================================"
echo "📊 Services Status:"
docker-compose ps

if [ "$SSL_DOMAIN" != "localhost" ] && [ -n "$SSL_DOMAIN" ]; then
    echo ""
    echo "🔗 Access URLs:"
    echo "   HTTPS: https://$SSL_DOMAIN"
    echo "   HTTP:  http://$SSL_DOMAIN (redirects to HTTPS)"
else
    echo ""
    echo "🔗 Access URLs:"
    echo "   Frontend: http://localhost"
    echo "   Backend:  http://localhost/api/"
fi

echo ""
echo "🔧 Management Commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   SSL status:    docker-compose exec nginx /usr/local/bin/renew-ssl.sh --dry-run"