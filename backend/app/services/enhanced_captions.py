"""
Enhanced caption system for Clipso
Integrates advanced text rendering with the existing system
"""

import os
import tempfile
import logging
import json
from typing import List, Dict, Any, Optional

# Import database-related modules
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import our app modules
from .r2 import upload_fileobj, get_file_url, file_exists
from .segment_parser import parse as parse_segments
from .text_drawer import create_styled_caption
from app.models import Video, Transcript
from app.db import AsyncSessionLocal
from app.core.config import settings

# We'll import these dynamically in functions to avoid issues
# import boto3
# import numpy as np
# from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

# Set up logging
logger = logging.getLogger(__name__)

async def generate_enhanced_final_video(filename: str, db: AsyncSession = None) -> str:
    """
    Generate the final video with enhanced stylish captions
    Returns the URL to the generated video in R2 storage
    
    Args:
        filename: The filename of the video to process
        db: Optional database session
        
    Returns:
        URL to the final video in R2 storage
    """
    # Import moviepy here to avoid import issues
    from moviepy.editor import VideoFileClip, CompositeVideoClip
    
    logger.info(f"Starting enhanced final video generation for: {filename}")
    
    # Use the provided db session or create a new one
    if db is None:
        # Create a new session within a context manager
        async with AsyncSessionLocal() as db_session:
            try:
                # Process the video with the new session
                return await _generate_enhanced_final_video(db_session, filename)
            except Exception as e:
                logger.error(f"Error generating enhanced final video: {e}", exc_info=True)
                # Re-raise after logging
                raise Exception(f"Failed to generate enhanced final video: {str(e)}")
    else:
        # Use the provided session
        try:
            # Process with the provided session
            return await _generate_enhanced_final_video(db, filename)
        except Exception as e:
            logger.error(f"Error generating enhanced final video: {e}", exc_info=True)
            # Re-raise after logging
            raise Exception(f"Failed to generate enhanced final video: {str(e)}")

