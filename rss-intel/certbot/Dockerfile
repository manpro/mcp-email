FROM certbot/certbot:latest

# Install additional tools
RUN apk add --no-cache bash curl nginx

# Copy scripts
COPY setup-ssl.sh /usr/local/bin/setup-ssl.sh
COPY renew-ssl.sh /usr/local/bin/renew-ssl.sh

# Make scripts executable
RUN chmod +x /usr/local/bin/setup-ssl.sh /usr/local/bin/renew-ssl.sh

# Create directories
RUN mkdir -p /var/www/certbot /var/log

# Create cron job for automatic renewal
RUN echo "0 3 * * * /usr/local/bin/renew-ssl.sh >> /var/log/ssl-renewal.log 2>&1" | crontab -

CMD ["/usr/local/bin/setup-ssl.sh"]