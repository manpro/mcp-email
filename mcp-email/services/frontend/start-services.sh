#!/bin/bash

# Email Manager Service Startup Script
# Starts and monitors all required services

set -e

echo "📧 Email Manager - Service Startup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=3013
FRONTEND_PORT=5173
REDIS_PORT=6381
REDIS_HOST="172.17.0.1"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup EXIT INT TERM

# Check if Redis is running
check_redis() {
    echo -n "Checking Redis on port $REDIS_PORT... "
    if nc -zv $REDIS_HOST $REDIS_PORT 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        echo "Starting Redis container..."
        docker run -d --name email-redis -p $REDIS_PORT:6379 redis:7-alpine
        sleep 2
    fi
}

# Check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}Port $port is already in use. Killing existing process...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Start backend service
start_backend() {
    echo -n "Starting Backend API on port $BACKEND_PORT... "
    check_port $BACKEND_PORT

    cd /home/micke/claude-env/mcp-email/services/email-service
    REDIS_HOST=$REDIS_HOST REDIS_PORT=$REDIS_PORT PORT=$BACKEND_PORT node unified-service.js &
    BACKEND_PID=$!

    sleep 2
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓${NC} (PID: $BACKEND_PID)"
    else
        echo -e "${RED}✗ Failed to start${NC}"
        exit 1
    fi
}

# Start frontend service
start_frontend() {
    echo -n "Starting Frontend on port $FRONTEND_PORT... "
    check_port $FRONTEND_PORT

    cd /home/micke/claude-env/mcp-email/services/frontend
    npm run dev &
    FRONTEND_PID=$!

    sleep 3
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓${NC} (PID: $FRONTEND_PID)"
    else
        echo -e "${RED}✗ Failed to start${NC}"
        exit 1
    fi
}

# Monitor services
monitor_services() {
    echo -e "\n${GREEN}All services started successfully!${NC}"
    echo "=================================="
    echo "📧 Frontend: http://localhost:$FRONTEND_PORT"
    echo "🔧 Backend API: http://localhost:$BACKEND_PORT"
    echo "💾 Redis: $REDIS_HOST:$REDIS_PORT"
    echo "=================================="
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

    while true; do
        # Check backend health
        if ! kill -0 $BACKEND_PID 2>/dev/null; then
            echo -e "${RED}Backend crashed! Restarting...${NC}"
            start_backend
        fi

        # Check frontend health
        if ! kill -0 $FRONTEND_PID 2>/dev/null; then
            echo -e "${RED}Frontend crashed! Restarting...${NC}"
            start_frontend
        fi

        sleep 5
    done
}

# Main execution
echo "Starting Email Manager services..."
echo ""

check_redis
start_backend
start_frontend
monitor_services