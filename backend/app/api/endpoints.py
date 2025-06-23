import logging
import time
from fastapi import APIRouter, UploadFile, BackgroundTasks, Depends, HTTPException, Body, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.services.storage import save_upload_file, file_exists
from app.services.caption import generate_transcript, transcript_exists, load_transcript, fetch_b_roll
from app.db import get_db
from app.models import Video

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload")
async def upload_video(file: UploadFile, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Received upload for file: {file.filename}")
        
        # Make sure we have a valid file
        if not file or not file.filename:
            logger.error("No valid file in the request")
            return JSONResponse(
                status_code=400,
                content={"message": "No valid file provided", "success": False}
            )
            
        # Set a default filename if none is provided
        filename = file.filename or f"upload_{int(time.time())}.webm"
        logger.info(f"Processing file: {filename}, content type: {file.content_type}")
        
        file_url = None
        try:
            # First upload to R2 storage
            file_url = await save_upload_file(file)
            logger.info(f"File saved to: {file_url}")
        except Exception as e:
            # Log detailed error but return generic message to frontend
            logger.error(f"Failed to save file to storage: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"message": "Failed to upload file to storage", "success": False}
            )
        
        # Only proceed with database if storage upload was successful
        if file_url:
            try:
                # Extract the R2 key from the URL
                r2_key = None
                # Parse out the key from the URL, which is the last part after the final /
                if file_url and '/' in file_url:
                    r2_key = file_url.split('/')[-1]
                
                # Create database record
                video = Video(
                    filename=filename, 
                    r2_key=r2_key, 
                    status="uploaded"
                )
                db.add(video)
                await db.commit()
                await db.refresh(video)
                logger.info(f"Created DB record for: {filename}, R2 key: {r2_key}")
                
                # Return success response
                logger.info(f"Upload successful for: {filename}")
                return JSONResponse({
                    "filename": filename, 
                    "status": "uploaded", 
                    "url": file_url,
                    "success": True
                })
            except Exception as e:
                # Log detailed DB error but return generic message to frontend
                logger.error(f"Database error during video record creation: {e}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"message": "Failed to process upload", "success": False}
                )
        else:
            logger.error("File upload failed: No URL returned from storage")
            return JSONResponse(
                status_code=500,
                content={"message": "Failed to process upload", "success": False}
            )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in upload_video: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Server error occurred", "success": False}
        )

