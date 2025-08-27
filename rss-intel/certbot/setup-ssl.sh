#!/bin/bash

# RSS Intelligence - Automatic SSL Certificate Setup
# This script sets up Let's Encrypt certificates with automatic renewal

set -e

DOMAIN="${SSL_DOMAIN:-localhost}"
EMAIL="${SSL_EMAIL:-admin@example.com}"
STAGING="${SSL_STAGING:-0}"

echo "🔒 Setting up SSL certificates for RSS Intelligence"
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo "Staging mode: $STAGING"

# Wait for nginx to be ready
echo "⏳ Waiting for Nginx..."
sleep 10

# Check if we already have certificates
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✅ Certificate already exists for $DOMAIN"
    exit 0
fi

# Use staging server for testing
if [ "$STAGING" = "1" ]; then
    CERTBOT_ARGS="--staging"
    echo "⚠️  Using Let's Encrypt staging server"
else
    CERTBOT_ARGS=""
    echo "🚀 Using Let's Encrypt production server"
fi

# Check if domain resolves to this server
echo "🔍 Checking domain resolution..."
if [ "$DOMAIN" != "localhost" ]; then
    if ! nslookup $DOMAIN > /dev/null 2>&1; then
        echo "❌ Domain $DOMAIN does not resolve. Please set up DNS first."
        echo "   Point your domain to this server's IP address."
        exit 1
    fi
    echo "✅ Domain resolves correctly"
fi

# Create temporary nginx config for certificate generation
echo "📝 Creating temporary nginx configuration..."
cat > /tmp/nginx-certbot.conf << EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name $DOMAIN;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://\$server_name\$request_uri;
        }
    }
}
EOF

# Stop nginx and start with temporary config
echo "🔄 Switching to certificate generation mode..."
nginx -s quit || true
sleep 2
nginx -c /tmp/nginx-certbot.conf

# Generate certificate
echo "🔐 Requesting SSL certificate..."
certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    $CERTBOT_ARGS \
    -d $DOMAIN

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate generated successfully!"
    
    # Update nginx configuration with real domain
    sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /etc/nginx/nginx.conf
    
    # Stop temporary nginx and start with SSL config
    nginx -s quit || true
    sleep 2
    nginx -g "daemon off;" &
    
    echo "🔒 HTTPS is now active for $DOMAIN"
    echo "📋 Certificate information:"
    certbot certificates
    
else
    echo "❌ Failed to generate SSL certificate"
    echo "🔧 Troubleshooting tips:"
    echo "   1. Ensure domain $DOMAIN points to this server"
    echo "   2. Check firewall allows ports 80 and 443"
    echo "   3. Try with SSL_STAGING=1 first"
    exit 1
fi