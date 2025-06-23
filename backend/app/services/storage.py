import logging
import os
import uuid
from io import BytesIO
from app.services.r2 import upload_fileobj, get_file_url, file_exists as r2_file_exists

logger = logging.getLogger(__name__)

async def save_upload_file(upload_file):
    """
    Upload a file to R2 cloud storage
    """
    if not upload_file or not upload_file.filename:
        logger.error("Invalid upload file: empty or missing filename")
        raise ValueError("Invalid upload file: empty or missing filename")
        
    try:
        # Get file information
        original_filename = upload_file.filename
        
        # Generate a unique filename based on the original to avoid collisions
        # Use the original extension if available
        name, ext = os.path.splitext(original_filename)
        key = f"{name}-{uuid.uuid4().hex[:8]}{ext}"
        
        logger.info(f"Processing file upload: {key}, content type: {upload_file.content_type}")
        
        # Read the file content
        file_content = await upload_file.read()
        if not file_content:
            logger.error("Empty file content")
            raise ValueError("Empty file content")
            
        # Create a BytesIO object from file content
        fileobj = BytesIO(file_content)
        
        # Upload to R2
        url = upload_fileobj(fileobj, key, content_type=upload_file.content_type)
        logger.info(f"File uploaded successfully to R2: {url}")
        return url
    except Exception as e:
        logger.error(f"Error in save_upload_file: {e}")
        raise RuntimeError(f"Failed to save file: {str(e)}")

def file_exists(filename: str) -> bool:
    """
    Check if a file exists in R2 storage
    """
    return r2_file_exists(filename)
