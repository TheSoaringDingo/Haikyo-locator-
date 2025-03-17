"""
Main entry point for the Haikyo Locator application.
This application scrapes abandoned location data from haikyo.info and
generates KML files for mapping.

This version uses a Flask web interface to make it compatible with Replit.
"""

from app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
