#!/bin/bash

echo "🛑 Stopping Project Dashboard..."

# Stop systemd service if running
sudo systemctl stop project-dashboard 2>/dev/null

# Kill any remaining processes on port 6888
PIDS=$(lsof -ti:6888 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    echo "Killing processes on port 6888: $PIDS"
    kill -9 $PIDS 2>/dev/null
fi

# Kill any python processes running app.py
pkill -f "project_dashboard/app.py" 2>/dev/null

# Wait a moment
sleep 2

# Check if port is free
if lsof -i:6888 >/dev/null 2>&1; then
    echo "❌ Port 6888 still in use"
    exit 1
else
    echo "✅ Port 6888 is now free"
fi