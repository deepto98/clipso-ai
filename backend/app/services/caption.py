import logging
import uuid
import requests
import tempfile
import os
import boto3
import hashlib
from io import BytesIO

from app.services.aws_ai_services import aws_ai_services

# Import video processing
# Will use FFmpeg directly instead of MoviePy

# ORM imports
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models import Transcript, Video
from app.core.config import settings
from app.services.r2 import upload_fileobj, get_file_url, s3

# Set bucket name from settings
BUCKET = settings.R2_BUCKET

# Set up logging
logger = logging.getLogger(__name__)

# AWS AI services are initialized in aws_ai_services module


async def generate_transcript(video_filename: str,
                              db: AsyncSession = None) -> str:
    import os

    try:
        # First check the database for records with this filename
        result = await db.execute(
            select(Video).where(Video.filename == video_filename))
        video = result.scalar_one_or_none()
        if not video:
            raise Exception(f"Video record not found for: {video_filename}")

        # Import what we need from r2.py
        from app.services.r2 import get_file_url, s3, file_exists, BUCKET

        if video.r2_key:
            # Use the stored R2 key directly
            logger.info(f"Using stored R2 key from database: {video.r2_key}")
            key = video.r2_key
        else:
            # Fall back to filename for older records
            logger.info(
                f"No R2 key in database, using filename: {video_filename}")
            import os
            name, ext = os.path.splitext(video_filename)

            # Try to find the file in R2

            if file_exists(video_filename):
                logger.info(
                    f"Found exact filename match in R2: {video_filename}")
                key = video_filename
            else:
                # Query objects with similar prefix
                try:
                    response = s3.list_objects_v2(Bucket=BUCKET,
                                                  Prefix=f"{name}-")

                    possible_keys = []
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            possible_keys.append(obj['Key'])

                    if possible_keys:
                        # Use the first match
                        key = possible_keys[0]
                        logger.info(f"Found key by prefix search: {key}")

                        # Update the record for future use
                        video.r2_key = key
                        await db.commit()
                    else:
                        raise Exception(
                            f"No matching files found in R2 for {video_filename}"
                        )
                except Exception as e:
                    logger.error(f"Error listing objects in R2: {e}")
                    raise Exception(f"Failed to find video in R2: {str(e)}")

        # Get the URL using the key
        video_url = get_file_url(key)
        logger.info(
            f"Requesting transcript for {video_url}")

        # Download video using boto3 directly instead of HTTP request

        try:
            # Use the S3 client to download the file directly
            logger.info(
                f"Downloading file from R2 using boto3, bucket: {BUCKET}, key: {key}"
            )
            video_bytes = BytesIO()
            s3.download_fileobj(BUCKET, key, video_bytes)
            # Reset file pointer to beginning
            video_bytes.seek(0)

            # Log file size for debugging
            file_size = video_bytes.getbuffer().nbytes
            logger.info(f"Downloaded video file size: {file_size} bytes")

            if file_size == 0:
                logger.error("Downloaded file is empty")
                raise Exception("Downloaded file is empty")
        except Exception as e:
            logger.error(f"Failed to download video from R2: {str(e)}")
            raise Exception(f"Failed to download video from R2: {str(e)}")

        # If this is a WebM file, we need to convert it to a supported format
        if video_filename.lower().endswith('.webm'):
            logger.info(
                "Converting WebM to MP3 processing using FFmpeg")

            # Save WebM to temp file
            with tempfile.NamedTemporaryFile(suffix='.webm',
                                             delete=False) as temp_webm:
                # Get the contents from our BytesIO buffer
                video_bytes.seek(0)
                webm_content = video_bytes.read()
                temp_webm.write(webm_content)
                temp_webm_path = temp_webm.name

            # Convert to MP3 using FFmpeg
            try:
                # Create temp file for MP3
                temp_mp3_path = temp_webm_path.replace('.webm', '.mp3')

                # Use FFmpeg to convert WebM to MP3
                import subprocess
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i',
                    temp_webm_path,
                    '-vn',  # Disable video recording
                    '-acodec',
                    'libmp3lame',
                    '-q:a',
                    '4',  # Audio quality (lower is better, 0-9)
                    '-y',  # Overwrite output files without asking
                    temp_mp3_path
                ]
                logger.info(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
                result = subprocess.run(ffmpeg_cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

                if result.returncode != 0:
                    logger.error(
                        f"FFmpeg error: {result.stderr.decode('utf-8')}")
                    raise Exception(
                        f"FFmpeg conversion failed: {result.stderr.decode('utf-8')}"
                    )

                logger.info(
                    f"FFmpeg conversion successful, MP3 file size: {os.path.getsize(temp_mp3_path)} bytes"
                )

                # Call AWS Transcribe service
                logger.info("Calling AWS Transcribe with converted MP3")
                transcript_resp = await aws_ai_services.transcribe_audio(temp_mp3_path)

                # Cleanup temp files
                if os.path.exists(temp_webm_path):
                    os.remove(temp_webm_path)
                if os.path.exists(temp_mp3_path):
                    os.remove(temp_mp3_path)
            except Exception as e:
                logger.error(f"Error during WebM conversion: {e}",
                             exc_info=True)
                # Clean up any temp files if they exist
                for path in [temp_webm_path, temp_mp3_path]:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except:
                        pass
                raise
        elif video_filename.lower().endswith('.mp4'):
            logger.info("Processing MP4 file")
            
            # Save MP4 to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_mp4:
                # Get the contents from our BytesIO buffer
                video_bytes.seek(0)
                mp4_content = video_bytes.read()
                temp_mp4.write(mp4_content)
                temp_mp4_path = temp_mp4.name
            
            try:
                # Extract audio from MP4 using FFmpeg
                temp_mp3_path = temp_mp4_path.replace('.mp4', '.mp3')
                
                import subprocess
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i',
                    temp_mp4_path,
                    '-vn',  # Disable video recording
                    '-acodec',
                    'libmp3lame',
                    '-q:a',
                    '4',  # Audio quality (lower is better, 0-9)
                    '-y',  # Overwrite output files without asking
                    temp_mp3_path
                ]
                logger.info(f"Running FFmpeg command for MP4: {' '.join(ffmpeg_cmd)}")
                result = subprocess.run(ffmpeg_cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr.decode('utf-8')}")
                    raise Exception(f"FFmpeg conversion failed: {result.stderr.decode('utf-8')}")
                
                logger.info(f"FFmpeg conversion successful, MP3 file size: {os.path.getsize(temp_mp3_path)} bytes")
                
                # Call AWS Transcribe service
                logger.info("Calling AWS Transcribe with extracted MP3 from MP4")
                transcript_resp = await aws_ai_services.transcribe_audio(temp_mp3_path)
                
                # Cleanup temp files
                if os.path.exists(temp_mp4_path):
                    os.remove(temp_mp4_path)
                if os.path.exists(temp_mp3_path):
                    os.remove(temp_mp3_path)
            except Exception as e:
                logger.error(f"Error during MP4 processing: {e}", exc_info=True)
                # Clean up any temp files if they exist
                for path in [temp_mp4_path, temp_mp3_path]:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except:
                        pass
                raise
        else:
            logger.info(f"Using direct API call for format: {os.path.splitext(video_filename)[1]}")
            try:
                # Create a temp file for the audio
                extension = os.path.splitext(video_filename)[1]
                with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
                    video_bytes.seek(0)
                    temp_file.write(video_bytes.read())
                    temp_path = temp_file.name
                
                # Call AWS Transcribe service
                transcript_resp = await aws_ai_services.transcribe_audio(temp_path)
                
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                logger.error(f"Error during API call for {extension} file: {e}", exc_info=True)
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                raise

        logger.info(f"Transcript received from AWS Transcribe for {video_filename}")

        # Convert the TranscriptionVerbose object to a dictionary for JSON serialization
        logger.info(
            "Converting transcript response to JSON serializable format")

        # Custom JSON encoder to handle non-serializable objects
        def custom_json_encoder(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, 'words') and hasattr(obj, 'text'):
                # Handle specific properties expected in TranscriptionVerbose
                data = {}
                for attr in ['duration', 'language', 'text', 'task', 'words']:
                    if hasattr(obj, attr):
                        value = getattr(obj, attr)
                        # Handle nested non-serializable objects
                        if hasattr(value, '__iter__') and not isinstance(
                                value, (str, dict)):
                            data[attr] = [
                                custom_json_encoder(item) if hasattr(
                                    item, '__dict__') else item
                                for item in value
                            ]
                        else:
                            data[attr] = value
                return data
            return str(obj)

        # Try different approaches to serialize the response
        try:
            import json
            # First attempt direct serialization
            transcript_data = json.loads(
                json.dumps(transcript_resp, default=custom_json_encoder))
            logger.info("Successfully serialized transcript response")
        except Exception as e:
            # If that fails, extract key data manually
            logger.warning(
                f"JSON serialization failed: {e}, extracting key data manually"
            )

            # Extract the text at minimum
            text = getattr(transcript_resp, 'text', str(transcript_resp))

            # Create a basic dictionary with available data
            transcript_data = {"text": text}

            # Try to add other fields if available
            for field in ['duration', 'language', 'task']:
                if hasattr(transcript_resp, field):
                    transcript_data[field] = getattr(transcript_resp, field)

            logger.info(
                f"Created manual transcript data with keys: {list(transcript_data.keys())}"
            )

        # Store transcript in Postgres
        if db is None:
            async with AsyncSessionLocal() as db:
                await _save_transcript(db, video_filename, transcript_data)
        else:
            await _save_transcript(db, video_filename, transcript_data)

        return transcript_resp
    except Exception as e:
        logger.error(f"Error generating transcript: {e}", exc_info=True)
        # Update the video record to show the error
        if db is None:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Video).where(Video.filename == video_filename))
                video = result.scalar_one_or_none()
                if video:
                    video.status = f"error: {str(e)}"
                    await db.commit()
        else:
            result = await db.execute(
                select(Video).where(Video.filename == video_filename))
            video = result.scalar_one_or_none()
            if video:
                video.status = f"error: {str(e)}"
                await db.commit()

        raise


