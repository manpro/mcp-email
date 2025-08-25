#!/bin/bash

# RSS Intelligence - Cloudflare Tunnel Setup Script
# This script sets up a Cloudflare tunnel for mobile access to the RSS Intelligence dashboard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TUNNEL_NAME="rss-intel-mobile"
SERVICE_NAME="rss-intel-tunnel"
INTERNAL_URL="http://localhost:3000"
DOMAIN_NAME=""  # Will be set by user input

echo -e "${GREEN}RSS Intelligence - Cloudflare Tunnel Setup${NC}"
echo "This script will set up a secure tunnel for mobile access to your RSS Intelligence dashboard."
echo

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}Installing cloudflared...${NC}"
    
    # Download and install cloudflared
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb
        rm cloudflared-linux-amd64.deb
    else
        echo -e "${RED}Please install cloudflared manually for your operating system${NC}"
        echo "Visit: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        exit 1
    fi
    
    echo -e "${GREEN}✓ cloudflared installed successfully${NC}"
else
    echo -e "${GREEN}✓ cloudflared is already installed${NC}"
fi

# Login to Cloudflare (if not already logged in)
echo
echo -e "${YELLOW}Authenticating with Cloudflare...${NC}"
if ! cloudflared tunnel list > /dev/null 2>&1; then
    echo "Please complete the authentication in your browser:"
    cloudflared tunnel login
else
    echo -e "${GREEN}✓ Already authenticated with Cloudflare${NC}"
fi

# Get domain name from user
echo
read -p "Enter your domain name (e.g., yourdomain.com): " DOMAIN_NAME
if [ -z "$DOMAIN_NAME" ]; then
    echo -e "${RED}Domain name is required${NC}"
    exit 1
fi

# Choose subdomain
read -p "Enter subdomain for RSS Intelligence (default: rss): " SUBDOMAIN
SUBDOMAIN=${SUBDOMAIN:-rss}
FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN_NAME}"

# Create tunnel (if it doesn't exist)
echo
echo -e "${YELLOW}Creating Cloudflare tunnel...${NC}"
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo -e "${GREEN}✓ Tunnel '$TUNNEL_NAME' already exists${NC}"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
else
    TUNNEL_ID=$(cloudflared tunnel create "$TUNNEL_NAME" | grep -o '[a-f0-9-]\{36\}' | head -1)
    echo -e "${GREEN}✓ Created tunnel '$TUNNEL_NAME' with ID: $TUNNEL_ID${NC}"
fi

# Create DNS record
echo
echo -e "${YELLOW}Creating DNS record for $FULL_DOMAIN...${NC}"
if cloudflared tunnel route dns "$TUNNEL_NAME" "$FULL_DOMAIN"; then
    echo -e "${GREEN}✓ DNS record created for $FULL_DOMAIN${NC}"
else
    echo -e "${YELLOW}Note: DNS record might already exist${NC}"
fi

# Create tunnel configuration
CONFIG_FILE="$HOME/.cloudflared/config.yml"
echo
echo -e "${YELLOW}Creating tunnel configuration...${NC}"

mkdir -p "$HOME/.cloudflared"

cat > "$CONFIG_FILE" << EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $FULL_DOMAIN
    service: $INTERNAL_URL
    originRequest:
      connectTimeout: 30s
      tlsTimeout: 30s
      tcpKeepAlive: 30s
      noHappyEyeballs: false
      keepAliveConnections: 10
      keepAliveTimeout: 30s
      httpHostHeader: localhost
  - service: http_status:404

EOF

echo -e "${GREEN}✓ Configuration created at $CONFIG_FILE${NC}"

# Install as system service
echo
echo -e "${YELLOW}Installing tunnel as system service...${NC}"

sudo cloudflared service install

# Create custom service file for RSS Intelligence
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Cloudflare Tunnel for RSS Intelligence
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/cloudflared tunnel --config $CONFIG_FILE run
Restart=always
RestartSec=5
KillMode=mixed
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo -e "${GREEN}✓ Tunnel service installed and started${NC}"

# Create startup script for RSS Intelligence
STARTUP_SCRIPT="./start-rss-mobile.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Start RSS Intelligence with mobile access

echo "Starting RSS Intelligence backend..."
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=\$!

echo "Starting RSS Intelligence frontend..."
cd web && npm start &
FRONTEND_PID=\$!

echo "Starting Cloudflare tunnel..."
sudo systemctl start $SERVICE_NAME

echo
echo "RSS Intelligence is now accessible at:"
echo "  Local: http://localhost:3000"
echo "  Mobile: https://$FULL_DOMAIN"
echo
echo "To stop all services, run: ./stop-rss-mobile.sh"
echo

# Wait for interrupt
trap 'echo "Shutting down..."; kill \$BACKEND_PID \$FRONTEND_PID; sudo systemctl stop $SERVICE_NAME; exit' INT
wait
EOF

chmod +x "$STARTUP_SCRIPT"

# Create stop script
STOP_SCRIPT="./stop-rss-mobile.sh"
cat > "$STOP_SCRIPT" << EOF
#!/bin/bash
# Stop RSS Intelligence services

echo "Stopping Cloudflare tunnel..."
sudo systemctl stop $SERVICE_NAME

echo "Stopping RSS Intelligence services..."
pkill -f "uvicorn app.main:app"
pkill -f "npm start"
pkill -f "next start"

echo "All services stopped."
EOF

chmod +x "$STOP_SCRIPT"

# Test tunnel status
echo
echo -e "${YELLOW}Testing tunnel status...${NC}"
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ Tunnel service is running${NC}"
else
    echo -e "${YELLOW}⚠ Starting tunnel service...${NC}"
    sudo systemctl start "$SERVICE_NAME"
    sleep 3
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓ Tunnel service started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start tunnel service${NC}"
        sudo systemctl status "$SERVICE_NAME"
    fi
fi

# Final instructions
echo
echo -e "${GREEN}🎉 Cloudflare Tunnel Setup Complete!${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Start your RSS Intelligence application:"
echo "   ${STARTUP_SCRIPT}"
echo
echo "2. Access your dashboard:"
echo "   • Local: http://localhost:3000"
echo "   • Mobile: https://$FULL_DOMAIN"
echo
echo -e "${YELLOW}Service Management:${NC}"
echo "• Check status: sudo systemctl status $SERVICE_NAME"
echo "• View logs: sudo journalctl -f -u $SERVICE_NAME"
echo "• Stop service: sudo systemctl stop $SERVICE_NAME"
echo "• Restart service: sudo systemctl restart $SERVICE_NAME"
echo
echo -e "${YELLOW}Security Notes:${NC}"
echo "• Your tunnel uses Cloudflare's security features"
echo "• Consider enabling Cloudflare Access for additional protection"
echo "• Monitor tunnel usage in your Cloudflare dashboard"
echo
echo -e "${GREEN}Enjoy secure mobile access to your RSS Intelligence dashboard!${NC}"