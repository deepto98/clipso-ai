"""
Enhanced transcription module with word-level timestamps
"""

import os
import tempfile
import logging
import json

from app.services.aws_ai_services import aws_ai_services

# Set up logging
logger = logging.getLogger(__name__)

def extract_audio(video_path, output_path=None):
    """
    Extract audio from video file using ffmpeg
    
    Args:
        video_path: Path to video file
        output_path: Optional path for output audio (defaults to temp file)
        
    Returns:
        Path to extracted audio file
    """
    import subprocess
    
    if output_path is None:
        output_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    
    try:
        subprocess.run([
            'ffmpeg',
            '-y',              # Overwrite output file if it exists
            '-i', video_path,  # Input video
            '-vn',             # Disable video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '16000',    # Sample rate
            '-ac', '1',        # Mono audio
            output_path        # Output path
        ], check=True, capture_output=True)
        
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting audio: {e}")
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise

async def transcribe_with_aws_api(
    audio_file,
    language_code='en-US'
):
    """
    Transcribe audio using AWS Transcribe with word-level timestamps
    
    Args:
        audio_file: Path to audio file
        language_code: Language code (e.g., 'en-US', 'es-ES')
        
    Returns:
        Transcript with word-level timestamps
    """
    logger.info(f"Transcribing audio file with AWS Transcribe: {audio_file}")
    
    try:
        # Call AWS Transcribe service
        response = await aws_ai_services.transcribe_audio(audio_file, language_code)
        
        # Response is already formatted to match our expected structure
        segments = response.get('segments', [])
        
        logger.info(f"AWS transcription complete: {len(segments)} segments")
        return segments
    
    except Exception as e:
        logger.error(f"Error in AWS Transcribe: {e}")
        raise

def format_transcript_for_captions(segments):
    """
    Convert transcript segments to format needed for captions
    
    Args:
        segments: Transcript segments 
        
    Returns:
        List of segments with word timestamps for caption generation
    """
    # If segments don't have word-level timestamps, create a simpler structure
    if not segments or "words" not in segments[0]:
        simplified_segments = []
        for segment in segments:
            # Create a synthetic word list if needed
            if "words" not in segment:
                words = segment["text"].split()
                duration_per_word = (segment["end"] - segment["start"]) / len(words)
                
                segment_words = []
                for i, word in enumerate(words):
                    word_start = segment["start"] + (i * duration_per_word)
                    word_end = word_start + duration_per_word
                    segment_words.append({
                        "word": f" {word}",  # Add space prefix
                        "start": word_start,
                        "end": word_end
                    })
                
                segment["words"] = segment_words
            
            simplified_segments.append(segment)
        return simplified_segments
    
    return segments