async def _generate_enhanced_final_video(db: AsyncSession, filename: str) -> str:
    """
    Internal implementation of enhanced final video generation
    """
    # Import moviepy here to avoid circular imports
    from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
    import numpy as np
    
    # Get video record with an explicit select
    logger.info(f"Fetching video record for: {filename}")
    result = await db.execute(select(Video).where(Video.filename == filename))
    video = result.scalar_one_or_none()
    
    if not video:
        logger.error(f"Video record not found for final video generation: {filename}")
        raise Exception(f"Video record not found for final video generation: {filename}")
    
    logger.info(f"Found video record with ID: {video.id}, status: {video.status}")
    
    # Get transcript explicitly with a separate query to avoid lazy loading issues
    logger.info(f"Fetching transcript for video ID: {video.id}")
    transcript_result = await db.execute(
        select(Transcript).where(Transcript.video_id == video.id)
    )
    transcript = transcript_result.scalar_one_or_none()
    
    if not transcript:
        logger.error(f"Transcript not found for video ID: {video.id}")
        raise Exception(f"Transcript not found for video: {filename}")
        
    logger.info(f"Found transcript with ID: {transcript.id}")
    
    # Update status
    video.status = "processing: generating enhanced final video"
    await db.commit()
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Import boto3 here to avoid import issues
        import boto3
        
        # Download video from R2
        r2_client = boto3.client(
            service_name='s3',
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        )
        
        # Download the video file
        temp_video_path = os.path.join(temp_dir, filename)
        logger.info(f"Downloading video from R2: {video.r2_key} to {temp_video_path}")
        r2_client.download_file(settings.R2_BUCKET, video.r2_key, temp_video_path)
        
        # Convert WebM to MP4 first to avoid issues with MoviePy not being able to read WebM duration
        import subprocess
        temp_mp4_path = os.path.join(temp_dir, f"{os.path.splitext(filename)[0]}.mp4")
        logger.info(f"Converting WebM to MP4: {temp_video_path} -> {temp_mp4_path}")
        
        try:
            # Run FFmpeg to convert the WebM to MP4
            ffmpeg_cmd = [
                "ffmpeg", "-i", temp_video_path, 
                "-c:v", "libx264", "-c:a", "aac", 
                "-strict", "experimental", 
                "-b:a", "192k", "-pix_fmt", "yuv420p",
                temp_mp4_path
            ]
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            logger.info(f"Successfully converted WebM to MP4")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion error: {e.stderr.decode() if e.stderr else str(e)}")
            raise Exception(f"Failed to convert video format: {str(e)}")
        
        # Load the converted MP4 video
        video_clip = VideoFileClip(temp_mp4_path)
        logger.info(f"Loaded video: {temp_mp4_path}, duration: {video_clip.duration:.2f}s")
        
        # Get transcript data directly (using our explicitly loaded transcript)
        # Handle if transcript.text is already a dict or if it's a JSON string
        try:
            if isinstance(transcript.text, dict):
                transcript_data = transcript.text
                logger.info("Transcript.text is already a dictionary, using directly")
            else:
                transcript_data = json.loads(transcript.text)
                logger.info("Parsed transcript.text from JSON string")
        except Exception as e:
            logger.error(f"Error parsing transcript data: {e}")
            # Fallback - try to convert to string first if it's not already
            try:
                if not isinstance(transcript.text, str):
                    transcript_text = json.dumps(transcript.text)
                    transcript_data = json.loads(transcript_text)
                    logger.info("Used fallback transcript parsing method")
                else:
                    raise ValueError("Unable to parse transcript text in any format")
            except Exception as inner_e:
                logger.error(f"Fallback transcript parsing failed: {inner_e}")
                raise ValueError(f"Could not parse transcript data: {e}, {inner_e}")
        
        segments = transcript_data.get('segments', [])
        logger.info(f"Loaded transcript with {len(segments)} segments")
        
        # Prepare for clips
        clips = [video_clip]  # Start with base video
        
        # Parse segments to ensure they fit on screen
        max_text_width = int(video_clip.w * 0.9)  # 90% of video width
        
        # Define a fit function based on approximate character width
        def fit_function(text):
            # Rough estimate for character width based on font size
            font_size = 80
            char_width = font_size * 0.5  # Approximate character width
            text_width = len(text) * char_width
            return text_width <= max_text_width
        
        # Generate captions with proper formatting
        parsed_captions = parse_segments(segments, fit_function)
        logger.info(f"Created {len(parsed_captions)} caption segments")
        
        # Create caption clips
        for caption in parsed_captions:
            # Clean the text
            text = caption["text"].strip().upper()
            
            # Create stylish caption with Bangers font
            font_size = 80  # Bangers is a display font that looks good at this size
            caption_clip = create_styled_caption(
                text=text,
                video_width=video_clip.w,
                fontsize=font_size,
                color="white",
                stroke_color="black",
                stroke_width=3,  # Slightly heavier stroke for Bangers
                blur_shadow=True,
                blur_radius=10  # Slightly increased shadow for better visibility
            )
            
            # Position at bottom with 20% margin as requested
            bottom_margin = video_clip.h * 0.20  # 20% margin from bottom (increased from 15%)
            position = ("center", video_clip.h - bottom_margin)
            
            # Set timing and position
            caption_clip = caption_clip.set_position(position)
            caption_clip = caption_clip.set_start(caption["start"])
            caption_clip = caption_clip.set_end(caption["end"])
            
            # Add to clip list
            clips.append(caption_clip)
        
        # Generate B-roll clips if available
        await _add_broll_clips(clips, segments, video_clip, temp_dir)
        
        # Create final composite
        logger.info(f"Creating composite with {len(clips)} elements")
        final_clip = CompositeVideoClip(clips)
        
        # Write to output file
        output_filename = f"final_{filename.replace('.webm', '.mp4')}"
        temp_output_path = os.path.join(temp_dir, output_filename)
        logger.info(f"Writing final video to: {temp_output_path}")
        
        final_clip.write_videofile(
            temp_output_path,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            threads=2,
            fps=24
        )
        
        # Upload to R2
        logger.info(f"Uploading final video to R2")
        final_key = f"final/{output_filename}"
        
        with open(temp_output_path, 'rb') as final_file:
            upload_fileobj(final_file, final_key, content_type="video/mp4")
        
        # Update video record
        video.final_r2_key = final_key
        video.status = "completed"
        await db.commit()
        
        # Get URL
        final_url = get_file_url(final_key)
        logger.info(f"Enhanced final video generated and uploaded: {final_url}")
        
        return final_url

