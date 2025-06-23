"""
AWS AI Services integration for Clipso
- Amazon Transcribe for audio transcription
- Amazon Bedrock (Titan Image Generator) for B-roll generation
"""

import logging
import boto3
import json
import tempfile
import hashlib
import requests
from io import BytesIO
from botocore.exceptions import ClientError
import os
import time

# Set up logging
logger = logging.getLogger(__name__)

class AWSAIServices:
    def __init__(self):
        """Initialize AWS AI service clients"""
        # AWS credentials should be in environment variables:
        # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
        
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize clients
        self.transcribe_client = boto3.client('transcribe', region_name=self.region)
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.region)
        
        # S3 bucket for temporary files (will use your existing R2 setup)
        self.temp_bucket = os.getenv('AWS_TEMP_BUCKET', '')
        
    async def transcribe_audio(self, audio_file_path: str, language_code: str = 'en-US') -> dict:
        """
        Transcribe audio using Amazon Transcribe
        
        Args:
            audio_file_path: Path to audio file
            language_code: Language code (e.g., 'en-US', 'es-ES')
            
        Returns:
            Transcript with word-level timestamps
        """
        logger.info(f"Starting AWS Transcribe for audio file: {audio_file_path}")
        
        try:
            # Generate unique job name
            job_name = f"clipso-transcribe-{int(time.time())}-{hashlib.md5(audio_file_path.encode()).hexdigest()[:8]}"
            
            # Upload audio file to S3 (temporary)
            s3_key = f"temp-audio/{job_name}.mp3"
            
            # For this implementation, we'll use the existing R2 storage
            # In production, you might want a dedicated AWS S3 bucket for temp files
            from app.services.r2 import upload_fileobj, get_file_url, BUCKET
            
            # Upload the audio file to R2 for transcription
            with open(audio_file_path, 'rb') as f:
                upload_fileobj(f, s3_key)
            
            # Get the public URL for transcription
            media_uri = get_file_url(s3_key)
            
            # Start transcription job
            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': media_uri},
                MediaFormat='mp3',  # Adjust based on actual format
                LanguageCode=language_code,
                Settings={
                    'ShowSpeakerLabels': False,
                    'ShowAlternatives': False
                }
            )
            
            logger.info(f"Transcription job started: {job_name}")
            
            # Poll for completion
            max_wait_time = 300  # 5 minutes
            wait_interval = 10   # 10 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                status_response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = status_response['TranscriptionJob']['TranscriptionJobStatus']
                logger.info(f"Transcription job status: {status}")
                
                if status == 'COMPLETED':
                    # Get the transcript
                    transcript_uri = status_response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    transcript_response = requests.get(transcript_uri)
                    transcript_data = transcript_response.json()
                    
                    formatted_transcript = self._format_aws_transcript(transcript_data)
                    
                    # Cleanup
                    self._cleanup_transcription_job(job_name, s3_key)
                    
                    return formatted_transcript
                    
                elif status == 'FAILED':
                    failure_reason = status_response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    logger.error(f"Transcription failed: {failure_reason}")
                    self._cleanup_transcription_job(job_name, s3_key)
                    raise Exception(f"AWS Transcribe failed: {failure_reason}")
                
                # Wait before next check
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            # Timeout reached
            logger.error(f"Transcription job timed out after {max_wait_time} seconds")
            self._cleanup_transcription_job(job_name, s3_key)
            raise Exception("Transcription job timed out")
            
        except Exception as e:
            logger.error(f"Error in AWS transcription: {e}", exc_info=True)
            raise
    
    def _format_aws_transcript(self, aws_transcript: dict) -> dict:
        """
        Convert AWS Transcribe format
        
        Args:
            aws_transcript: Raw transcript from AWS Transcribe
            
        Returns:
            Formatted transcript compatible with existing code
        """
        try:
            results = aws_transcript['results']
            transcript_text = results['transcripts'][0]['transcript']
            
            # Extract word-level timestamps
            words = []
            segments = []
            
            current_segment_words = []
            segment_start = None
            segment_text = ""
            
            for item in results['items']:
                if item['type'] == 'pronunciation':
                    word_data = {
                        'word': ' ' + item['alternatives'][0]['content'],  # Add space prefix
                        'start': float(item['start_time']),
                        'end': float(item['end_time'])
                    }
                    words.append(word_data)
                    current_segment_words.append(word_data)
                    
                    if segment_start is None:
                        segment_start = float(item['start_time'])
                    
                    segment_text += item['alternatives'][0]['content'] + " "
                    
                    # Create segments every ~10 words or at punctuation
                    if len(current_segment_words) >= 10 or item['alternatives'][0]['content'].endswith('.'):
                        if current_segment_words:
                            segment = {
                                'start': segment_start,
                                'end': current_segment_words[-1]['end'],
                                'text': segment_text.strip(),
                                'words': current_segment_words.copy()
                            }
                            segments.append(segment)
                            
                            # Reset for next segment
                            current_segment_words = []
                            segment_start = None
                            segment_text = ""
            
            # Handle remaining words
            if current_segment_words:
                segment = {
                    'start': segment_start,
                    'end': current_segment_words[-1]['end'],
                    'text': segment_text.strip(),
                    'words': current_segment_words
                }
                segments.append(segment)
            
            return {
                'text': transcript_text,
                'segments': segments,
                'words': words,
                'language': 'en',  # AWS doesn't return detected language in same format
                'duration': words[-1]['end'] if words else 0
            }
            
        except Exception as e:
            logger.error(f"Error formatting AWS transcript: {e}", exc_info=True)
            # Return minimal format on error
            return {
                'text': aws_transcript.get('results', {}).get('transcripts', [{}])[0].get('transcript', ''),
                'segments': [],
                'words': []
            }
    
    def _cleanup_transcription_job(self, job_name: str, s3_key: str):
        """Clean up AWS resources after transcription"""
        try:
            # Delete transcription job
            self.transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
            logger.info(f"Deleted transcription job: {job_name}")
        except Exception as e:
            logger.warning(f"Failed to delete transcription job {job_name}: {e}")
        
        try:
            # Delete temporary S3 file (from R2 in our case)
            from app.services.r2 import s3, BUCKET
            s3.delete_object(Bucket=BUCKET, Key=s3_key)
            logger.info(f"Deleted temporary file: {s3_key}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {s3_key}: {e}")
    
    async def generate_image(self, prompt: str, style: str = "photographic") -> str:
        """
        Generate B-roll image using Amazon Bedrock (Titan Image Generator)
        
        Args:
            prompt: Text prompt for image generation
            style: Image style (photographic, cinematic, pop-art, etc.)
            
        Returns:
            URL to generated image in R2 storage
        """
        logger.info(f"Generating image with AWS Bedrock for prompt: {prompt}")
        
        try:
            # Prepare the request for Titan Image Generator
            request_body = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": prompt,
                    "style": style
                },
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "quality": "premium",
                    "height": 1024,
                    "width": 1024,
                    "cfgScale": 7.5,
                    "seed": None
                }
            }
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId="amazon.titan-image-generator-v1",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'images' not in response_body or not response_body['images']:
                raise Exception("No images returned from Bedrock")
            
            # Get the base64 encoded image
            image_base64 = response_body['images'][0]
            
            # Convert to bytes
            import base64
            image_bytes = base64.b64decode(image_base64)
            
            # Generate cache key based on prompt
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
            key = f"broll/aws-{prompt_hash}.png"
            
            # Upload to R2
            from app.services.r2 import upload_fileobj, get_file_url
            
            img_buffer = BytesIO(image_bytes)
            upload_fileobj(img_buffer, key, content_type="image/png")
            
            # Get the URL
            r2_url = get_file_url(key)
            logger.info(f"B-roll image uploaded to R2: {r2_url}")
            
            return r2_url
            
        except Exception as e:
            logger.error(f"AWS Bedrock image generation failed: {e}", exc_info=True)
            
            # Return fallback image if available
            from app.services.r2 import get_file_url, file_exists
            fallback_key = "broll/fallback.png"
            if file_exists(fallback_key):
                logger.info("Using fallback B-roll image due to AWS error")
                return get_file_url(fallback_key)
            
            raise


# Global instance
aws_ai_services = AWSAIServices()