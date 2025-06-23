import boto3
from app.core.config import settings
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Initialize R2 client - configuration is validated in settings
# Log initialization attempt
logger.info("Initializing R2 client with settings from environment...")

# Validate required settings
if not settings.R2_ENDPOINT:
    raise ValueError("R2_ENDPOINT is missing or empty")
if not settings.R2_ACCESS_KEY_ID:
    raise ValueError("R2_ACCESS_KEY_ID is missing or empty")
if not settings.R2_SECRET_ACCESS_KEY:
    raise ValueError("R2_SECRET_ACCESS_KEY is missing or empty")
if not settings.R2_BUCKET:
    raise ValueError("R2_BUCKET is missing or empty")

# Create session and client
session = boto3.session.Session()
s3 = session.client(
    service_name="s3",
    endpoint_url=settings.R2_ENDPOINT,
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    region_name="auto",  # Let boto3 determine region automatically
)
BUCKET = settings.R2_BUCKET

# Log connection info
logger.info(f"Initialized R2 client with endpoint: {settings.R2_ENDPOINT} and bucket: {BUCKET}")

def upload_fileobj(fileobj, key: str, content_type: str = None) -> str:
    """
    Upload a file object to R2 storage
    """
    # First, read the fileobj contents
    try:
        contents = fileobj.read()
        # Reset the file pointer in case we need to reuse it
        fileobj.seek(0)
    except Exception as e:
        logger.error(f"Failed to read file contents: {e}")
        raise
    
    try:
        logger.info(f"Uploading file to R2 bucket: {BUCKET}, key: {key}")
        
        # Set up upload parameters
        extra_args = {"ACL": "public-read"}
        if content_type:
            extra_args["ContentType"] = content_type
        
        # Create a BytesIO object from contents for upload
        stream = BytesIO(contents)
        
        # Upload to R2
        s3.upload_fileobj(stream, BUCKET, key, ExtraArgs=extra_args)
        
        # Generate the correct public URL based on endpoint format
        # Cloudflare R2 URL format might be https://<id>.r2.cloudflarestorage.com/<bucket>
        # or might end with the bucket name already
        if BUCKET in settings.R2_ENDPOINT:
            url = f"{settings.R2_ENDPOINT}/{key}"
        else:
            url = f"{settings.R2_ENDPOINT}/{BUCKET}/{key}"
            
        logger.info(f"File uploaded to R2 successfully: {url}")
        return url
    except Exception as e:
        logger.error(f"Failed to upload file to R2: {e}")
        raise RuntimeError(f"Failed to upload to R2: {e}")

# Flag to control direct public URL access
# Set to True to use Cloudflare public URL, False to proxy through the API
public_access_allowed = True

# Cloudflare public URL domain (adjust as needed based on your specific R2 setup)
CLOUDFLARE_PUBLIC_URL = "https://pub-f7fdd9a323df414ba0d52f4474f6f12f.r2.dev"

def get_file_url(key: str, use_api_proxy: bool = False):
    """
    Get the URL for a file in R2
    
    Args:
        key: The key of the file in R2
        use_api_proxy: Force using API proxy even if public access is allowed
    
    Returns:
        URL string for accessing the file
    """
    # If public access is allowed and we don't explicitly request API proxy, use Cloudflare public URL
    if public_access_allowed and not use_api_proxy:
        # Use the direct Cloudflare public URL
        return f"{CLOUDFLARE_PUBLIC_URL}/{key}"
    else:
        # Use API proxy (for local dev or when direct access is not allowed)
        if key.startswith("final/"):
            # For final videos, use our streaming API endpoint with the original filename
            # Extract original filename from the final/final_FILENAME.mp4 key format
            # The format is "final/final_originalname.mp4"
            try:
                original_filename = key.split("final_")[1].split(".mp4")[0] + ".webm"
                return f"/api/stream_final_video/{original_filename}"
            except Exception as e:
                logger.error(f"Error extracting original filename from key {key}: {e}")
                # Fall back to standard URL format
                pass
                
        # For other files or if filename extraction fails, generate the standard R2 URL
        if BUCKET in settings.R2_ENDPOINT:
            return f"{settings.R2_ENDPOINT}/{key}"
        else:
            return f"{settings.R2_ENDPOINT}/{BUCKET}/{key}"

def file_exists(key: str) -> bool:
    """
    Check if a file exists in R2 storage
    """
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except Exception as e:
        # Check if it's a 404 (NoSuchKey or Not Found) error
        error_message = str(e)
        if "404" in error_message or "NoSuchKey" in error_message:
            return False
        
        # Log other errors but don't block the flow
        logger.error(f"Error checking if file exists in R2: {e}")
        return False