async def _add_broll_clips(clips: List, segments: List[Dict[str, Any]], video_clip, temp_dir: str) -> List:
    """
    Add B-roll clips to the video based on transcript content
    
    Args:
        clips: List of existing video clips
        segments: Transcript segments with timestamps
        video_clip: Main video clip
        temp_dir: Temporary directory for processing
        
    Returns:
        Updated list of clips with B-roll added
    """
    # Import here to avoid circular imports
    from moviepy.editor import ImageClip
    from PIL import Image
    import numpy as np
    from .caption import fetch_b_roll
    
    logger.info(f"Starting B-roll generation with {len(segments)} segments")
    
    # Instead of selecting specific segments, let's spread B-rolls throughout the video
    # at regular intervals (every 4-5 seconds)
    
    # Get total video duration
    video_duration = video_clip.duration
    logger.info(f"Video duration: {video_duration} seconds")
    
    # Calculate number of B-rolls to add (one every 5 seconds)
    # Start after the first 2 seconds as requested
    interval = 5.0  # seconds between B-rolls (fixed at 5 seconds as requested)
    first_broll_time = 2.0  # Don't show B-roll in first 2 seconds
    remaining_duration = video_duration - first_broll_time
    
    # Ensure we have the right number of B-rolls - for a 60s video, should be 12 B-rolls (one every 5s)
    min_b_rolls = max(1, int(remaining_duration / interval))
    max_b_rolls = min(20, min_b_rolls)  # Cap at 20 B-rolls for very long videos
    
    logger.info(f"Planning to add {max_b_rolls} B-rolls at {interval}s intervals, starting after {first_broll_time}s")
    
    # Create time slots for B-rolls at fixed intervals
    broll_times = []
    for i in range(max_b_rolls):
        broll_time = first_broll_time + (i * interval)
        if broll_time < video_duration - 3:  # Ensure B-roll doesn't start in last 3 seconds
            broll_times.append(broll_time)
    
    logger.info(f"Created {len(broll_times)} B-roll time slots at fixed intervals")
    
    # Find the best segment for each desired B-roll time
    b_roll_segments = []
    
    for target_time in broll_times:
        # Find closest segment to this target time
        closest_segment = None
        min_distance = float('inf')
        
        for segment in segments:
            segment_start = segment.get('start', 0)
            segment_end = segment.get('end', 0)
            
            # Calculate distance to target time (prioritize segments that contain the target time)
            if segment_start <= target_time <= segment_end:
                # Target time is within this segment - perfect match
                distance = 0
            else:
                # Calculate distance to segment midpoint
                segment_mid = (segment_start + segment_end) / 2
                distance = abs(segment_mid - target_time)
            
            # Update closest if this is better
            if distance < min_distance:
                min_distance = distance
                closest_segment = segment
        
        if closest_segment:
            # Create an enhanced segment with additional context
            # Look for nearby segments to create more meaningful context for B-roll
            enhanced_text = closest_segment.get('text', '').strip()
            
            # Try to build a complete sentence for better B-roll context
            # Look at segments within 2 seconds before and after for context
            context_segments = []
            segment_start = closest_segment.get('start', 0)
            segment_end = closest_segment.get('end', 0)
            
            for segment in segments:
                seg_start = segment.get('start', 0)
                seg_end = segment.get('end', 0)
                
                # Check if this segment overlaps or is adjacent to our target segment
                if (seg_end >= segment_start - 2 and seg_start <= segment_end + 2):
                    context_segments.append(segment)
            
            # Sort context segments by start time
            context_segments.sort(key=lambda x: x.get('start', 0))
            
            # Combine text from context segments (up to ~10 words for a concise B-roll prompt)
            if context_segments:
                combined_text = " ".join([s.get('text', '').strip() for s in context_segments])
                # Extract approximately the first 10-15 words for a focused prompt
                words = combined_text.split()
                if len(words) > 15:
                    enhanced_text = " ".join(words[:15])
                else:
                    enhanced_text = combined_text
            
            # Clone the segment and update with enhanced text and target time
            enhanced_segment = closest_segment.copy()
            enhanced_segment["text"] = enhanced_text
            enhanced_segment["broll_time"] = target_time  # Store the target time
            
            # Explicitly set the start time to the target time
            enhanced_segment['start'] = target_time
            
            # Add to our B-roll segments list
            b_roll_segments.append(enhanced_segment)
    
    logger.info(f"Created {len(b_roll_segments)} B-roll segments at fixed time intervals")
    
    # Process each B-roll segment - no hard limit, but we'll still have a maximum
    max_added_brolls = 0
    for i, segment in enumerate(b_roll_segments):
        # Set a higher limit, but still have one to prevent issues
        if max_added_brolls >= 20:
            logger.info("Reached maximum B-roll limit (20), skipping remaining segments")
            break
            
        try:
            # Generate a clean prompt for B-roll generation
            segment_text = segment.get('text', '').strip()
            if not segment_text:
                continue
                
            # Create a descriptive prompt for good B-roll generation
            prompt = f"High quality visual scene representing: {segment_text[:100]}"
            logger.info(f"Requesting B-roll for segment {i+1}/{len(b_roll_segments)}: {prompt}")
            
            # Request B-roll from DALL-E 3
            broll_url = await fetch_b_roll(prompt)
            if not broll_url:
                logger.warning(f"B-roll generation failed for segment {i+1}, skipping")
                continue
            
            # Download the B-roll image
            import requests
            image_path = os.path.join(temp_dir, f"broll_{i}.png")
            
            try:
                response = requests.get(broll_url, stream=True, timeout=10)  # Add timeout
                if response.status_code == 200:
                    with open(image_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):  # Use iter_content for safety
                            if chunk:
                                f.write(chunk)
                else:
                    logger.warning(f"Failed to download B-roll image: HTTP {response.status_code}")
                    continue
            except Exception as download_err:
                logger.error(f"Error downloading B-roll image: {download_err}")
                continue
            
            # Load and resize image for B-roll
            broll_img = Image.open(image_path)
            
            # Calculate dimensions - make it 70% of video width
            new_width = int(video_clip.w * 0.7)
            ratio = broll_img.width / broll_img.height
            new_height = int(new_width / ratio)
            
            # Resize image
            broll_img = broll_img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to numpy array for MoviePy
            img_array = np.array(broll_img)
            
            # Create clip
            broll_clip = ImageClip(img_array)
            
            # Position at top center of frame
            position = ((video_clip.w - new_width) / 2, video_clip.h * 0.20)
            
            # Display B-roll for a fixed duration of 3 seconds regardless of segment length
            # This ensures consistent B-roll display even for short segments
            segment_start = segment.get('start', 0)
            segment_end = segment.get('end', 0)
            segment_duration = segment_end - segment_start
            
            # Always show B-roll for 3 seconds, but ensure it doesn't start before first_broll_time
            # If segment is shorter than 3 seconds, B-roll will still show for 3 seconds
            start_time = max(segment_start, first_broll_time)  # Ensure B-roll never starts before first_broll_time
            duration = 3.0  # Fixed 3 second duration for consistency
            end_time = start_time + duration
            
            # Add fade effects
            fade_duration = 0.5
            broll_clip = broll_clip.set_position(position).set_start(start_time).set_end(end_time)
            
            # Add fades if there's enough duration
            if duration > 2 * fade_duration:
                broll_clip = broll_clip.fadein(fade_duration).fadeout(fade_duration)
            
            # Add to clip list
            clips.append(broll_clip)
            max_added_brolls += 1
            logger.info(f"Added B-roll clip {max_added_brolls}/{max_b_rolls} at time {start_time:.2f}s")
        
        except Exception as e:
            logger.error(f"Error adding B-roll: {e}", exc_info=True)
            continue
            
    return clips