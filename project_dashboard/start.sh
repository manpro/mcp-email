#!/bin/bash

# Start Project Dashboard
echo "🚀 Starting Project Dashboard..."

# Check if already running
if pgrep -f "python3.*app.py" > /dev/null; then
    echo "⚠️  Project Dashboard is already running!"
    echo "   Use 'ps aux | grep app.py' to see the process"
    echo "   Use './stop.sh' to stop it first"
    exit 1
fi

# Start the server in background
cd /home/micke/project_dashboard
nohup python3 app.py > dashboard.log 2>&1 &

# Wait a moment and check if it started
sleep 2
if pgrep -f "python3.*app.py" > /dev/null; then
    echo "✅ Project Dashboard started successfully!"
    echo "📱 Access it at: http://172.16.16.148:6888"
    echo "📱 Local access: http://localhost:6888"
    echo "📋 Logs: tail -f /home/micke/project_dashboard/dashboard.log"
else
    echo "❌ Failed to start Project Dashboard"
    echo "📋 Check the logs: cat /home/micke/project_dashboard/dashboard.log"
    exit 1
fi