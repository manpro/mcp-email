#!/bin/bash

# RSS Intelligence - Automatic SSL Certificate Renewal
# This script runs daily to check and renew certificates

set -e

echo "🔄 Checking SSL certificate renewal..."

# Check if certificates need renewal (30 days before expiry)
if certbot renew --dry-run --quiet; then
    echo "✅ Certificate check passed"
    
    # Actually renew if needed
    if certbot renew --quiet; then
        echo "🔄 Certificate renewed, reloading nginx..."
        nginx -s reload
        echo "✅ SSL certificate renewal completed"
        
        # Log renewal event
        echo "$(date): SSL certificate renewed for $(hostname)" >> /var/log/ssl-renewal.log
    else
        echo "ℹ️  Certificate still valid, no renewal needed"
    fi
else
    echo "⚠️  Certificate renewal check failed"
    exit 1
fi