@router.post("/generate_captions")
async def generate_captions(filename: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Log all parameters for debugging
    logger.info(f"Requested caption generation for: {filename}")
    
    # Make sure filename has no spaces or URL encoding
    filename = filename.strip()
    
    # Use filename to find video in database
    try:
        result = await db.execute(select(Video).where(Video.filename == filename))
        video = result.scalar_one_or_none()
        if not video:
            logger.warning(f"Video not found: {filename}")
            raise HTTPException(status_code=404, detail="Video not found.")
        
        # First check if transcript already exists to prevent duplicate processing
        transcript_already_exists = await transcript_exists(filename, db)
        
        if transcript_already_exists:
            logger.info(f"Transcript already exists for {filename}, skipping generation")
            return {
                "status": "completed", 
                "transcript_file": f"{filename}.json",
                "video_id": video.id,
                "message": "Transcript already exists"
            }
        
        # Check if the video is already being processed
        if video.status == "processing":
            logger.info(f"Video {filename} is already being processed, skipping duplicate generation")
            return {
                "status": "processing", 
                "transcript_file": f"{filename}.json",
                "video_id": video.id,
                "message": "Processing already in progress"
            }
        
        # Update status to "processing" to prevent duplicate requests
        video.status = "processing"
        await db.commit()
        
        # Queue background task for transcript generation
        background_tasks.add_task(generate_transcript, filename, db)
        logger.info(f"Caption generation task started for: {filename}")
        
        # Return success response
        return {
            "status": "processing", 
            "transcript_file": f"{filename}.json",
            "video_id": video.id
        }
    except Exception as e:
        logger.error(f"Caption generation request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Caption generation failed: {str(e)}")

@router.get("/transcript/{filename}")
async def get_transcript(filename: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Transcript fetch requested for: {filename}")
    exists = await transcript_exists(filename, db)
    if not exists:
        logger.warning(f"Transcript not found: {filename}")
        raise HTTPException(status_code=404, detail="Transcript not found.")
    transcript = await load_transcript(filename, db)
    logger.info(f"Transcript returned for: {filename}")
    return transcript

@router.get("/video/{share_id}")
async def get_video_by_share_id(
    share_id: str = Path(..., description="The share ID of the video"),
    db: AsyncSession = Depends(get_db)
):

    """
    Get video information by share_id.
    This is used by the frontend to resolve share URLs like /preview/abc123.
    """
    logger.info(f"Video info requested for share_id: {share_id}")
    
    try:
        # Look up the video by share_id
        result = await db.execute(select(Video).where(Video.share_id == share_id))
        video = result.scalar_one_or_none()
        
        if not video:
            logger.warning(f"Video not found for share_id: {share_id}")
            raise HTTPException(status_code=404, detail="Video not found")
            
        # Return basic video info and status
        response = {
            "filename": video.filename,
            "share_id": video.share_id,
            "status": video.status,
            "uploaded_at": video.uploaded_at.isoformat() if video.uploaded_at else None,
        }
        
        # Include final video URL if available
        if video.final_r2_key:
            from app.services.r2 import get_file_url, file_exists
            if file_exists(video.final_r2_key):
                response["final_video_url"] = get_file_url(video.final_r2_key)
                response["has_final_video"] = True
            else:
                response["has_final_video"] = False
        else:
            response["has_final_video"] = False
            
        logger.info(f"Video info returned for share_id: {share_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video by share_id: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving video: {str(e)}")

# Track in-progress API requests to prevent duplicates
broll_generations_in_progress = {}
final_video_generations_in_progress = {}

@router.post("/generate_final_video")
async def generate_final_video(filename: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    logger.info(f"Final video generation requested for: {filename}")
    
    # Make sure filename has no spaces or URL encoding
    filename = filename.strip()
    
    try:
        # Check if video exists
        result = await db.execute(select(Video).where(Video.filename == filename))
        video = result.scalar_one_or_none()
        if not video:
            logger.warning(f"Video not found for final generation: {filename}")
            raise HTTPException(status_code=404, detail="Video not found")
            
        # Check if final video already exists
        if video.final_r2_key:
            from app.services.r2 import get_file_url, file_exists
            if file_exists(video.final_r2_key):
                logger.info(f"Final video already exists for {filename}")
                return {
                    "status": "completed", 
                    "final_video_url": get_file_url(video.final_r2_key)
                }
                
        # Check if already processing
        if filename in final_video_generations_in_progress and final_video_generations_in_progress[filename]:
            logger.info(f"Final video generation already in progress for {filename}")
            return {
                "status": "processing",
                "message": "Final video generation already in progress"
            }
            
        # Check if transcript exists
        transcript_exists_check = await transcript_exists(filename, db)
        if not transcript_exists_check:
            logger.warning(f"Cannot generate final video - transcript not found for {filename}")
            raise HTTPException(status_code=400, detail="Transcript not found. Generate captions first.")
            
        # Mark as processing
        final_video_generations_in_progress[filename] = True
        
        try:
            # Update status to reflect processing
            video.status = "rendering"
            await db.commit()
            
            # Use the enhanced caption generator for better text styling
            from app.services.enhanced_captions import generate_enhanced_final_video
            
            # Don't pass the db session to the background task
            # It will create its own database session to avoid issues
            background_tasks.add_task(generate_enhanced_final_video, filename)
            
            logger.info(f"Enhanced final video generation task started for {filename}")
            return {
                "status": "processing",
                "message": "Final video generation started with clean caption styling"
            }
            
        except Exception as e:
            # Mark as not processing in case of error
            final_video_generations_in_progress[filename] = False
            logger.error(f"Error starting final video generation: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to start video generation: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in final video generation request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
        
@router.get("/final_video/{filename}")
async def get_final_video(filename: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Final video URL requested for: {filename}")
    
    try:
        # Check if video exists
        result = await db.execute(select(Video).where(Video.filename == filename))
        video = result.scalar_one_or_none()
        if not video:
            logger.warning(f"Video not found: {filename}")
            raise HTTPException(status_code=404, detail="Video not found")
            
        # Check for final video
        if not video.final_r2_key:
            logger.warning(f"Final video not generated yet for: {filename}")
            raise HTTPException(status_code=404, detail="Final video not generated yet")
            
        # Check if file exists in R2
        from app.services.r2 import get_file_url, file_exists
        if not file_exists(video.final_r2_key):
            logger.warning(f"Final video file not found in R2: {video.final_r2_key}")
            raise HTTPException(status_code=404, detail="Final video file not found")
            
        # Get the correct URL based on our settings (direct Cloudflare or API proxy)
        from app.services.r2 import get_file_url, public_access_allowed
        
        # Determine the URL based on whether public access is allowed
        if public_access_allowed:
            # Use direct Cloudflare public URL
            final_video_url = get_file_url(video.final_r2_key)
            logger.info(f"Returning direct Cloudflare URL: {final_video_url}")
        else:
            # Use our stream endpoint as a fallback if public access is not allowed
            final_video_url = f"/api/stream_final_video/{filename}"
            logger.info(f"Returning proxied final video URL: {final_video_url}")
            
        return {
            "status": "completed",
            "final_video_url": final_video_url,
            "filename": filename,
            "share_id": video.share_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting final video URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting final video: {str(e)}")
        
@router.get("/final_video_by_share/{share_id}")
async def get_final_video_by_share_id(
    share_id: str = Path(..., description="The share ID of the video"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get final video URL by share_id.
    This provides a more user-friendly method to access videos for sharing.
    """
    logger.info(f"Final video URL requested for share_id: {share_id}")
    
    try:
        # Look up the video by share_id
        result = await db.execute(select(Video).where(Video.share_id == share_id))
        video = result.scalar_one_or_none()
        
        if not video:
            logger.warning(f"Video not found for share_id: {share_id}")
            raise HTTPException(status_code=404, detail="Video not found")
            
        # Check for final video
        if not video.final_r2_key:
            logger.warning(f"Final video not generated yet for share_id: {share_id}")
            raise HTTPException(status_code=404, detail="Final video not generated yet")
            
        # Check if file exists in R2
        from app.services.r2 import get_file_url, file_exists
        if not file_exists(video.final_r2_key):
            logger.warning(f"Final video file not found in R2: {video.final_r2_key}")
            raise HTTPException(status_code=404, detail="Final video file not found")
            
        # Get the correct URL based on our settings (direct Cloudflare or API proxy)
        from app.services.r2 import get_file_url, public_access_allowed
        
        # Determine the URL based on whether public access is allowed
        if public_access_allowed:
            # Use direct Cloudflare public URL
            final_video_url = get_file_url(video.final_r2_key)
            logger.info(f"Returning direct Cloudflare URL: {final_video_url}")
        else:
            # Use our stream endpoint as a fallback if public access is not allowed
            # Use the share_id-based streaming endpoint for cleaner URLs
            final_video_url = f"/api/stream_by_share_id/{share_id}"
            logger.info(f"Returning proxied final video URL by share_id: {final_video_url}")
            
        return {
            "status": "completed",
            "final_video_url": final_video_url,
            "filename": video.filename,
            "share_id": share_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting final video URL by share_id: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting final video: {str(e)}")
        
@router.get("/stream_final_video/{filename}")
async def stream_final_video(filename: str, download: bool = False, db: AsyncSession = Depends(get_db)):
    """
    Stream the final video through our API instead of direct R2 access.
    This avoids cross-origin issues when playing videos from R2.
    
    If download=True is passed, the Content-Disposition will be set to attachment
    instead of inline, triggering a download in the browser.
    """
    logger.info(f"Streaming final video for: {filename}, download mode: {download}")
    
    try:
        # Check if video exists and has a final video
        result = await db.execute(select(Video).where(Video.filename == filename))
        video = result.scalar_one_or_none()
        if not video or not video.final_r2_key:
            logger.warning(f"Final video not found for: {filename}")
            raise HTTPException(status_code=404, detail="Final video not found")
            
        # Get the video from R2
        from app.services.r2 import s3, BUCKET
        import io
        import tempfile
        from fastapi.responses import StreamingResponse
        
        try:
            # Create a temporary file to store the video
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                temp_path = temp_file.name
                
            # Download the file from R2
            s3.download_file(BUCKET, video.final_r2_key, temp_path)
            
            # Define a generator to stream the file
            def iterfile():
                with open(temp_path, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk
                        
                # Clean up the temp file after streaming
                import os
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error removing temp file: {e}")
            
            # Return a streaming response
            response = StreamingResponse(iterfile(), media_type="video/mp4")
            
            # Set appropriate Content-Disposition based on download parameter
            output_filename = f"clipso_enhanced_{filename.replace('.webm', '.mp4')}"
            
            if download:
                # For download requests, use attachment disposition
                response.headers["Content-Disposition"] = f'attachment; filename="{output_filename}"'
                logger.info(f"Serving video for download: {output_filename}")
            else:
                # For viewing in the browser, use inline disposition
                response.headers["Content-Disposition"] = f'inline; filename="{output_filename}"'
                logger.info(f"Streaming video for viewing: {output_filename}")
                
            return response
            
        except Exception as e:
            logger.error(f"Error streaming video from R2: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error streaming video: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in video streaming endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/stream_by_share_id/{share_id}")
async def stream_by_share_id(
    share_id: str = Path(..., description="The share ID of the video"),
    download: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream the final video using share_id instead of filename.
    This provides cleaner, more user-friendly URLs for sharing.
    
    If download=True is passed, the Content-Disposition will be set to attachment
    instead of inline, triggering a download in the browser.
    """
    logger.info(f"Streaming video by share_id: {share_id}, download mode: {download}")
    
    try:
        # Look up the video by share_id
        result = await db.execute(select(Video).where(Video.share_id == share_id))
        video = result.scalar_one_or_none()
        
        if not video:
            logger.warning(f"Video not found for share_id: {share_id}")
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not video.final_r2_key:
            logger.warning(f"Final video not generated yet for share_id: {share_id}")
            raise HTTPException(status_code=404, detail="Final video not generated yet")
        
        # Get the video from R2
        from app.services.r2 import s3, BUCKET, file_exists
        if not file_exists(video.final_r2_key):
            logger.warning(f"Final video file not found in R2: {video.final_r2_key}")
            raise HTTPException(status_code=404, detail="Final video file not found")
            
        import tempfile
        from fastapi.responses import StreamingResponse
        
        try:
            # Create a temporary file to store the video
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                temp_path = temp_file.name
                
            # Download the file from R2
            s3.download_file(BUCKET, video.final_r2_key, temp_path)
            
            # Define a generator to stream the file
            def iterfile():
                with open(temp_path, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk
                        
                # Clean up the temp file after streaming
                import os
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error removing temp file: {e}")
            
            # Return a streaming response
            response = StreamingResponse(iterfile(), media_type="video/mp4")
            
            # Set appropriate Content-Disposition based on download parameter
            output_filename = f"clipso_enhanced_{video.share_id}.mp4"
            
            if download:
                # For download requests, use attachment disposition
                response.headers["Content-Disposition"] = f'attachment; filename="{output_filename}"'
                logger.info(f"Serving video for download by share_id: {share_id}")
            else:
                # For viewing in the browser, use inline disposition
                response.headers["Content-Disposition"] = f'inline; filename="{output_filename}"'
                logger.info(f"Streaming video for viewing by share_id: {share_id}")
                
            return response
            
        except Exception as e:
            logger.error(f"Error streaming video from R2: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error streaming video: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in video streaming by share_id: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/broll")
async def broll(prompt: str = Body(..., embed=True)):
    # Prompt is now directly extracted from request body
    
    # Log the request with all parameters for debugging
    logger.info(f"B-roll fetch requested for prompt: {prompt}")
    
    # Validate the prompt
    if not prompt or len(str(prompt).strip()) < 3:
        logger.error(f"Invalid B-roll prompt: {prompt}")
        raise HTTPException(status_code=400, detail="Invalid prompt - must be at least 3 characters")
    
    # Check if this exact prompt is already being processed
    import hashlib
    prompt_hash = hashlib.md5(str(prompt).encode()).hexdigest()[:10]
    
    if prompt_hash in broll_generations_in_progress and broll_generations_in_progress[prompt_hash]:
        logger.info(f"B-roll generation already in progress for prompt hash: {prompt_hash}, skipping duplicate request")
        return {"message": "B-roll generation already in progress", "status": "processing", "prompt": prompt}
    
    try:
        # Mark this prompt as being processed
        broll_generations_in_progress[prompt_hash] = True
        
        # Call the B-roll generation service (which already has caching built in)
        url = await fetch_b_roll(str(prompt))
        logger.info(f"B-roll successfully generated for prompt: {prompt}, URL: {url}")
        
        # Return the B-roll URL
        return {"broll_url": url, "prompt": prompt, "success": True}
    except Exception as e:
        # Log detailed error with stack trace
        logger.error(f"B-roll fetch failed: {e}", exc_info=True)
        # Return a user-friendly error
        raise HTTPException(status_code=500, detail=f"B-roll generation failed: {str(e)}")
    finally:
        # Mark processing as complete to allow future requests
        broll_generations_in_progress[prompt_hash] = False
