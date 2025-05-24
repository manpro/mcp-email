#!/bin/bash

# Script för att installera MCP Agents Server som systemd service
set -e

echo "🚀 Installerar MCP Agents Server som systemd service..."

# Kontrollera att vi har npm och TypeScript byggd
if [ ! -f "dist/index.js" ]; then
    echo "📦 Bygger TypeScript projekt..."
    npm run build
fi

# Kopiera service-filen till systemd
echo "📋 Kopierar service-fil till systemd..."
sudo cp mcp-agents-server.service /etc/systemd/system/

# Ladda om systemd konfiguration
echo "🔄 Laddar om systemd daemon..."
sudo systemctl daemon-reload

# Aktivera service för automatisk start
echo "✅ Aktiverar service för automatisk start..."
sudo systemctl enable mcp-agents-server.service

# Starta service
echo "▶️  Startar MCP Agents Server..."
sudo systemctl start mcp-agents-server.service

# Visa status
echo "📊 Status för MCP Agents Server:"
sudo systemctl status mcp-agents-server.service

echo ""
echo "🎉 MCP Agents Server är nu installerad och kommer starta automatiskt vid omstart!"
echo ""
echo "🔌 Tillgängliga endpoints:"
echo "  http://172.16.16.148:3111/agent/gitea-create-issue  # Gitea issues"
echo "  http://172.16.16.148:3111/agent/pg-query           # PostgreSQL"  
echo "  http://172.16.16.148:3111/agent/weaviate-query     # Weaviate search"
echo ""
echo "Användbara kommandon:"
echo "  sudo systemctl status mcp-agents-server    # Visa status"
echo "  sudo systemctl stop mcp-agents-server      # Stoppa service"
echo "  sudo systemctl start mcp-agents-server     # Starta service"
echo "  sudo systemctl restart mcp-agents-server   # Starta om service"
echo "  sudo journalctl -u mcp-agents-server -f    # Visa logs"
echo "  sudo systemctl disable mcp-agents-server   # Inaktivera autostart"