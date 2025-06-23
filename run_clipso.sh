#!/bin/bash

# Clipso Run Script
# This script runs the Clipso application (backend + frontend)

# Define colors for console output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display usage information
show_usage() {
  echo -e "${YELLOW}Clipso Run Script${NC}"
  echo "Usage: ./run_clipso.sh [OPTION]"
  echo ""
  echo "Options:"
  echo "  dev      Run both backend and frontend in development mode"
  echo "  backend  Run only the backend server"
  echo "  build    Build the frontend for production"
  echo "  deploy   Build frontend and run backend serving static files"
  echo "  prod     Run the backend in production mode (no rebuilding)"
  echo "  help     Show this help message"
  echo ""
}

# Function to install dependencies
install_dependencies() {
  echo -e "${GREEN}Checking and installing dependencies...${NC}"
  
  # Install Python dependencies
  echo -e "${GREEN}Installing Python dependencies...${NC}"
  pip install -r backend/requirements.txt
  
  # Install Node.js dependencies
  echo -e "${GREEN}Installing Node.js dependencies...${NC}"
  cd frontend
  npm install
  cd ..
}

# Function to run the backend server in development mode
run_backend_dev() {
  echo -e "${GREEN}Starting Clipso backend server in development mode...${NC}"
  cd backend
  python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
}

# Function to run the backend server in production mode
run_backend_prod() {
  echo -e "${GREEN}Starting Clipso backend server in production mode...${NC}"
  cd backend
  python -m uvicorn app.main:app --host 0.0.0.0 --port 5000
}

# Function to run the frontend development server
run_frontend() {
  echo -e "${GREEN}Starting Clipso frontend development server...${NC}"
  cd frontend
  npm run dev
}

# Function to build the frontend for production
build_frontend() {
  echo -e "${GREEN}Building Clipso frontend for production...${NC}"
  
  # Make sure we're in the right directory
  cd "$(dirname "$0")"
  
  # Install dependencies first
  cd frontend
  npm install
  
  # Build the frontend
  npm run build
  
  # Check if the build was successful
  if [ $? -ne 0 ]; then
    echo -e "${RED}Frontend build failed!${NC}"
    return 1
  fi
  
  echo -e "${GREEN}Frontend build successful!${NC}"
  
  # Create static directory in backend if it doesn't exist
  echo -e "${GREEN}Copying frontend build to backend/static...${NC}"
  mkdir -p ../backend/static
  cp -r dist/* ../backend/static/
  
  echo -e "${GREEN}Frontend build deployed to backend/static${NC}"
  
  # Return to root directory
  cd ..
  return 0
}

# Function to deploy the application
deploy_app() {
  # Make sure we're in the right directory
  cd "$(dirname "$0")"
  
  # Install dependencies first
  install_dependencies
  
  # Build the frontend
  build_frontend
  
  # Check if the build was successful
  if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed due to frontend build errors.${NC}"
    exit 1
  fi
  
  # Run the backend server in production mode
  run_backend_prod
}

# Main execution
case "$1" in
  "dev")
    echo -e "${YELLOW}Running Clipso in development mode...${NC}"
    echo -e "${YELLOW}This will start both the backend and frontend servers.${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop both servers.${NC}"
    
    # Install dependencies
    install_dependencies
    
    # Run both servers in background
    run_backend_dev &
    BACKEND_PID=$!
    run_frontend &
    FRONTEND_PID=$!
    
    # Wait for either process to finish
    wait $BACKEND_PID $FRONTEND_PID
    
    # Kill both processes on exit
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    ;;
    
  "backend")
    # Install dependencies
    install_dependencies
    run_backend_dev
    ;;
    
  "build")
    build_frontend
    ;;
    
  "deploy")
    deploy_app
    ;;
    
  "prod")
    # Just run the backend in production mode without rebuilding
    run_backend_prod
    ;;
    
  "help"|*)
    show_usage
    ;;
esac