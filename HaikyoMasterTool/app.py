"""
Flask web application for the Haikyo Locator.
This provides a web interface for searching, scraping, and generating KML files.
"""

import os
import json
import time
import threading
from flask import Flask, render_template, request, jsonify, send_file, session, flash, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename

from scraper import HaikyoScraper
from kml_generator import KMLGenerator
from utils import sanitize_filename

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Bootstrap
bootstrap = Bootstrap(app)

# Global variables for tracking status
search_results = []
locations = []
progress_data = {
    'progress': 0,
    'message': 'Ready',
    'status': 'ready'  # ready, searching, scraping, generating
}
lock = threading.Lock()

# Initialize scraper and KML generator
scraper = HaikyoScraper()
kml_generator = KMLGenerator()

# Form for search
class SearchForm(FlaskForm):
    search_term = StringField('Search Term', validators=[DataRequired()])
    submit = SubmitField('Search')

def update_progress(progress, message, status=None):
    """Update progress information for status tracking."""
    global progress_data
    with lock:
        progress_data['progress'] = progress
        progress_data['message'] = message
        if status:
            progress_data['status'] = status

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', form=SearchForm())

@app.route('/search', methods=['POST'])
def search():
    """Handle search form submission."""
    form = SearchForm()
    if form.validate_on_submit():
        search_term = form.search_term.data
        # Start search in a background thread
        threading.Thread(target=search_task, args=(search_term,), daemon=True).start()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Invalid form submission'})

def search_task(search_term):
    """Perform the search task in a background thread."""
    global search_results, locations
    
    try:
        update_progress(0, f"Searching for '{search_term}'...", 'searching')
        
        # Clear previous results
        search_results = []
        locations = []
        
        # Perform the search
        urls = scraper.search_locations(search_term, 
                                        lambda p, m: update_progress(p, m, 'searching'))
        
        # Process URLs to extract basic information
        for i, url in enumerate(urls):
            progress = (i + 1) / len(urls) * 100
            update_progress(progress, f"Processing search result {i+1} of {len(urls)}", 'searching')
            
            # Extract basic info from URL
            title = url.split('/')[-1].replace('.html', '').title()
            
            # Add to results
            search_results.append({
                'id': i,
                'title': title,
                'url': url,
                'address': "Click 'Scrape' for details",
                'coordinates': "Click 'Scrape' to get coordinates"
            })
            
            # Add to locations list
            locations.append({
                'title': title,
                'url': url,
                'address': "",
                'coordinates': None,
                'description': "",
                'images': [],
                'translated_title': title,
                'translated_address': "",
                'translated_description': ""
            })
            
            # Pause briefly to prevent overwhelming the server
            time.sleep(0.1)
        
        # Update status
        if len(urls) > 0:
            update_progress(100, f"Found {len(urls)} locations", 'ready')
        else:
            update_progress(100, "No locations found. Try a different search term.", 'ready')
    
    except Exception as e:
        update_progress(0, f"Error during search: {str(e)}", 'ready')

@app.route('/get_progress')
def get_progress():
    """Return the current progress data."""
    with lock:
        return jsonify(progress_data)

@app.route('/get_results')
def get_results():
    """Return the current search results."""
    return jsonify({'results': search_results})

@app.route('/scrape', methods=['POST'])
def scrape():
    """Handle scraping request for selected locations."""
    try:
        data = request.get_json()
        selected_ids = data.get('selected_ids', [])
        
        if not selected_ids:
            return jsonify({'status': 'error', 'message': 'No locations selected'})
        
        # Start scraping in a background thread
        threading.Thread(target=scrape_task, args=(selected_ids,), daemon=True).start()
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def scrape_task(selected_ids):
    """Perform the scraping task in a background thread."""
    global search_results, locations
    
    try:
        update_progress(0, "Scraping selected locations...", 'scraping')
        
        selected_urls = []
        selected_indices = []
        
        # Get URLs for selected items
        for item_id in selected_ids:
            item_id = int(item_id)
            if 0 <= item_id < len(search_results):
                selected_urls.append(search_results[item_id]['url'])
                selected_indices.append(item_id)
        
        # Scrape location details
        scraped_locations = scraper.scrape_batch(selected_urls, 
                                               lambda p, m: update_progress(p, m, 'scraping'))
        
        # Update locations and search results with scraped data
        for i, location_data in enumerate(scraped_locations):
            index = selected_indices[i]
            locations[index] = location_data
            
            # Update the search results
            coords_text = f"{location_data['coordinates']['lat']}, {location_data['coordinates']['lng']}"
            search_results[index]['title'] = location_data['title']
            search_results[index]['address'] = location_data.get('address', "")
            search_results[index]['coordinates'] = coords_text
        
        # Update status
        update_progress(100, f"Scraped {len(scraped_locations)} locations", 'ready')
    
    except Exception as e:
        update_progress(0, f"Error during scraping: {str(e)}", 'ready')

@app.route('/generate_kml', methods=['POST'])
def generate_kml():
    """Handle KML generation request."""
    try:
        # Check if we have locations with coordinates
        valid_locations = [loc for loc in locations if loc['coordinates'] and 
                           (loc['coordinates']['lat'] != 0 or loc['coordinates']['lng'] != 0)]
        
        if not valid_locations:
            return jsonify({
                'status': 'error', 
                'message': 'No locations with valid coordinates to export. Please scrape locations first.'
            })
        
        # Generate a filename based on timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"haikyo_locations_{timestamp}.kml"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Start KML generation in a background thread
        thread = threading.Thread(
            target=generate_kml_task, 
            args=(output_path, filename),
            daemon=True
        )
        thread.start()
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def generate_kml_task(output_path, filename):
    """Generate KML file in a background thread."""
    try:
        update_progress(0, "Generating KML file...", 'generating')
        
        # Generate KML file
        success = kml_generator.generate_kml(
            locations, 
            output_path, 
            lambda p, m: update_progress(p, m, 'generating')
        )
        
        if success:
            update_progress(
                100, 
                f"KML file generated successfully. <a href='/download/{filename}' class='btn btn-success btn-sm'>Download KML</a>", 
                'ready'
            )
        else:
            update_progress(0, "Failed to generate KML file", 'ready')
    
    except Exception as e:
        update_progress(0, f"Error generating KML file: {str(e)}", 'ready')

@app.route('/download/<filename>')
def download_file(filename):
    """Download the generated KML file."""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('File not found', 'error')
        return redirect(url_for('index'))

@app.route('/location_details/<int:location_id>')
def location_details(location_id):
    """Get details for a specific location."""
    if 0 <= location_id < len(locations):
        return jsonify({'status': 'success', 'location': locations[location_id]})
    return jsonify({'status': 'error', 'message': 'Location not found'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)