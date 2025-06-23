"""
Modern caption generator with stylish text rendering
Inspired by professional caption systems
"""

import os
import tempfile
import logging
import time
from typing import Dict, List, Any, Tuple, Callable, Optional

from moviepy.editor import (
    VideoFileClip, 
    CompositeVideoClip,
    AudioFileClip
)

from .text_drawer import (
    create_styled_caption,
    create_text_ex,
    Word,
    Character,
    blur_text_clip,
)

from .enhanced_transcriber import (
    extract_audio,
    transcribe_with_aws_api,
    format_transcript_for_captions
)

from .segment_parser import (
    parse as parse_segments,
    calculate_display_time
)

from .r2 import upload_fileobj, get_file_url

# Set up logging
logger = logging.getLogger(__name__)

# Cache for processed text
shadow_cache = {}

def fits_frame(max_width: int, font_size: int) -> Callable[[str], bool]:
    """
    Create a function that checks if text fits within frame width
    
    Args:
        max_width: Maximum width in pixels
        font_size: Font size in pixels
        
    Returns:
        Function that takes text and returns True if it fits
    """
    def fit_function(text: str) -> bool:
        # Approximate character width (varies by font)
        char_width = font_size * 0.6
        
        # Calculate approximate text width
        text_width = len(text) * char_width
        
        return text_width <= max_width
    
    return fit_function

async def generate_styled_captions(
    video_file: str,
    output_file: str = None,
    font_size: int = 70,
    font_color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    shadow: bool = True,
    shadow_blur: int = 10,
    max_line_length: int = 40,
    bottom_margin: float = 0.1,  # Percentage of video height from bottom
) -> str:
    """
    Generate clean, stylish captions for a video
    
    Args:
        video_file: Path to input video
        output_file: Optional path for output video (defaults to temp file)
        font_size: Font size for captions
        font_color: Color of caption text
        stroke_color: Color of text outline
        stroke_width: Width of text outline
        shadow: Whether to add shadow
        shadow_blur: Blur radius for shadow
        max_line_length: Maximum characters per line
        bottom_margin: Margin from bottom (as percentage of video height)
        
    Returns:
        Path to output video with captions
    """
    start_time = time.time()
    logger.info(f"Starting caption generation for {video_file}")
    
    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract audio for transcription
        audio_file = os.path.join(temp_dir, "audio.wav")
        audio_file = extract_audio(video_file, audio_file)
        logger.info(f"Extracted audio to {audio_file}")
        
        # Transcribe audio
        segments = await transcribe_with_aws_api(audio_file)
        segments = format_transcript_for_captions(segments)
        logger.info(f"Transcription complete: {len(segments)} segments")
        
        # Load video
        video = VideoFileClip(video_file)
        
        # Calculate dimensions and constraints
        video_width = video.w
        video_height = video.h
        max_text_width = int(video_width * 0.9)  # 90% of video width
        
        # Function to check if text fits
        fit_func = fits_frame(max_text_width, font_size)
        
        # Parse segments into captions
        captions = parse_segments(segments, fit_func)
        captions = calculate_display_time(captions)
        logger.info(f"Generated {len(captions)} caption segments")
        
        # Create video with captions
        clips = [video]  # Start with original video
        
        # Process each caption
        for caption in captions:
            # Position at bottom of frame with margin
            y_position = video_height - (video_height * bottom_margin)
            position = ("center", y_position)
            
            # Create caption text (convert to uppercase for better readability)
            text = caption["text"].upper()
            
            # Create text clip
            text_clip = create_styled_caption(
                text=text,
                video_width=video_width,
                fontsize=font_size,
                color=font_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                blur_shadow=shadow,
                blur_radius=shadow_blur
            )
            
            # Set timing and position
            text_clip = text_clip.set_position(position)
            text_clip = text_clip.set_start(caption["start"])
            text_clip = text_clip.set_end(caption["end"])
            
            # Add to clip list
            clips.append(text_clip)
        
        # Create composite with all elements
        logger.info(f"Creating composite with {len(clips)} elements")
        final_video = CompositeVideoClip(clips)
        
        # Set output path
        if not output_file:
            output_file = os.path.join(temp_dir, "captioned_video.mp4")
        
        # Write to file
        logger.info(f"Writing captioned video to {output_file}")
        final_video.write_videofile(
            output_file,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            fps=24
        )
        
        # Upload to R2 storage
        logger.info("Uploading captioned video to R2 storage")
        with open(output_file, "rb") as f:
            output_key = f"final/{os.path.basename(output_file)}"
            upload_fileobj(f, output_key, content_type="video/mp4")
        
        # Get public URL
        final_url = get_file_url(output_key)
        
        # Log completion
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Caption generation completed in {duration:.2f} seconds")
        logger.info(f"Final video URL: {final_url}")
        
        return final_url