async def _save_transcript(db: AsyncSession, video_filename: str,
                           transcript_resp):
    # Get video record
    result = await db.execute(
        select(Video).where(Video.filename == video_filename))
    video = result.scalar_one_or_none()
    if not video:
        raise Exception("Video record not found for transcript saving.")
    transcript = Transcript(video_id=video.id, text=transcript_resp)
    db.add(transcript)
    await db.commit()
    logger.info(f"Transcript saved to DB for video {video_filename}")


async def transcript_exists(filename: str, db: AsyncSession = None) -> bool:
    if db is None:
        async with AsyncSessionLocal() as db:
            return await _transcript_exists(db, filename)
    return await _transcript_exists(db, filename)


async def _transcript_exists(db: AsyncSession, filename: str) -> bool:
    result = await db.execute(select(Video).where(Video.filename == filename))
    video = result.scalar_one_or_none()
    if not video:
        return False
    # Use first() instead of scalar_one_or_none() to handle multiple transcripts
    result = await db.execute(
        select(Transcript).where(Transcript.video_id == video.id))
    transcript = result.first()
    return transcript is not None


async def load_transcript(filename: str, db: AsyncSession = None):
    if db is None:
        async with AsyncSessionLocal() as db:
            return await _load_transcript(db, filename)
    return await _load_transcript(db, filename)


