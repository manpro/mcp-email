FROM nginx:alpine

# Install openssl for certificate generation
RUN apk add --no-cache openssl

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create directory for Let's Encrypt challenges
RUN mkdir -p /var/www/certbot

# Create directory for SSL certificates
RUN mkdir -p /etc/letsencrypt/live

# Generate self-signed certificate for initial setup
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/temp.key \
    -out /etc/nginx/ssl/temp.crt \
    -subj "/C=US/ST=CA/L=SF/O=RSS-Intel/CN=localhost"

# Expose ports
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]