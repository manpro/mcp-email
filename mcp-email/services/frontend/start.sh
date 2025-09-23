#!/bin/bash

# Start the email proxy server in the background
echo "Starting email proxy server on port 3625..."
node email-proxy-server.cjs &

# Wait a moment for the proxy to start
sleep 2

# Start the Vite dev server
echo "Starting frontend on port 3623..."
npm run dev -- --host 0.0.0.0 --port 3623