async def _load_transcript(db: AsyncSession, filename: str):
    try:
        # Log that we're starting transcript load
        logger.info(f"Loading transcript for filename: {filename}")

        # Find the video
        result = await db.execute(
            select(Video).where(Video.filename == filename))
        video = result.scalar_one_or_none()
        if not video:
            logger.error(f"Video not found for transcript fetch: {filename}")
            raise Exception("Video not found for transcript fetch.")

        logger.info(f"Found video with ID {video.id} for filename {filename}")

        # Query for transcripts, get most recent first
        result = await db.execute(
            select(Transcript).where(Transcript.video_id == video.id).order_by(
                Transcript.id.desc()))

        # Get first result - not using first() as the return format varies
        all_transcripts = result.all()

        if not all_transcripts or len(all_transcripts) == 0:
            logger.error(f"No transcript found for video ID {video.id}")
            raise Exception("Transcript not found.")

        # Get the first transcript (most recent one)
        transcript_record = all_transcripts[0]

        # Handle different return types (Transcript object or tuple with Transcript)
        if hasattr(transcript_record,
                   "__len__") and len(transcript_record) > 0:
            transcript = transcript_record[0]
        else:
            transcript = transcript_record

        logger.info(
            f"Retrieved transcript for video {filename}, transcript ID: {transcript.id}"
        )

        return transcript.text

    except Exception as e:
        logger.error(f"Error loading transcript: {e}")
        raise


