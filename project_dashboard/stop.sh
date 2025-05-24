#!/bin/bash

# Stop Project Dashboard
echo "🛑 Stopping Project Dashboard..."

# Find and kill the process
PIDS=$(pgrep -f "python3.*app.py")

if [ -z "$PIDS" ]; then
    echo "ℹ️  Project Dashboard is not running"
    exit 0
fi

# Kill the processes
for PID in $PIDS; do
    echo "🔪 Killing process $PID"
    kill $PID
done

# Wait a moment and check
sleep 2
REMAINING=$(pgrep -f "python3.*app.py")

if [ -z "$REMAINING" ]; then
    echo "✅ Project Dashboard stopped successfully!"
else
    echo "⚠️  Some processes are still running, force killing..."
    for PID in $REMAINING; do
        kill -9 $PID
    done
    echo "✅ Project Dashboard force stopped!"
fi