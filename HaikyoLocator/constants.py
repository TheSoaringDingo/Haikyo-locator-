"""
Constants used throughout the application
"""

# Base URL for the website
BASE_URL = "https://haikyo.info/"

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Default filename for KML output
DEFAULT_KML_FILENAME = "haikyo_locations.kml"

# Default filename for text output
DEFAULT_TEXT_FILENAME = "haikyo_locations.txt"

# KML style for placemarks
KML_STYLE = {
    "icon": "http://maps.google.com/mapfiles/kml/pushpin/red-pushpin.png",
    "scale": 1.0,
    "color": "ff0000ff"  # Red color in ABGR format
}