# --- B-Roll Fetching Logic ---
async def fetch_b_roll(prompt: str) -> str:
    """
    Fetch a B-roll image for the given prompt using AWS Bedrock (Titan Image Generator).
    The result is uploaded to R2 and the URL is returned.
    """
    # Import what we need from r2.py
    from app.services.r2 import get_file_url, upload_fileobj, BUCKET, file_exists, public_access_allowed, CLOUDFLARE_PUBLIC_URL

    logger.info(f"Fetching B-roll for prompt: {prompt}")

    # Generate a deterministic key based on the prompt to enable caching
    # This avoids regenerating the same image for the same prompt
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
    key = f"broll/{prompt_hash}.png"

    # Check if we already have an image for this prompt in R2
    if file_exists(key):
        logger.info(f"Using cached B-roll for prompt: {prompt}")
        # Get the URL based on public access settings
        return get_file_url(key)

    try:
        # Generate image with AWS Bedrock Titan Image Generator
        logger.info(f"Requesting AWS Bedrock image generation for prompt: {prompt}")
        
        # Call AWS Bedrock service directly - it handles upload to R2 internally
        r2_url = await aws_ai_services.generate_image(prompt, style="photographic")
        
        logger.info(f"B-roll generated and uploaded to R2: {r2_url}")
        return r2_url

    except Exception as e:
        logger.error(f"AWS B-roll generation failed: {str(e)}", exc_info=True)

        # Return a fallback image if available, otherwise re-raise the exception
        fallback_key = "broll/fallback.png"
        if file_exists(fallback_key):
            logger.info(f"Using fallback B-roll image due to AWS error")
            return get_file_url(fallback_key)

        # If no fallback, raise the exception
        raise


# --- Final Video Rendering Logic ---
async def generate_final_video(filename: str, db: AsyncSession = None) -> str:
    """
    Generate the final video with captions and B-roll images.
    Returns the URL to the generated video in R2 storage.
    """
    # Import and configure moviepy
    from moviepy.editor import VideoFileClip, TextClip, ImageClip, CompositeVideoClip
    from moviepy.video.tools.subtitles import SubtitlesClip
    import tempfile
    import os

    logger.info(f"Starting final video generation for: {filename}")

    try:
        # Get video record
        if db is None:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Video).where(Video.filename == filename))
                video = result.scalar_one_or_none()
        else:
            result = await db.execute(
                select(Video).where(Video.filename == filename))
            video = result.scalar_one_or_none()

        if not video:
            raise Exception(
                f"Video record not found for final video generation: {filename}"
            )

        # Make sure we have transcript
        transcript_exists_check = await transcript_exists(filename, db)
        if not transcript_exists_check:
            raise Exception(f"Transcript not found for video: {filename}")

        # Get transcript data
        transcript_data = await load_transcript(filename, db)
        if not transcript_data:
            raise Exception(f"Failed to load transcript for video: {filename}")

        # Get the video URL
        from app.services.r2 import get_file_url, file_exists

        if not video.r2_key or not file_exists(video.r2_key):
            raise Exception(
                f"Original video file not found in R2 storage: {video.r2_key}")

        # Parse the transcript for subtitle generation
        segments = []
        text_for_broll = ""

        try:
            if isinstance(transcript_data, dict):
                if 'text' in transcript_data:
                    text_for_broll = transcript_data['text']

                # Check for segments, which contain timing info
                if 'segments' in transcript_data:
                    for segment in transcript_data['segments']:
                        if 'start' in segment and 'end' in segment and 'text' in segment:
                            segments.append((segment['start'], segment['end'],
                                             segment['text']))
                # If no segments, use simple text with estimated timing
                elif 'text' in transcript_data:
                    # Simple approach: split text by sentences, estimate 1 sec per word
                    import re
                    sentences = re.split(r'[.!?]', transcript_data['text'])
                    start_time = 0
                    for sentence in sentences:
                        if sentence.strip():
                            words = len(sentence.split())
                            duration = max(1, words * 0.4)  # Estimate
                            segments.append((start_time, start_time + duration,
                                             sentence.strip()))
                            start_time += duration
            elif isinstance(transcript_data, str):
                text_for_broll = transcript_data
                # Simple approach for string data
                words = transcript_data.split()
                total_words = len(words)
                words_per_segment = min(10, total_words)
                start_time = 0

                for i in range(0, total_words, words_per_segment):
                    segment_words = words[i:min(i +
                                                words_per_segment, total_words
                                                )]
                    segment_text = " ".join(segment_words)
                    duration = len(segment_words) * 0.4
                    segments.append(
                        (start_time, start_time + duration, segment_text))
                    start_time += duration
        except Exception as e:
            logger.error(f"Error parsing transcript data: {e}", exc_info=True)
            # Fall back to simple approach if parsing fails
            if isinstance(transcript_data, dict) and 'text' in transcript_data:
                text_for_broll = transcript_data['text']
            elif isinstance(transcript_data, str):
                text_for_broll = transcript_data

        # Generate multiple B-roll images based on transcript segments
        broll_images = []

        if segments and len(segments) > 0:
            logger.info(
                f"Generating multiple B-roll images from {len(segments)} transcript segments"
            )

            # Determine how many B-roll images to use based on video length
            # Target approximately one image every 8-10 seconds with shorter display times
            estimated_duration = segments[-1][1]  # End time of last segment
            target_image_count = max(1, min(6, int(
                estimated_duration / 9)))  # Fewer B-rolls for a snappier look

            logger.info(
                f"Estimated video duration: {estimated_duration:.2f}s, targeting {target_image_count} B-roll images"
            )

            # Select evenly spaced segments to visualize
            if target_image_count >= len(segments):
                # If we have fewer segments than target, use all segments
                segments_to_visualize = segments
            else:
                # Otherwise, pick evenly distributed segments
                step = len(segments) / target_image_count
                indices = [int(i * step) for i in range(target_image_count)]
                segments_to_visualize = [segments[i] for i in indices]

                      # Use AWS AI to analyze the transcript and generate B-roll suggestions
            all_text = " ".join([text for _, _, text in segments])
            try:
                # For each segment we want to visualize, generate a B-roll image
                for i, (start_time, end_time,
                        segment_text) in enumerate(segments_to_visualize):
                    try:
                        logger.info(
                            f"Generating B-roll for segment {i+1}/{len(segments_to_visualize)}: {segment_text[:50]}..."
                        )

                        # Create a focused prompt for this segment
                        broll_prompt = f"High quality visual scene representing: {segment_text}"

                        # Fetch B-roll with existing method
                        broll_url = await fetch_b_roll(broll_prompt)

                        if broll_url:
                            # Store the B-roll image URL along with timing information
                            # Add 2 second delay for first B-roll, ensure B-rolls are 1 second max
                            start_adjusted = max(2.0, start_time) if i == 0 else start_time
                            # Limit B-roll display to 1 second maximum for a snappy look
                            end_adjusted = min(start_adjusted + 1.0, estimated_duration)
                            
                            broll_images.append({
                                "url": broll_url,
                                "start_time": start_adjusted,
                                "end_time": end_adjusted,
                                "text": segment_text
                            })
                            logger.info(
                                f"B-roll image {i+1} fetched successfully for timestamp {start_time:.2f}s"
                            )
                    except Exception as segment_err:
                        logger.error(
                            f"Failed to generate B-roll for segment {i+1}: {segment_err}"
                        )
                        continue
            except Exception as e:
                logger.error(f"Failed to generate multiple B-roll images: {e}",
                             exc_info=True)

            logger.info(
                f"Generated {len(broll_images)} B-roll images for video")
        else:
            # Fallback to single image if no segments
            logger.warning(
                "No transcript segments available, falling back to single B-roll image"
            )

            if text_for_broll:
                # Extract the first sentence for B-roll
                first_sentence = text_for_broll.split('.')[0]
                broll_prompt = f"High quality visual scene representing: {first_sentence}"

                try:
                    # Fetch B-roll with existing method
                    broll_url = await fetch_b_roll(broll_prompt)
                    logger.info(
                        f"Single B-roll fetched for final video: {broll_url}")

                    if broll_url:
                        # Delay first B-roll by 2 seconds and display for 1 second only
                        broll_images.append({
                            "url": broll_url,
                            "start_time": 2.0,  # Delay by 2 seconds
                            "end_time": 3.0,    # Show for only 1 second 
                            "text": first_sentence
                        })
                except Exception as e:
                    logger.error(f"Failed to fetch fallback B-roll image: {e}",
                                 exc_info=True)

        # Generate final video by downloading original, adding captions and B-roll
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download original video
            logger.info(f"Downloading original video from R2")
            from app.services.r2 import s3, BUCKET
            import subprocess

            temp_video_path = os.path.join(temp_dir, f"original_{filename}")
            with open(temp_video_path, 'wb') as video_file:
                s3.download_fileobj(BUCKET, video.r2_key, video_file)

            logger.info(f"Original video downloaded to: {temp_video_path}")

            # Convert WebM to MP4 using FFmpeg for better compatibility with MoviePy
            temp_mp4_path = os.path.join(
                temp_dir, f"converted_{os.path.splitext(filename)[0]}.mp4")
            logger.info(
                f"Converting WebM to MP4 using FFmpeg: {temp_video_path} -> {temp_mp4_path}"
            )

            try:
                # Run FFmpeg to convert the video
                ffmpeg_cmd = [
                    'ffmpeg', '-i', temp_video_path, '-c:v', 'libx264', '-crf',
                    '23', '-preset', 'ultrafast', '-c:a', 'aac', '-b:a',
                    '128k', '-y', temp_mp4_path
                ]
                logger.info(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")

                ffmpeg_process = subprocess.run(ffmpeg_cmd,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                text=True)

                if ffmpeg_process.returncode != 0:
                    logger.error(
                        f"FFmpeg conversion failed: {ffmpeg_process.stderr}")
                    raise Exception(
                        f"FFmpeg conversion failed: {ffmpeg_process.stderr}")

                logger.info(f"FFmpeg conversion successful: {temp_mp4_path}")

                # Use the converted MP4 file for processing
                video_path_to_use = temp_mp4_path
            except Exception as e:
                logger.error(f"Error converting video: {e}", exc_info=True)
                # Fallback to the original file if conversion fails
                logger.warning(
                    f"Using original file without conversion due to error")
                video_path_to_use = temp_video_path

            # Download and prepare multiple B-roll images
            broll_clips = []
            if broll_images and len(broll_images) > 0:
                logger.info(
                    f"Preparing {len(broll_images)} B-roll images for video")

                from app.services.r2 import BUCKET, CLOUDFLARE_PUBLIC_URL
                from urllib.parse import urlparse
                from PIL import Image
                import numpy as np

                # Function to download a single B-roll image
                def download_broll_image(broll_url, filename_index):
                    logger.info(f"Downloading B-roll image from: {broll_url}")

                    temp_path = os.path.join(temp_dir,
                                             f"broll_{filename_index}.png")

                    try:
                        parsed_url = urlparse(broll_url)

                        # Check for different URL formats
                        is_cloudflare_url = "r2.dev" in parsed_url.netloc
                        is_regular_r2_url = BUCKET in parsed_url.netloc

                        if is_cloudflare_url or is_regular_r2_url:
                            # It's in our R2 storage, extract the key
                            r2_key = parsed_url.path.lstrip('/')

                            # Handle different URL formats
                            if r2_key.startswith(BUCKET + '/'):
                                r2_key = r2_key[len(BUCKET) + 1:]

                            logger.info(
                                f"B-roll is in our R2 storage, extracted key: {r2_key}"
                            )

                            # Download directly via boto3
                            from app.services.r2 import s3
                            try:
                                s3.download_file(BUCKET, r2_key, temp_path)
                                logger.info(
                                    f"B-roll image downloaded from R2 to: {temp_path}"
                                )
                                return temp_path
                            except Exception as r2_err:
                                logger.warning(
                                    f"Failed to download from R2 directly, trying HTTP request: {r2_err}"
                                )

                                # If direct download fails, try HTTP
                                broll_resp = requests.get(
                                    broll_url,
                                    timeout=10,
                                    headers={
                                        'User-Agent':
                                        'Mozilla/5.0 (X11; Linux x86_64) Clipso/1.0'
                                    })
                                if broll_resp.ok:
                                    with open(temp_path, 'wb') as broll_file:
                                        broll_file.write(broll_resp.content)
                                    logger.info(
                                        f"B-roll image downloaded via HTTP to: {temp_path}"
                                    )
                                    return temp_path
                                else:
                                    logger.error(
                                        f"Failed to download B-roll image via HTTP: {broll_resp.status_code}"
                                    )
                                    return None
                        else:
                            # Try regular HTTP request for external URLs
                            logger.info(
                                f"B-roll is an external URL, downloading via HTTP"
                            )
                            broll_resp = requests.get(
                                broll_url,
                                timeout=10,
                                headers={
                                    'User-Agent':
                                    'Mozilla/5.0 (X11; Linux x86_64) Clipso/1.0'
                                })
                            if broll_resp.ok:
                                with open(temp_path, 'wb') as broll_file:
                                    broll_file.write(broll_resp.content)
                                logger.info(
                                    f"B-roll image downloaded to: {temp_path}")
                                return temp_path
                            else:
                                logger.error(
                                    f"Failed to download B-roll image via HTTP: {broll_resp.status_code}"
                                )
                                return None
                    except Exception as e:
                        logger.error(f"Error downloading B-roll: {e}",
                                     exc_info=True)
                        return None

                # Load the video (using the converted MP4 if available) - moved earlier
                logger.info(f"Loading video with MoviePy: {video_path_to_use}")
                video_clip = VideoFileClip(video_path_to_use)

                # Function to create a B-roll clip from a downloaded image
                def create_broll_clip(image_path, start_time, end_time,
                                      video_clip):
                    logger.info(
                        f"Creating B-roll clip from {image_path} for time {start_time:.2f}s - {end_time:.2f}s"
                    )

                    try:
                        # Load the image with PIL
                        img = Image.open(image_path)

                        # Calculate new dimensions for the B-roll (70% of the video width)
                        # Much larger size for Instagram/YouTube style
                        new_width = int(video_clip.w * 0.70)

                        # Maintain aspect ratio
                        aspect_ratio = img.width / img.height
                        new_height = int(new_width / aspect_ratio)

                        # Use newer resampling method (Pillow 9+ doesn't support ANTIALIAS)
                        try:
                            # Try the newer API first
                            if hasattr(Image, 'Resampling') and hasattr(
                                    Image.Resampling, 'LANCZOS'):
                                resized_img = img.resize(
                                    (new_width, new_height),
                                    Image.Resampling.LANCZOS)
                            # Fall back to the older API
                            elif hasattr(Image, 'LANCZOS'):
                                resized_img = img.resize(
                                    (new_width, new_height), Image.LANCZOS)
                            # Last resort
                            else:
                                resized_img = img.resize(
                                    (new_width, new_height))
                        except Exception as resize_err:
                            logger.warning(
                                f"Error using preferred resize method: {resize_err}, falling back to basic resize"
                            )
                            resized_img = img.resize((new_width, new_height))

                        # Convert PIL Image to numpy array for MoviePy
                        img_array = np.array(resized_img)

                        # Create clip directly from the pre-resized image
                        from moviepy.editor import ImageClip
                        broll_image = ImageClip(img_array)

                        # Calculate center position
                        # Position the image in the center of the frame
                        center_x = (video_clip.w - new_width) / 2
                        # Position B-roll higher up to avoid overlapping with captions
                        center_y = video_clip.h * 0.20  # 20% from the top (higher up)

                        # Create clip with timing and position
                        # Add fade in/out for smooth transitions (Instagram-style)
                        fade_duration = 0.25  # 0.25 second fade in/out
                        
                        broll_clip = broll_image.set_start(start_time).set_end(
                            end_time).set_pos((center_x, center_y))
                            
                        # Add fade in and fade out effects
                        if end_time - start_time > 2 * fade_duration:
                            broll_clip = broll_clip.fadein(fade_duration).fadeout(fade_duration)

                        logger.info(
                            f"Successfully created B-roll clip: {new_width}x{new_height} at position ({center_x:.1f}, {center_y:.1f})"
                        )
                        return broll_clip
                    except Exception as e:
                        logger.error(f"Error creating B-roll clip: {e}",
                                     exc_info=True)
                        return None

                # Process each B-roll image
                for i, broll_item in enumerate(broll_images):
                    try:
                        # Download the image
                        image_path = download_broll_image(broll_item["url"], i)

                        if image_path:
                            # Create clip with specific timing
                            clip = create_broll_clip(image_path,
                                                     broll_item["start_time"],
                                                     broll_item["end_time"],
                                                     video_clip)

                            if clip:
                                broll_clips.append(clip)
                                logger.info(
                                    f"Added B-roll clip {i+1}/{len(broll_images)} at time {broll_item['start_time']:.2f}s"
                                )
                    except Exception as e:
                        logger.error(
                            f"Error processing B-roll image {i+1}: {e}")
                        continue

                logger.info(
                    f"Successfully prepared {len(broll_clips)} B-roll clips")

            # Using the video clip loaded earlier

            # Create subtitle clips from segments
            subtitle_clips = []
            if segments:
                logger.info(
                    f"Creating subtitles from {len(segments)} segments")
                for start, end, text in segments:
                    # Create stylish Instagram-like captions using PIL for consistent sizing
                    try:
                        # Use PIL for text rendering for consistent style
                        logger.info(
                            f"Creating stylish caption for text segment: {text[:30]}..."
                        )

                        from PIL import Image, ImageDraw, ImageFont
                        import numpy as np

                        # Fixed dimensions for consistent caption size
                        caption_width = int(video_clip.w *
                                            0.85)  # 85% of video width

                        # Taller captions for Instagram/YouTube style with more impact
                        caption_height = 100  # Much taller for modern look

                        # Very simple caption style - ONLY white text with thin black shadow
                        # No background at all, truly transparent
                        img = Image.new('RGBA',
                                        (caption_width, caption_height),  # Normal height, simpler
                                        color=(0, 0, 0, 0))  # Completely transparent
                        draw = ImageDraw.Draw(img)
                        
                        # Much larger font size
                        font_size = 65  # Large, bold font
                        
                        # Center text horizontally
                        text_position = (caption_width // 2,
                                        caption_height // 2)  # Center in canvas
                        
                        # Use ALL CAPS for better readability on video
                        caption_text = text.upper()
                        
                        # Pure white text with minimal black shadow/outline
                        # Absolutely no background boxes or rectangles
                        draw.text(
                            text_position,
                            caption_text,
                            fill=(255, 255, 255, 255),  # Bright white
                            align='center',
                            anchor='mm',
                            stroke_width=2,  # Very thin outline 
                            stroke_fill=(0, 0, 0, 180)  # Very light shadow
                        )

                        # Convert to RGB for MoviePy - use transparent background
                        # Create a fully transparent background first
                        rgb_img = Image.new('RGB', img.size, (0, 0, 0, 0))  # Fully transparent
                        # Only paste the actual text pixels, not the background
                        rgb_img.paste(img, (0, 0), mask=img.split()[3])

                        # Convert PIL Image to numpy array for MoviePy
                        img_array = np.array(rgb_img)

                        # Create ImageClip from the numpy array
                        from moviepy.editor import ImageClip
                        text_clip = ImageClip(img_array)

                        logger.info(
                            f"Successfully created stylish caption with size: {caption_width}x{caption_height}"
                        )
                    except Exception as e:
                        # If creation fails, try simpler method
                        logger.warning(
                            f"Error creating stylish caption: {e}, falling back to basic method"
                        )
                        try:
                            # Create simple black background with white text
                            from PIL import Image, ImageDraw
                            import numpy as np

                            # Fixed dimensions - match Mr. Beast caption style in fallback
                            caption_width = int(video_clip.w * 0.85)
                            caption_height = 200  # Much taller for big text

                            # Simple fully transparent background
                            img = Image.new('RGBA',
                                            (caption_width, caption_height),
                                            color=(0, 0, 0, 0))
                            draw = ImageDraw.Draw(img)

                            # Simple ALL CAPS text for better readability
                            caption_text = text.upper()
                            
                            # Large white text with minimal black shadow
                            draw.text(
                                (caption_width // 2, caption_height // 2),
                                caption_text,
                                fill='white',
                                align='center',
                                anchor='mm',
                                stroke_width=2,  # Very thin outline
                                stroke_fill=(0, 0, 0, 180))  # Light shadow

                            # Convert to numpy array
                            img_array = np.array(img)

                            # Create clip
                            from moviepy.editor import ImageClip
                            text_clip = ImageClip(img_array)
                        except Exception as pil_error:
                            # If all methods fail, log the error and continue without this subtitle
                            logger.error(
                                f"Failed to create text clip: {pil_error}")
                            text_clip = None
                            continue

                    # Position captions at the bottom of the frame consistently
                    # Fixed position at the bottom for all captions
                    
                    # Calculate bottom position with margin
                    bottom_margin = video_clip.h * 0.15  # 15% margin from bottom
                    caption_position = ('center', video_clip.h - bottom_margin)
                    
                    # Add fade in effect for captions to make them appear letter by letter
                    # For YouTube/TikTok look
                    fade_in_duration = 0.2  # Faster for snappier Mr. Beast style
                    fade_out_duration = 0.15
                    clip_duration = end - start
                    
                    text_clip = text_clip.set_position(caption_position).set_start(start).set_end(end)
                        
                    # Add fade effects if the clip is long enough
                    if clip_duration > fade_in_duration + fade_out_duration:
                        text_clip = text_clip.fadein(fade_in_duration).fadeout(fade_out_duration)
                    
                    subtitle_clips.append(text_clip)

            # Combine all clips: video, subtitles, and B-roll images
            all_clips = [video_clip] + subtitle_clips + broll_clips

            logger.info(
                f"Creating composite video with {len(all_clips)} clips")
            final_clip = CompositeVideoClip(all_clips)

            # Write final video to temp file
            output_filename = f"final_{filename.replace('.webm', '.mp4')}"
            temp_output_path = os.path.join(temp_dir, output_filename)
            logger.info(f"Writing final video to: {temp_output_path}")

            final_clip.write_videofile(
                temp_output_path,
                codec='libx264',
                audio_codec='aac',
                preset='ultrafast',  # Use faster preset for quicker rendering
                threads=2,
                fps=24)

            # Upload final video to R2
            logger.info(f"Uploading final video to R2")
            final_key = f"final/{output_filename}"

            with open(temp_output_path, 'rb') as final_file:
                upload_fileobj(final_file, final_key, content_type="video/mp4")

            # Update video record with final video key
            video.final_r2_key = final_key
            video.status = "completed"
            await db.commit()

            # Return the URL to the final video
            final_url = get_file_url(final_key)
            logger.info(f"Final video generated and uploaded: {final_url}")
            return final_url

    except Exception as e:
        logger.error(f"Error generating final video: {e}", exc_info=True)

        # Update video status to show error
        if video:
            video.status = f"error: final video generation failed: {str(e)}"
            await db.commit()

        raise Exception(f"Failed to generate final video: {str(e)}")
