"""
Text drawer module for creating styled caption images
Advanced text rendering with outline and shadow effects
"""

import os
from moviepy.editor import TextClip
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Default resources
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         '../../fonts/Bangers-Regular.ttf')
if not os.path.exists(FONT_PATH):
    # Try OpenSans as fallback
    FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '../../fonts/OpenSans-Bold.ttf')
    if not os.path.exists(FONT_PATH):
        # Fallback to system font
        FONT_PATH = None

def create_styled_caption(
    text: str,
    video_width: int,
    fontsize: int = 80,
    font_path: str = FONT_PATH,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    blur_shadow: bool = True,
    blur_radius: int = 8
) -> TextClip:
    """
    Create a styled caption with outline and shadow effects
    
    Args:
        text: The text to render
        video_width: Width of the video frame in pixels
        fontsize: Font size for text
        font_path: Path to TTF font file
        color: Text color
        stroke_color: Outline color
        stroke_width: Outline width
        blur_shadow: Whether to add shadow
        blur_radius: Shadow blur radius
        
    Returns:
        MoviePy TextClip for the styled caption
    """
    # Handle empty text
    if not text:
        text = " "  # Use a space rather than empty string
    
    # Create image with PIL (for better control over styling)
    font = _get_font(font_path, fontsize)
    text_size = _get_text_size(text, font)
    
    # Add padding for stroke and shadow
    padding = max(stroke_width * 4, blur_radius * 2) if blur_shadow else stroke_width * 4
    
    # Create image with alpha channel
    img = Image.new('RGBA', 
                   (text_size[0] + padding * 2, text_size[1] + padding * 2), 
                   (0, 0, 0, 0))
    
    # Add shadow if requested
    if blur_shadow:
        shadow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        shadow_draw.text((padding, padding), text, font=font, fill=(0, 0, 0, 200))
        
        # Apply blur to shadow
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Paste shadow onto main image
        img.paste(shadow_img, (0, 0), shadow_img)
    
    # Draw text outline
    draw = ImageDraw.Draw(img)
    
    # Draw text outline by rendering text multiple times with small offsets
    if stroke_width > 0 and stroke_color:
        for offset_x, offset_y in _get_outline_offsets(stroke_width):
            draw.text((padding + offset_x, padding + offset_y), 
                     text, font=font, fill=stroke_color)
    
    # Draw main text
    draw.text((padding, padding), text, font=font, fill=color)
    
    # Convert to numpy array for MoviePy
    img_array = np.array(img)
    
    # Instead of using TextClip with a function, we'll use different approach
    # This avoids the "a bytes-like object is required, not 'function'" error
    from moviepy.editor import ImageClip
    
    # Create an ImageClip from our rendered image array
    clip = ImageClip(img_array)
    # Make it last for 1 second (will be overridden when setting start/end times)
    clip = clip.set_duration(1)
    
    return clip

def _get_font(font_path: str, size: int) -> ImageFont:
    """Get a font for rendering text"""
    if font_path and os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

def _get_text_size(text: str, font: ImageFont) -> tuple:
    """Calculate the size of text with the given font"""
    if hasattr(font, 'getbbox'):
        # Newer Pillow versions
        bbox = font.getbbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    else:
        # Older Pillow versions
        return font.getsize(text)

def _get_outline_offsets(width: int) -> list:
    """Generate offset positions for text outline"""
    offsets = []
    for x in range(-width, width + 1, max(1, width // 2)):
        for y in range(-width, width + 1, max(1, width // 2)):
            if x == 0 and y == 0:
                continue  # Skip center position (main text)
            offsets.append((x, y))
    return offsets

def create_text(
    text: str,
    size: int = 80,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None
) -> Image:
    """
    Create text with outline using PIL.
    Simpler version for cases when MoviePy TextClip is not needed.
    
    Args:
        text: Text to render
        size: Font size
        color: Text color
        stroke_color: Outline color
        stroke_width: Outline width
        font: Font file path (optional)
        
    Returns:
        PIL Image with rendered text
    """
    if not text:
        text = " "
        
    # Get font
    if font and os.path.exists(font):
        try:
            font_obj = ImageFont.truetype(font, size)
        except IOError:
            font_obj = ImageFont.load_default()
    else:
        if FONT_PATH and os.path.exists(FONT_PATH):
            font_obj = ImageFont.truetype(FONT_PATH, size)
        else:
            font_obj = ImageFont.load_default()
    
    # Calculate text size
    text_size = _get_text_size(text, font_obj)
    
    # Add padding for stroke
    padding = stroke_width * 4
    
    # Create image with alpha channel
    img = Image.new('RGBA', 
                   (text_size[0] + padding * 2, text_size[1] + padding * 2), 
                   (0, 0, 0, 0))
    
    draw = ImageDraw.Draw(img)
    
    # Draw text outline
    if stroke_width > 0 and stroke_color:
        for offset_x, offset_y in _get_outline_offsets(stroke_width):
            draw.text((padding + offset_x, padding + offset_y), 
                     text, font=font_obj, fill=stroke_color)
    
    # Draw main text
    draw.text((padding, padding), text, font=font_obj, fill=color)
    
    return img