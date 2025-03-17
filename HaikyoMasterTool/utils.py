"""
Utility functions for the Haikyo Locator application.
"""

import re
import os
import sys
import logging
from urllib.parse import urlparse, urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('haikyo_locator')

def is_valid_url(url):
    """
    Check if a URL is valid.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def normalize_url(url, base_url="https://haikyo.info"):
    """
    Normalize a URL, ensuring it's properly formatted.
    
    Args:
        url (str): URL to normalize
        base_url (str, optional): Base URL to use for relative URLs
        
    Returns:
        str: Normalized URL
    """
    if not url:
        return None
    
    # Check if the URL is relative
    if not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
    
    return url

def extract_coordinates_from_text(text):
    """
    Extract coordinates from text using regex patterns.
    
    Args:
        text (str): Text to search for coordinates
        
    Returns:
        dict: Dictionary with lat and lng keys, or None if no coordinates found
    """
    # Pattern for standard decimal coordinates (e.g. "35.123456, 139.123456")
    pattern1 = r'(\d{1,2}\.\d{5,})[,\s]+(\d{2,3}\.\d{5,})'
    
    # Pattern for degrees, minutes, seconds (e.g. "35°41'23.45"N, 139°41'30.12"E")
    pattern2 = r'(\d{1,2})°\s*(\d{1,2})\'?\s*(\d{1,2}(?:\.\d+)?)\"?\s*([NS])[,\s]+(\d{1,3})°\s*(\d{1,2})\'?\s*(\d{1,2}(?:\.\d+)?)\"?\s*([EW])'
    
    # Try standard decimal pattern
    match = re.search(pattern1, text)
    if match:
        try:
            lat = float(match.group(1))
            lng = float(match.group(2))
            return {'lat': lat, 'lng': lng}
        except (ValueError, TypeError):
            pass
    
    # Try degrees, minutes, seconds pattern
    match = re.search(pattern2, text)
    if match:
        try:
            lat_deg = float(match.group(1))
            lat_min = float(match.group(2))
            lat_sec = float(match.group(3))
            lat_dir = match.group(4)
            
            lng_deg = float(match.group(5))
            lng_min = float(match.group(6))
            lng_sec = float(match.group(7))
            lng_dir = match.group(8)
            
            lat = lat_deg + (lat_min / 60) + (lat_sec / 3600)
            if lat_dir == 'S':
                lat = -lat
                
            lng = lng_deg + (lng_min / 60) + (lng_sec / 3600)
            if lng_dir == 'W':
                lng = -lng
                
            return {'lat': lat, 'lng': lng}
        except (ValueError, TypeError):
            pass
    
    return None

def sanitize_filename(filename):
    """
    Sanitize a filename, removing invalid characters.
    
    Args:
        filename (str): Filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    # Replace characters that are not allowed in filenames
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Ensure the filename is not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized
