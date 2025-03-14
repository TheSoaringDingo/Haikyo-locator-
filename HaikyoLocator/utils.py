"""
Utility functions for the haikyo.info scraper
"""
import re
import logging
from typing import Tuple, Optional

def parse_coordinates(coord_text: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinates from text in various formats.
    Returns tuple of (latitude, longitude) or None if parsing fails.
    """
    if not coord_text:
        return None

    try:
        # Remove any whitespace and unwanted characters
        coord_text = coord_text.strip()

        # Try to match coordinates in decimal format
        decimal_pattern = r'(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)'
        decimal_match = re.search(decimal_pattern, coord_text)

        if decimal_match:
            lat = float(decimal_match.group(1))
            lon = float(decimal_match.group(2))
            return validate_coordinates(lat, lon)

        # Try to match coordinates in degrees/minutes/seconds format
        dms_pattern = r'(\d+)°\s*(\d+)\'(?:\s*(\d+(?:\.\d+)?)")?\s*([NS])[,\s]+(\d+)°\s*(\d+)\'(?:\s*(\d+(?:\.\d+)?)")?\s*([EW])'
        dms_match = re.search(dms_pattern, coord_text)

        if dms_match:
            lat = convert_dms_to_decimal(
                int(dms_match.group(1)),
                int(dms_match.group(2)),
                float(dms_match.group(3) or 0),
                dms_match.group(4)
            )
            lon = convert_dms_to_decimal(
                int(dms_match.group(5)),
                int(dms_match.group(6)),
                float(dms_match.group(7) or 0),
                dms_match.group(8)
            )
            return validate_coordinates(lat, lon)

        # Try to match coordinates from map data attributes
        map_pattern = r'lat["\']?\s*:\s*(-?\d+\.?\d*)[,\s]+lon["\']?\s*:\s*(-?\d+\.?\d*)'
        map_match = re.search(map_pattern, coord_text, re.IGNORECASE)

        if map_match:
            lat = float(map_match.group(1))
            lon = float(map_match.group(2))
            return validate_coordinates(lat, lon)

        return None

    except Exception as e:
        logging.error(f"Error parsing coordinates '{coord_text}': {str(e)}")
        return None

def convert_dms_to_decimal(degrees: int, minutes: int, seconds: float, direction: str) -> float:
    """
    Convert coordinates from degrees/minutes/seconds to decimal format
    """
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

def validate_coordinates(lat: float, lon: float) -> Optional[Tuple[float, float]]:
    """
    Validate that coordinates are within valid ranges
    """
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return (lat, lon)
    return None

def format_coordinates(lat: float, lon: float) -> str:
    """
    Format coordinates for text output
    """
    return f"{lat:.6f}, {lon:.6f}"