#!/usr/bin/env python3
"""
Clipso Unified Deployment Entry Point
This script starts the backend server which also serves the frontend static files
"""

import os
import subprocess
import sys
import time

def install_dependencies():
    """Install required Python dependencies"""
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], check=True)
    except subprocess.CalledProcessError:
        print("Error: Failed to install Python dependencies.")
        sys.exit(1)

def ensure_frontend_built():
    """Ensure frontend is built and ready to be served"""
    if not os.path.exists(os.path.join("backend", "static", "index.html")):
        print("Frontend static files not found. Running deployment script...")
        try:
            subprocess.run(["./deploy.sh"], check=True)
        except subprocess.CalledProcessError:
            print("Error: Deployment script failed.")
            sys.exit(1)
    else:
        print("Frontend static files found. Skipping build step.")

def start_backend():
    """Start the backend server"""
    print("Starting backend server...")
    os.chdir("backend")
    try:
        # Use exec to replace the current process with uvicorn
        args = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
        print(f"Executing: {' '.join(args)}")
        os.execv(sys.executable, args)
    except Exception as e:
        print(f"Error starting backend server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting Clipso unified application...")
    
    # Make sure we're in the root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Make sure all directories exist
    if not os.path.exists("backend"):
        print("Error: Backend directory not found.")
        sys.exit(1)
    
    if not os.path.exists("frontend"):
        print("Error: Frontend directory not found.")
        sys.exit(1)
    
    # Install dependencies first
    install_dependencies()
    
    # Make sure frontend is built
    ensure_frontend_built()
    
    # Start the backend server
    start_backend()