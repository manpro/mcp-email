FROM node:20-slim

WORKDIR /app

# Install Python and build dependencies for native modules
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy all application files first (including node_modules)
COPY . .

# Remove existing node_modules and reinstall fresh in container
RUN rm -rf node_modules && \
    npm ci --omit=dev

# Create database directory
RUN mkdir -p /app/data

# Environment variables (can be overridden)
ENV PORT=3015
ENV REDIS_HOST=172.17.0.1
ENV REDIS_PORT=6381
ENV LLM_CONFIG=./llm-config.json
ENV DATABASE_PATH=/app/data/email_cache.db

EXPOSE 3015

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3015/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 1

CMD ["node", "integrated-email-service.js"]