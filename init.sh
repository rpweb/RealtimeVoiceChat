#!/bin/bash

# Initialize project with pnpm
echo "Initializing RealtimeVoiceChat with pnpm..."

# Install dependencies 
echo "Installing dependencies..."
pnpm install

# Copy environment templates if they exist
if [ -f "server/src/.env.example" ]; then
  echo "Setting up server environment..."
  cp server/src/.env.example server/.env
fi

if [ -f "client-app/.env.example" ]; then
  echo "Setting up client environment..."
  cp client-app/.env.example client-app/.env.local
fi

echo "Setup complete! Run 'pnpm dev' to start both the server and client."
echo ""
echo "For development, you can use:"
echo "  - 'pnpm dev:server' - Start only the backend server"
echo "  - 'pnpm dev:client' - Start only the frontend client"
echo "  - 'pnpm dev' - Start both server and client"
echo "" 