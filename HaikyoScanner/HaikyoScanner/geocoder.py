"""
Geocoder module for HaikyoLocator.
Handles geocoding of addresses for map visualization.
"""

import re
import time
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Geocoder:
    """A class to handle geocoding of location addresses."""
    
    def __init__(self):
        """Initialize the geocoder."""
        self.geolocator = Nominatim(user_agent="haikyo_locator")
        self.cache = {}  # Simple in-memory cache
    
    def _normalize_address(self, address):
        """Normalize address for better geocoding results."""
        if not address:
            return ""
        
        # Remove common non-address parts
        address = re.sub(r'電話番号.*$', '', address, flags=re.IGNORECASE)
        address = re.sub(r'TEL.*$', '', address, flags=re.IGNORECASE)
        
        # Make sure the address contains Japan
        if '日本' not in address and 'Japan' not in address:
            address = f"{address}, Japan"
        
        return address.strip()
    
    def _fallback_geocoding(self, name, address):
        """Fallback geocoding method using a combination of name and address."""
        # Try with just the prefecture if available
        prefecture_match = re.search(r'(.+?)[都道府県]', address)
        if prefecture_match:
            prefecture = prefecture_match.group(0)
            query = f"{prefecture}, Japan"
            coords = self._geocode_with_retry(query)
            if coords:
                return coords
        
        # Try with name and Japan
        query = f"{name}, Japan"
        return self._geocode_with_retry(query)
    
    def _geocode_with_retry(self, query, max_retries=3):
        """Geocode with retry logic to handle timeouts."""
        if not query:
            return None
        
        # Check cache first
        if query in self.cache:
            return self.cache[query]
        
        for attempt in range(max_retries):
            try:
                location = self.geolocator.geocode(query)
                if location:
                    coords = (location.latitude, location.longitude)
                    self.cache[query] = coords  # Cache result
                    return coords
                time.sleep(1)  # Be nice to the geocoding service
            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                logger.warning(f"Geocoding retry {attempt+1}/{max_retries} for '{query}': {str(e)}")
                time.sleep(2)  # Wait before retry
            except Exception as e:
                logger.error(f"Geocoding error for '{query}': {str(e)}")
                break
        
        return None
    
    def geocode(self, name, address):
        """
        Geocode a location based on its name and address.
        
        Args:
            name (str): The name of the location
            address (str): The address of the location
            
        Returns:
            tuple: (latitude, longitude) or None if geocoding fails
        """
        # Try geocoding with the full address first
        normalized_address = self._normalize_address(address)
        coords = self._geocode_with_retry(normalized_address)
        
        # If that fails, try fallback methods
        if not coords:
            coords = self._fallback_geocoding(name, normalized_address)
        
        # If all geocoding attempts fail, return default coordinates for Japan
        if not coords:
            logger.warning(f"Geocoding failed for {name}: {address}")
            # Return approximate coordinates for Japan if nothing else works
            return (36.2048, 138.2529)  # Center of Japan
        
        return coords
