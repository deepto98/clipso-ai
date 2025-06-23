#!/bin/bash

# Clipso Deployment Script
# This script builds the frontend and deploys it for the backend to serve

echo "Starting Clipso deployment process..."

# Install any missing dependencies for the frontend
echo "Installing frontend dependencies..."
cd frontend
npm install

# Build the frontend
echo "Building frontend..."
npm run build

# Check if the build was successful
if [ $? -ne 0 ]; then
  echo "Frontend build failed!"
  exit 1
fi

# Copy frontend build to backend/static directory
echo "Copying frontend build to backend/static..."
mkdir -p ../backend/static
cp -r dist/* ../backend/static/

echo "Frontend successfully deployed to backend/static"

# Return to root directory
cd ..

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Deployment complete!"