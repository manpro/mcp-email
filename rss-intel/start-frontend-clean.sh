#!/bin/bash

echo "🚀 Starting RSS Intelligence Frontend with Clean Setup"
echo "======================================================"

cd /home/micke/claude-env/rss-intel/web

# Kill any existing processes
echo "🔄 Stopping existing processes..."
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

# Try to remove .next directory
echo "🧹 Cleaning build cache..."
if [ -d ".next" ]; then
    echo "Removing existing .next directory..."
    # Try normal removal first
    rm -rf .next 2>/dev/null || {
        echo "Permission issues detected. Trying alternative cleanup..."
        # Move the problematic directory instead of removing
        mv .next ".next.backup.$(date +%s)" 2>/dev/null || {
            echo "Creating fresh .next directory..."
            mkdir -p .next.clean
            mv .next .next.backup.$(date +%s) 2>/dev/null || true
            mv .next.clean .next 2>/dev/null || true
        }
    }
fi

# Install dependencies if node_modules doesn't exist or is incomplete
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo ""
echo "🎯 Starting Next.js Development Server..."
echo "The frontend will be available at one of these URLs:"
echo "  • http://localhost:3000"
echo "  • http://localhost:3001" 
echo "  • http://localhost:3002"
echo ""
echo "📱 Features available:"
echo "  • Mobile-responsive design"
echo "  • User authentication"
echo "  • Analytics dashboard"
echo "  • A/B testing management"
echo "  • Advanced search"
echo "  • Email newsletter client"
echo ""
echo "🔧 To stop the server, press Ctrl+C"
echo "======================================================"
echo ""

# Start the development server
npm run dev