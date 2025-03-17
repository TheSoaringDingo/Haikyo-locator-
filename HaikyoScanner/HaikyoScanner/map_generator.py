"""
Map Generator module for HaikyoLocator.
Handles the creation of interactive maps with location markers.
"""

import os
import folium
from folium.plugins import MarkerCluster
import random
import string
import tempfile

class MapGenerator:
    """A class to generate interactive maps with location markers."""
    
    def __init__(self):
        """Initialize the map generator."""
        self.temp_dir = 'temp'
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def _random_string(self, length=8):
        """Generate a random string for unique filenames."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def _create_popup_html(self, location):
        """Create HTML content for location popups."""
        html = f"""
        <div class="location-popup">
            <h3>{location.get('name', 'Unknown Location')}</h3>
        """
        
        if location.get('image_url'):
            html += f"""<img src="{location['image_url']}" alt="{location.get('name', 'Location image')}" style="max-width:200px; max-height:150px;"><br>"""
        
        if location.get('address'):
            html += f"""<strong>Address:</strong> {location['address']}<br>"""
        
        if location.get('category'):
            html += f"""<strong>Category:</strong> {location['category']}<br>"""
        
        if location.get('description'):
            html += f"""<p>{location['description']}</p>"""
        
        if location.get('url'):
            html += f"""<a href="{location['url']}" target="_blank">View Original Page</a>"""
        
        html += "</div>"
        return html
    
    def generate_map(self, locations, center=None):
        """
        Generate an interactive map with markers for the given locations.
        
        Args:
            locations (list): A list of dictionaries containing location data
            center (tuple): Optional (latitude, longitude) to center the map
            
        Returns:
            str: Path to the generated HTML map file
        """
        if not locations:
            raise ValueError("No locations provided for map generation")
        
        # Determine map center if not provided
        if not center:
            # Use the center of all locations or default to center of Japan
            if all('latitude' in loc and 'longitude' in loc for loc in locations):
                lats = [loc['latitude'] for loc in locations]
                lons = [loc['longitude'] for loc in locations]
                center = (sum(lats) / len(lats), sum(lons) / len(lons))
            else:
                center = (36.2048, 138.2529)  # Center of Japan
        
        # Create map
        m = folium.Map(location=center, zoom_start=7, tiles="OpenStreetMap")
        
        # Add marker cluster
        marker_cluster = MarkerCluster().add_to(m)
        
        # Add markers for each location
        for location in locations:
            if 'latitude' in location and 'longitude' in location:
                popup_html = self._create_popup_html(location)
                folium.Marker(
                    location=[location['latitude'], location['longitude']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=location.get('name', 'Unknown Location'),
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(marker_cluster)
        
        # Generate a unique filename
        filename = f"haikyo_map_{self._random_string()}.html"
        filepath = os.path.join(self.temp_dir, filename)
        
        # Save map to file
        m.save(filepath)
        
        return filepath
