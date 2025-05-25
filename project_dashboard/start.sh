#!/bin/bash

echo "🚀 Starting Project Dashboard..."

# Stop any existing instances first
./stop.sh

# Install systemd service if not exists
if [ ! -f /etc/systemd/system/project-dashboard.service ]; then
    echo "Installing systemd service..."
    sudo cp project-dashboard.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable project-dashboard
fi

# Start the service
sudo systemctl start project-dashboard

# Wait a moment for startup
sleep 3

# Check if service is running
if sudo systemctl is-active --quiet project-dashboard; then
    echo "✅ Project Dashboard service is running"
    echo "🌐 Available at: http://172.16.16.148:6888"
else
    echo "❌ Failed to start service, checking status..."
    sudo systemctl status project-dashboard
fi