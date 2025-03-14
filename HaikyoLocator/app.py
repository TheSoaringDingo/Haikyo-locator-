from flask import Flask, render_template, request, jsonify
from scraper import HaikyoScraper
import threading
import queue
import simplekml
import os
from constants import DEFAULT_KML_FILENAME

app = Flask(__name__)
progress_queue = queue.Queue()
current_progress = {'percent': 0, 'message': '', 'locations': []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    num_locations = int(request.form.get('num_locations', 5))

    # Reset progress
    global current_progress
    current_progress = {'percent': 0, 'message': 'Starting scrape...', 'locations': []}

    def scrape_task():
        scraper = HaikyoScraper()
        try:
            # Update progress for initialization
            current_progress['percent'] = 10
            current_progress['message'] = 'Initializing scraper...'

            # Fetch and process locations
            html_content = scraper.fetch_page(url)
            if not html_content:
                current_progress['message'] = 'Failed to fetch main page'
                return

            current_progress['percent'] = 20
            current_progress['message'] = 'Fetching location links...'

            location_links = scraper.get_location_links(html_content)
            if not location_links:
                current_progress['message'] = 'No location links found'
                return

            # Limit to requested number of locations
            location_links = location_links[:num_locations]
            total_locations = len(location_links)
            progress_per_location = 70 / total_locations  # Reserve 30% for init and completion

            locations = []
            for i, link in enumerate(location_links):
                current_progress['message'] = f'Processing location {i+1} of {total_locations}...'
                location = scraper.scrape_location(link)
                if location:
                    location_data = {
                        'name_ja': location['ja'],
                        'name_en': location['en'],
                        'coordinates': location['coordinates'],
                        'url': link
                    }
                    locations.append(location_data)
                    current_progress['locations'].append(location_data)
                current_progress['percent'] = 20 + ((i + 1) * progress_per_location)

            # Generate KML file
            if locations:
                current_progress['percent'] = 90
                current_progress['message'] = 'Generating KML file...'

                kml = simplekml.Kml()
                for loc in locations:
                    if loc.get('coordinates'):
                        lat, lon = loc['coordinates']
                        pnt = kml.newpoint(name=loc['name_ja'])
                        pnt.description = f"{loc['name_en']}\n{loc['url']}"
                        pnt.coords = [(lon, lat)]  # KML uses (longitude, latitude) order
                # Ensure static folder exists
                static_folder = 'static'
                if not os.path.exists(static_folder):
                    os.makedirs(static_folder)
                kml.save(os.path.join(static_folder, DEFAULT_KML_FILENAME))

            # Final progress update
            current_progress['percent'] = 100
            current_progress['message'] = 'Scraping completed'
            progress_queue.put(locations)

        except Exception as e:
            current_progress['message'] = f'Error: {str(e)}'
            progress_queue.put([])

    # Start scraping in a separate thread
    thread = threading.Thread(target=scrape_task)
    thread.start()
    return jsonify({'status': 'started'})

@app.route('/progress')
def get_progress():
    return jsonify(current_progress)

@app.route('/results')
def get_results():
    try:
        locations = progress_queue.get_nowait()
        return jsonify({'locations': locations, 'kml_file': f'/download/{DEFAULT_KML_FILENAME}' if locations else None})
    except queue.Empty:
        return jsonify({'locations': None, 'kml_file': None})

@app.route('/download/<filename>')
def download_file(filename):
    if filename == DEFAULT_KML_FILENAME and os.path.exists(DEFAULT_KML_FILENAME):
        return app.send_static_file(DEFAULT_KML_FILENAME)
    return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)