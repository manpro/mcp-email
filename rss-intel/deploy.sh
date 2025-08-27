#!/bin/bash
set -e

# RSS Intelligence Dashboard - Production Deployment Script
# This script helps deploy the system to production environment

echo "🚀 RSS Intelligence Dashboard - Production Deployment"
echo "=================================================="

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"
BACKUP_DIR="/data/backups"
LOG_FILE="/var/log/rss-intel-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Success message
success() {
    echo -e "${GREEN}✓ $1${NC}"
    log "SUCCESS: $1"
}

# Warning message  
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARNING: $1"
}

# Check if script is run as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root (use sudo)"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error_exit "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.production" ]; then
            cp .env.production .env
            warning "Created .env from .env.production template. Please review and modify as needed."
        else
            error_exit ".env file not found. Please create one based on .env.production template."
        fi
    fi
    
    success "Prerequisites check passed"
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    # Create necessary directories
    mkdir -p /data/{image-cache,backups,logs}
    mkdir -p ./nginx/ssl
    mkdir -p ./monitoring
    
    # Set permissions
    chown -R www-data:www-data /data/image-cache || true
    chmod 755 /data/{image-cache,backups,logs}
    
    success "Directories setup completed"
}

# Generate SSL certificates (Let's Encrypt)
setup_ssl() {
    if [ -z "$1" ]; then
        warning "No domain provided, skipping SSL setup"
        return 0
    fi
    
    local domain=$1
    local email=${SSL_EMAIL:-admin@$domain}
    
    log "Setting up SSL certificates for $domain..."
    
    # Check if certificates already exist
    if [ -f "./nginx/ssl/fullchain.pem" ] && [ -f "./nginx/ssl/privkey.pem" ]; then
        success "SSL certificates already exist"
        return 0
    fi
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Generate certificates
    certbot certonly --standalone \
        --email "$email" \
        --agree-tos \
        --no-eff-email \
        -d "$domain" \
        --cert-path ./nginx/ssl/fullchain.pem \
        --key-path ./nginx/ssl/privkey.pem
    
    if [ $? -eq 0 ]; then
        success "SSL certificates generated successfully"
    else
        error_exit "Failed to generate SSL certificates"
    fi
}

# Database backup
backup_database() {
    if [ -z "$1" ]; then
        return 0
    fi
    
    local backup_name="rss_intel_$(date +%Y%m%d_%H%M%S).sql"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log "Creating database backup: $backup_name"
    
    docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U rss rssintel > "$backup_path"
    
    if [ $? -eq 0 ]; then
        gzip "$backup_path"
        success "Database backup created: ${backup_path}.gz"
    else
        warning "Database backup failed (this is normal for first deployment)"
    fi
}

# Deploy application
deploy() {
    log "Starting deployment..."
    
    # Pull latest images
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build custom images
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Run database migrations
    log "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    sleep 30  # Wait for database to be ready
    
    docker-compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
    
    # Start all services
    log "Starting all services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    success "Deployment completed"
}

# Health check
health_check() {
    log "Performing health checks..."
    
    # Wait for services to be ready
    sleep 30
    
    # Check backend health
    local backend_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
    if [ "$backend_health" = "200" ]; then
        success "Backend health check passed"
    else
        error_exit "Backend health check failed (HTTP $backend_health)"
    fi
    
    # Check frontend
    local frontend_health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
    if [ "$frontend_health" = "200" ]; then
        success "Frontend health check passed"
    else
        error_exit "Frontend health check failed (HTTP $frontend_health)"
    fi
    
    # Check cache
    log "Warming up cache..."
    curl -s -X POST http://localhost/api/cache/warm-up > /dev/null || true
    
    success "All health checks passed"
}

# Setup monitoring (optional)
setup_monitoring() {
    if [ "$1" = "true" ]; then
        log "Setting up monitoring stack..."
        docker-compose -f "$COMPOSE_FILE" --profile monitoring up -d
        success "Monitoring stack deployed"
    fi
}

# Setup automated backups
setup_backups() {
    log "Setting up automated backups..."
    
    # Create backup script
    cat > /usr/local/bin/rss-intel-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/data/backups"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
COMPOSE_FILE="/opt/rss-intel/docker-compose.prod.yml"

# Create backup
cd /opt/rss-intel
backup_name="rss_intel_$(date +%Y%m%d_%H%M%S).sql"
docker-compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U rss rssintel | gzip > "$BACKUP_DIR/$backup_name.gz"

# Clean old backups
find "$BACKUP_DIR" -name "rss_intel_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $backup_name.gz"
EOF
    
    chmod +x /usr/local/bin/rss-intel-backup.sh
    
    # Add cron job
    local cron_schedule=${BACKUP_SCHEDULE:-"0 2 * * *"}
    echo "$cron_schedule /usr/local/bin/rss-intel-backup.sh >> /var/log/rss-intel-backup.log 2>&1" | crontab -
    
    success "Automated backups configured"
}

# Main deployment function
main() {
    local command=${1:-"deploy"}
    local domain=${DOMAIN:-""}
    
    log "Starting RSS Intelligence deployment with command: $command"
    
    case $command in
        "deploy"|"full")
            check_root
            check_prerequisites
            setup_directories
            
            if [ -n "$domain" ]; then
                setup_ssl "$domain"
            fi
            
            backup_database "existing"
            deploy
            health_check
            
            if [ "$PROMETHEUS_ENABLED" = "true" ]; then
                setup_monitoring true
            fi
            
            setup_backups
            
            success "🎉 RSS Intelligence Dashboard deployed successfully!"
            echo ""
            echo "Access your dashboard at:"
            if [ -n "$domain" ]; then
                echo "  🌐 https://$domain"
            else
                echo "  🌐 http://localhost"
            fi
            echo ""
            echo "System metrics: /system/metrics"
            echo "API docs: /api/docs"
            echo "Cache stats: /api/cache/status"
            ;;
            
        "update")
            log "Updating existing deployment..."
            backup_database "pre-update"
            docker-compose -f "$COMPOSE_FILE" pull
            docker-compose -f "$COMPOSE_FILE" build --no-cache
            docker-compose -f "$COMPOSE_FILE" up -d
            health_check
            success "Update completed successfully!"
            ;;
            
        "backup")
            backup_database "manual"
            ;;
            
        "restore")
            if [ -z "$2" ]; then
                error_exit "Please specify backup file: $0 restore <backup_file>"
            fi
            log "Restoring from backup: $2"
            zcat "$2" | docker-compose -f "$COMPOSE_FILE" exec -T postgres \
                psql -U rss -d rssintel
            success "Restore completed"
            ;;
            
        "ssl")
            check_root
            setup_ssl "$domain"
            ;;
            
        "logs")
            docker-compose -f "$COMPOSE_FILE" logs -f "${2:-backend}"
            ;;
            
        "stop")
            docker-compose -f "$COMPOSE_FILE" down
            success "Services stopped"
            ;;
            
        "status")
            docker-compose -f "$COMPOSE_FILE" ps
            echo ""
            echo "System health:"
            curl -s http://localhost/health | jq . 2>/dev/null || curl -s http://localhost/health
            ;;
            
        *)
            echo "Usage: $0 {deploy|update|backup|restore|ssl|logs|stop|status}"
            echo ""
            echo "Commands:"
            echo "  deploy  - Full deployment (default)"
            echo "  update  - Update existing deployment"
            echo "  backup  - Create manual backup"
            echo "  restore - Restore from backup file"
            echo "  ssl     - Setup/renew SSL certificates"
            echo "  logs    - Show service logs"
            echo "  stop    - Stop all services"
            echo "  status  - Show service status"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"