"""
Segment parser module for handling transcript segments and words
Optimized for generating clean, readable captions
"""

import logging
from typing import List, Dict, Any, Callable

logger = logging.getLogger(__name__)

def has_partial_sentence(text):
    """
    Check if the text ends with a partial sentence (e.g., ends after a period in the middle)
    """
    # Determine if text ends naturally or needs continuation
    sentence_enders = ('.', '!', '?', ':', '...', ';')
    last_sentence_end = max(text.rfind(end) for end in sentence_enders)
    
    # If we found a sentence ender and it's not at the end, 
    # then we have partial sentence
    if last_sentence_end > 0 and last_sentence_end < len(text) - 1:
        # Check that we actually have meaningful text after the sentence end
        remaining = text[last_sentence_end+1:].strip()
        if len(remaining) > 3:  # More than just a couple characters
            return True
    
    return False

def parse(
    segments: List[Dict[str, Any]],
    fit_function: Callable,
    allow_partial_sentences: bool = False,
):
    """
    Parse transcription segments into captions that fit on the video frame
    
    Args:
        segments: List of transcript segments with words and timestamps
        fit_function: Function that determines if text fits in the frame
        allow_partial_sentences: Whether to allow breaking at partial sentences
        
    Returns:
        List of caption objects with start/end times and text
    """
    captions = []
    current_caption = ""
    current_start = 0
    current_end = 0
    
    # Process each segment
    for segment in segments:
        segment_text = segment.get('text', '').strip()
        segment_start = segment.get('start', 0)
        segment_end = segment.get('end', 0)
        
        # If segment has words with timestamps, use those for fine-grained captions
        words = segment.get('words', [])
        
        if words:
            # Start a new caption if none exists
            if not current_caption:
                current_start = words[0].get('start', segment_start)
                current_caption = ""
            
            # Process each word 
            for word_idx, word in enumerate(words):
                word_text = word.get('text', '')
                word_start = word.get('start', 0)
                word_end = word.get('end', 0)
                
                # Skip empty words
                if not word_text.strip():
                    continue
                
                # Test if adding this word would make the caption too long
                test_caption = current_caption + (" " if current_caption else "") + word_text
                
                if fit_function(test_caption):
                    # Word fits, add it to current caption
                    current_caption = test_caption
                    current_end = word_end
                else:
                    # Word doesn't fit, start a new caption
                    
                    # Before creating a new caption, check if we're breaking at a sentence boundary
                    if not allow_partial_sentences and has_partial_sentence(current_caption):
                        # Find a better break point - go back to last sentence end
                        sentence_enders = ('.', '!', '?', ':', '...', ';')
                        last_sentence_end = max(current_caption.rfind(end) for end in sentence_enders)
                        
                        if last_sentence_end > 0:
                            # Split the caption at sentence end
                            part1 = current_caption[:last_sentence_end+1].strip()
                            part2 = current_caption[last_sentence_end+1:].strip()
                            
                            # Add first part as a caption
                            captions.append({
                                "text": part1,
                                "start": current_start,
                                "end": current_end - len(part2) * 0.1  # Approximate time adjustment
                            })
                            
                            # Start a new caption with the remainder
                            current_caption = part2 + (" " if part2 else "") + word_text
                            current_start = current_end - len(part2) * 0.1
                            current_end = word_end
                            continue
                    
                    # Add the current caption
                    if current_caption:
                        captions.append({
                            "text": current_caption,
                            "start": current_start,
                            "end": current_end
                        })
                    
                    # Start a new caption with this word
                    current_caption = word_text
                    current_start = word_start
                    current_end = word_end
        else:
            # Segment doesn't have individual words, use whole segment
            # Only use if segment_text fits on screen
            if fit_function(segment_text):
                captions.append({
                    "text": segment_text,
                    "start": segment_start,
                    "end": segment_end
                })
            else:
                # Split long segment text into smaller parts
                words = segment_text.split()
                current_line = ""
                start_idx = 0
                
                for idx, word in enumerate(words):
                    test_line = current_line + (" " if current_line else "") + word
                    
                    if fit_function(test_line):
                        current_line = test_line
                    else:
                        # Add current line as caption
                        if current_line:
                            # Calculate approximate times based on word positions
                            line_start = segment_start + (segment_end - segment_start) * (start_idx / len(words))
                            line_end = segment_start + (segment_end - segment_start) * (idx / len(words))
                            
                            captions.append({
                                "text": current_line,
                                "start": line_start,
                                "end": line_end
                            })
                        
                        # Start new line
                        current_line = word
                        start_idx = idx
                
                # Add final line if any
                if current_line:
                    line_start = segment_start + (segment_end - segment_start) * (start_idx / len(words))
                    
                    captions.append({
                        "text": current_line,
                        "start": line_start,
                        "end": segment_end
                    })
    
    # Add any remaining caption
    if current_caption:
        captions.append({
            "text": current_caption,
            "start": current_start,
            "end": current_end
        })
    
    # Calculate caption durations for better display
    captions = calculate_display_time(captions)
    
    return captions

def calculate_display_time(captions, min_duration=1.0, max_duration=5.0, 
                         chars_per_second=15):
    """
    Calculate optimal display time for captions based on text length
    
    Args:
        captions: List of caption objects
        min_duration: Minimum display time in seconds
        max_duration: Maximum display time in seconds
        chars_per_second: Reading speed in characters per second
        
    Returns:
        The same captions with adjusted end times if needed
    """
    for i, caption in enumerate(captions):
        # Calculate minimum required duration based on text length
        text_length = len(caption["text"])
        required_duration = text_length / chars_per_second
        
        # Apply minimum and maximum constraints
        desired_duration = max(min_duration, min(required_duration, max_duration))
        
        # Calculate actual duration
        actual_duration = caption["end"] - caption["start"]
        
        # If caption is too short for comfortable reading, extend end time
        if actual_duration < desired_duration:
            # Check if we can extend without overlapping next caption
            if i < len(captions) - 1:
                next_start = captions[i+1]["start"]
                # Don't extend into next caption's time
                new_end = min(caption["start"] + desired_duration, next_start - 0.1)
                caption["end"] = new_end
            else:
                # Last caption, can extend freely
                caption["end"] = caption["start"] + desired_duration
    
    return captions