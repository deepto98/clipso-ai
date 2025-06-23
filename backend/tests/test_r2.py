"""
Test module for R2 storage functionality
This ensures the R2 storage service is working correctly without any fallbacks
"""

import os
import pytest
import boto3
from io import BytesIO
import logging
import time
import secrets
from botocore.exceptions import ClientError
from app.core.config import settings
from app.services.r2 import upload_fileobj, get_file_url, s3, BUCKET, file_exists

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_r2_connection():
    """Test that the R2 connection is working correctly"""
    # Check that the R2 settings are configured
    assert settings.R2_ENDPOINT, "R2_ENDPOINT is not configured"
    assert settings.R2_ACCESS_KEY_ID, "R2_ACCESS_KEY_ID is not configured"
    assert settings.R2_SECRET_ACCESS_KEY, "R2_SECRET_ACCESS_KEY is not configured"
    assert settings.R2_BUCKET, "R2_BUCKET is not configured"

    # Check that the R2 client is initialized
    assert s3 is not None, "R2 client (s3) is not initialized"
    assert BUCKET is not None, "R2 BUCKET is not initialized"

    # Log settings (without secret values)
    logger.info(f"R2_ENDPOINT: {settings.R2_ENDPOINT}")
    logger.info(f"R2_BUCKET: {settings.R2_BUCKET}")
    logger.info(f"R2_ACCESS_KEY_ID: {'*' * 4 + settings.R2_ACCESS_KEY_ID[-4:] if settings.R2_ACCESS_KEY_ID else 'Not set'}")
    logger.info(f"R2_SECRET_ACCESS_KEY: {'*' * 8 if settings.R2_SECRET_ACCESS_KEY else 'Not set'}")

    # Try a simple operation to verify connection
    try:
        # List objects in the bucket to verify permissions
        response = s3.list_objects_v2(Bucket=BUCKET, MaxKeys=1)
        logger.info(f"Successfully connected to R2 bucket: {BUCKET}")
        
        # Check if there are any objects in the bucket
        if 'Contents' in response and response['Contents']:
            object_count = len(response['Contents'])
            logger.info(f"Found {object_count} objects in the bucket.")
            
            # Display first object
            if object_count > 0:
                first_object = response['Contents'][0]
                logger.info(f"First object key: {first_object['Key']}")
        else:
            logger.info("Bucket is empty.")
    except Exception as e:
        logger.error(f"Failed to list objects in bucket: {e}")
        raise


def test_upload_and_retrieve():
    """Test uploading a file to R2 and retrieving it"""
    # Create a test file with timestamp to ensure uniqueness
    test_content = f"This is a test file created at {time.strftime('%Y-%m-%d %H:%M:%S')}".encode('utf-8')
    file_obj = BytesIO(test_content)
    
    # Generate a unique key using a random suffix
    random_suffix = secrets.token_hex(4)
    key = f"test-file-{random_suffix}.txt"
    
    logger.info(f"Testing upload with key: {key}")

    try:
        # Upload the file
        url = upload_fileobj(file_obj, key, content_type="text/plain")

        # Verify the URL format
        assert url.startswith(settings.R2_ENDPOINT), f"URL does not start with R2_ENDPOINT: {url}"
        assert BUCKET in url, f"URL does not contain bucket name: {url}"
        assert key in url, f"URL does not contain file key: {url}"

        logger.info(f"File uploaded successfully: {url}")
        
        # Check if file exists using the file_exists function
        assert file_exists(key), f"file_exists check failed for key: {key}"
        logger.info(f"file_exists check passed for key: {key}")

        # Try to retrieve the file to verify it exists
        try:
            logger.info(f"Retrieving the uploaded file...")
            response = s3.get_object(Bucket=BUCKET, Key=key)
            content = response['Body'].read()

            # Verify the content matches
            assert content == test_content, "Retrieved content does not match uploaded content"
            logger.info("✅ File content verification successful!")
        except Exception as e:
            logger.error(f"Failed to retrieve file: {e}")
            raise

        # Clean up - delete the test file (uncommented this section)
        try:
            logger.info(f"Deleting test file: {key}")
            s3.delete_object(Bucket=BUCKET, Key=key)
            logger.info("Test file deleted")
        except Exception as e:
            logger.error(f"Failed to delete test file: {e}")
            raise
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


def test_file_url_generation():
    """Test that get_file_url generates the correct URL format"""
    test_key = "test-file.txt"
    url = get_file_url(test_key)

    # Check URL format
    assert url.startswith(
        settings.R2_ENDPOINT), f"URL does not start with R2_ENDPOINT: {url}"
    assert BUCKET in url, f"URL does not contain bucket name: {url}"
    assert test_key in url, f"URL does not contain file key: {url}"

    # Test with Cloudflare R2 URL format
    expected_url = f"{settings.R2_ENDPOINT}/{BUCKET}/{test_key}"
    assert url == expected_url, f"URL format incorrect. Expected: {expected_url}, Got: {url}"
    
    # Also ensure the file_exists function is properly implemented
    if "test-actually-does-not-exist.txt" not in url:
        assert not file_exists("test-actually-does-not-exist.txt"), "file_exists returned True for non-existent file"
