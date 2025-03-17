"""
Module for generating KML files from location data.
"""

import os
import simplekml

class KMLGenerator:
    """
    Class for generating KML files from location data.
    """
    
    def __init__(self):
        """
        Initialize the KML generator.
        """
        pass
    
    def generate_kml(self, locations, output_path, callback=None):
        """
        Generate a KML file from a list of locations.
        
        Args:
            locations (list): A list of location dictionaries.
            output_path (str): Path to save the KML file.
            callback (function, optional): Callback function for progress updates.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Create a new KML document
            kml = simplekml.Kml()
            
            # Set document name and description
            kml.document.name = "Haikyo Locations"
            kml.document.description = f"Abandoned locations from haikyo.info ({len(locations)} locations)"
            
            total_locations = len(locations)
            valid_locations = 0
            
            for i, location in enumerate(locations):
                # Skip locations without valid coordinates
                if not location['coordinates'] or \
                   location['coordinates']['lat'] == 0 and location['coordinates']['lng'] == 0:
                    if callback:
                        progress = (i + 1) / total_locations * 100
                        callback(progress, f"Skipping location without coordinates: {location['title']}")
                    continue
                
                # Create a placemark for the location
                placemark = kml.newpoint(
                    name=location['title'],
                    description=self._format_description(location),
                    coords=[(location['coordinates']['lng'], location['coordinates']['lat'])]
                )
                
                # Set placemark style (optional customization)
                placemark.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/shopping.png'
                placemark.style.iconstyle.scale = 1.0
                
                valid_locations += 1
                
                if callback:
                    progress = (i + 1) / total_locations * 100
                    callback(progress, f"Added location to KML: {location['title']}")
            
            # Save the KML file
            kml.save(output_path)
            
            if callback:
                callback(100, f"KML file generated with {valid_locations} locations")
            
            return True
        
        except Exception as e:
            if callback:
                callback(0, f"Error generating KML file: {str(e)}")
            return False
    
    def _format_description(self, location):
        """
        Format the description for a KML placemark.
        
        Args:
            location (dict): Location dictionary with details.
            
        Returns:
            str: HTML-formatted description for the KML placemark.
        """
        description = f"""
        <![CDATA[
        <h3>{location['title']}</h3>
        {f"<p><strong>Address:</strong> {location['address']}</p>" if location.get('address') else ""}
        <p>{location['description'][:200]}{'...' if len(location['description']) > 200 else ''}</p>
        <p><a href="{location['url']}" target="_blank">View on haikyo.info</a></p>
        """
        
        # Add images if available (limit to 3 to keep KML file size reasonable)
        if location['images'] and len(location['images']) > 0:
            description += "<div style='display: flex; flex-wrap: wrap;'>"
            for img_url in location['images'][:3]:
                description += f"<img src='{img_url}' style='max-width: 200px; margin: 5px;' />"
            description += "</div>"
        
        description += "]]>"
        return description
