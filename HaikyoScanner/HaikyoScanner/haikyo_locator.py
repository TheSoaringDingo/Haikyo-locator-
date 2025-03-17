#!/usr/bin/env python3
"""
HaikyoLocator - A tool for scraping and visualizing abandoned locations in Japan
from haikyo.info with enhanced search capabilities.
"""

import os
import sys
import re
import webbrowser
import json
from urllib.parse import quote, unquote
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, make_response

from scraper import Scraper
from geocoder import Geocoder
from map_generator import MapGenerator

app = Flask(__name__, template_folder='templates', static_folder='static')

# Initialize components
scraper = Scraper()
geocoder = Geocoder()
map_generator = MapGenerator()

# Data storage
locations = []
current_map_path = None

# Progress tracking
progress = {
    'progress': 0,
    'current_step': 'Idle',
    'total_locations': 0,
    'processed_locations': 0
}

@app.route('/')
def index():
    """Render the main search page."""
    return render_template('search_form.html')

@app.route('/progress', methods=['GET'])
def get_progress():
    """Return current progress information."""
    global progress
    return jsonify(progress)

@app.route('/search', methods=['POST'])
def search():
    """Handle search requests and scrape data."""
    # Reset progress
    global progress
    progress = {
        'progress': 0,
        'current_step': 'Initializing search',
        'total_locations': 0,
        'processed_locations': 0
    }
    
    # Get search parameters
    search_term = request.form.get('search_term', '')
    max_locations = request.form.get('max_locations', '10')
    
    try:
        max_locations = int(max_locations)
    except ValueError:
        max_locations = 10
    
    if not search_term:
        return jsonify({'error': 'Search term is required'}), 400
    
    # Check if it's a direct URL or a search term
    if search_term.startswith('http'):
        url = search_term
    else:
        # Try more effective URL formats based on the search term
        # First, check if it looks like a prefecture name
        if re.search(r'[都道府県]$', search_term):
            url = f"https://haikyo.info/explorer/list/prefecture/{quote(search_term)}/"
        # Or if it's likely a city name
        elif re.search(r'[市町村区]$', search_term):
            url = f"https://haikyo.info/explorer/list/address/{quote(search_term)}/"
        # Default to general search
        else:
            url = f"https://haikyo.info/search.php?sw={quote(search_term)}"
    
    try:
        print(f"Searching with URL: {url}, max locations: {max_locations}")
        progress['current_step'] = f"Searching for abandoned locations at {url}"
        progress['progress'] = 10
        
        # Scrape locations with the user-specified maximum
        global locations
        locations = scraper.scrape_locations(url, max_pages=max_locations//5 + 1)
        
        # Limit to max_locations if needed
        if len(locations) > max_locations:
            locations = locations[:max_locations]
        
        print(f"Found {len(locations)} locations before geocoding")
        progress['current_step'] = f"Found {len(locations)} locations. Starting geocoding..."
        progress['progress'] = 30
        progress['total_locations'] = len(locations)
        
        # Geocode locations
        geocoded_locations = []
        for i, location in enumerate(locations):
            # Update progress for each location
            progress_pct = 30 + (i / len(locations) * 50)
            progress['progress'] = progress_pct
            progress['processed_locations'] = i
            progress['current_step'] = f"Geocoding location {i+1}/{len(locations)}: {location.get('name', 'unknown')}"
            
            if not location.get('address'):
                print(f"No address found for {location.get('name', 'unknown location')}")
                continue
                
            coords = geocoder.geocode(location['name'], location['address'])
            if coords:
                location['latitude'] = coords[0]
                location['longitude'] = coords[1]
                geocoded_locations.append(location)
                print(f"Successfully geocoded: {location['name']}")
            else:
                print(f"Failed to geocode: {location['name']}, {location['address']}")
        
        # Generate map if we have geocoded locations
        progress['current_step'] = "Generating interactive map..."
        progress['progress'] = 90
        
        global current_map_path
        if geocoded_locations:
            current_map_path = map_generator.generate_map(geocoded_locations)
            print(f"Generated map with {len(geocoded_locations)} locations")
        else:
            print("No locations were successfully geocoded")
        
        progress['current_step'] = "Search complete!"
        progress['progress'] = 100
        
        # Return success response
        return jsonify({
            'success': True,
            'locations_found': len(locations),
            'locations_mapped': len(geocoded_locations),
            'redirect': '/map'
        })
    except Exception as e:
        progress['current_step'] = f"Error: {str(e)}"
        progress['progress'] = 0
        
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/map')
def show_map():
    """Show the generated map with locations."""
    global locations
    return render_template('map_view.html', locations=locations)

@app.route('/map_file')
def get_map_file():
    """Return the generated HTML map file."""
    global current_map_path
    if current_map_path and os.path.exists(current_map_path):
        return send_file(current_map_path)
    return "Map not generated yet", 404

@app.route('/export', methods=['GET'])
def export_data():
    """Export the scraped data as JSON."""
    global locations
    if not locations:
        return jsonify({'error': 'No data to export'}), 400
    
    format_type = request.args.get('format', 'json')
    
    if format_type == 'kml':
        return export_as_kml()
    else:
        return jsonify(locations)

def export_as_kml():
    """Export location data as KML for use in Google Earth/Maps."""
    global locations
    
    # Create KML content
    kml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml_content += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    kml_content += '<Document>\n'
    kml_content += '  <name>Haikyo Locations</name>\n'
    kml_content += '  <description>Abandoned locations from HaikyoLocator</description>\n'
    
    # Add style for placemarks
    kml_content += '  <Style id="haikyoIcon">\n'
    kml_content += '    <IconStyle>\n'
    kml_content += '      <color>ff0000ff</color>\n'
    kml_content += '      <scale>1.0</scale>\n'
    kml_content += '      <Icon>\n'
    kml_content += '        <href>http://maps.google.com/mapfiles/kml/paddle/red-stars.png</href>\n'
    kml_content += '      </Icon>\n'
    kml_content += '    </IconStyle>\n'
    kml_content += '  </Style>\n'
    
    # Add placemarks for each location
    for location in locations:
        if 'latitude' not in location or 'longitude' not in location:
            continue
            
        name = location.get('name', 'Unknown Location')
        lat = location.get('latitude')
        lon = location.get('longitude')
        address = location.get('address', '')
        category = location.get('category', '')
        url = location.get('url', '')
        
        kml_content += '  <Placemark>\n'
        kml_content += f'    <name>{name}</name>\n'
        kml_content += '    <description><![CDATA[\n'
        kml_content += f'      <p><strong>Address:</strong> {address}</p>\n'
        if category:
            kml_content += f'      <p><strong>Category:</strong> {category}</p>\n'
        if url:
            kml_content += f'      <p><a href="{url}" target="_blank">View Original Page</a></p>\n'
        kml_content += f'      <p><strong>Coordinates:</strong> {lat}, {lon}</p>\n'
        kml_content += '    ]]></description>\n'
        kml_content += '    <styleUrl>#haikyoIcon</styleUrl>\n'
        kml_content += '    <Point>\n'
        kml_content += f'      <coordinates>{lon},{lat},0</coordinates>\n'
        kml_content += '    </Point>\n'
        kml_content += '  </Placemark>\n'
    
    kml_content += '</Document>\n'
    kml_content += '</kml>'
    
    # Create a response with KML content
    response = make_response(kml_content)
    response.headers['Content-Type'] = 'application/vnd.google-earth.kml+xml'
    response.headers['Content-Disposition'] = 'attachment; filename=haikyo_locations.kml'
    
    return response

def main():
    """Main entry point for the application."""
    # Create temporary directory for map files if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    print("Starting HaikyoLocator...")
    print("Open your browser and navigate to http://localhost:5000")
    
    # Open the browser automatically
    webbrowser.open('http://localhost:5000')
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()
