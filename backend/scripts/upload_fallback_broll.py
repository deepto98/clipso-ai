#!/usr/bin/env python3
"""
Script to upload a fallback B-roll image to R2 storage.
This ensures we always have a fallback option if DALL-E API calls fail.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.r2 import upload_fileobj, file_exists, get_file_url
from backend.app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    fallback_key = "broll/fallback.png"
    
    # Check if fallback already exists
    if file_exists(fallback_key):
        logger.info(f"Fallback B-roll already exists at: {get_file_url(fallback_key)}")
        return
    
    # Look for fallback image in uploads directory - different paths depending on where script is run from
    possible_paths = [
        Path("uploads/broll/fallback.png"),  # If run from project root
        Path("../uploads/broll/fallback.png"),  # If run from backend dir
        Path("../../uploads/broll/fallback.png"),  # If run from scripts dir
    ]
    
    fallback_path = None
    for path in possible_paths:
        if path.exists():
            fallback_path = path
            logger.info(f"Found fallback image at: {fallback_path}")
            break
            
    if not fallback_path:
        logger.error(f"Fallback image not found in any of the expected locations: {possible_paths}")
        return
    
    # Upload the fallback image
    logger.info(f"Uploading fallback B-roll from: {fallback_path}")
    try:
        with open(fallback_path, "rb") as f:
            upload_fileobj(f, fallback_key, content_type="image/png")
        
        logger.info(f"Fallback B-roll uploaded successfully to: {get_file_url(fallback_key)}")
    except Exception as e:
        logger.error(f"Failed to upload fallback B-roll: {e}")

if __name__ == "__main__":
    main()