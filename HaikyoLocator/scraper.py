"""
Main scraper script for haikyo.info
"""
import logging
import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse, unquote
from constants import BASE_URL, HEADERS, DEFAULT_TEXT_FILENAME
from googletrans import Translator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HaikyoScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.translator = Translator()
        self.translation_cache = {}
        self.processed_urls = set()  # Cache for processed URLs

    def fetch_page(self, url: str) -> str:
        """
        Fetch a page and return its HTML content
        """
        try:
            # Don't fetch URLs we've already processed
            if url in self.processed_urls:
                logging.debug(f"Skipping already processed URL: {url}")
                return None

            # Only process certain domains
            parsed_url = urlparse(url)
            if any(domain in parsed_url.netloc for domain in ['fc2.com/signup', 'secure.', 'blog.fc2.com/']):
                logging.debug(f"Skipping non-content URL: {url}")
                return None

            logging.info(f"Fetching URL: {url}")
            self.processed_urls.add(url)  # Mark as processed
            response = self.session.get(url, headers=HEADERS, timeout=10)  # Add timeout
            response.raise_for_status()
            return response.text
        except Exception as e:
            logging.error(f"Error fetching {url}: {str(e)}")
            return None

    def extract_coords_from_url(self, url: str) -> tuple:
        """
        Extract coordinates from a Google Maps URL using various patterns
        """
        try:
            # Decode URL-encoded characters
            decoded_url = unquote(url)
            logging.debug(f"Decoded URL: {decoded_url}")

            # Try different coordinate patterns
            patterns = [
                # Embed format with coordinates in query parameters
                (r'!1d([-\d.]+)!2d([-\d.]+)', False),  # (lat, lon)
                (r'@([-\d.]+),([-\d.]+)', False),     # Standard format (lat, lon)
                (r'!3d([-\d.]+)!4d([-\d.]+)', False), # Data parameter format
                (r'll=([-\d.]+),([-\d.]+)', False),   # ll parameter
                (r'q=([-\d.]+),([-\d.]+)', False),    # query parameter
            ]

            for pattern, swap_coords in patterns:
                match = re.search(pattern, decoded_url)
                if match:
                    try:
                        val1 = float(match.group(1))
                        val2 = float(match.group(2))
                        lat, lon = (val2, val1) if swap_coords else (val1, val2)
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            logging.info(f"Found coordinates: {lat}, {lon}")
                            return (lat, lon)
                    except ValueError:
                        continue

            logging.debug(f"No coordinates found in URL: {decoded_url}")
            return None

        except Exception as e:
            logging.error(f"Error extracting coordinates from URL: {str(e)}")
            return None

    def find_coordinates_in_section(self, section: BeautifulSoup) -> tuple:
        """
        Find coordinates in a specific section using various methods
        """
        # Log the section HTML for debugging
        logging.debug(f"Analyzing section HTML: {section.prettify()}")

        # Check for <gmap-frame> tags first (custom element for map embeds)
        gmap_frames = section.find_all('gmap-frame')
        for frame in gmap_frames:
            # Try both :links and links attributes
            links_attr = frame.get(':links') or frame.get('links', '')
            if links_attr:
                try:
                    # Handle JSON string format
                    links_str = links_attr.replace('\\"', '"').strip('\'')
                    if links_str.startswith('['):
                        # Parse as JSON array
                        map_urls = json.loads(links_str)
                    else:
                        # Single URL
                        map_urls = [links_str]

                    for url in map_urls:
                        if 'google.com/maps' in url:
                            logging.info(f"Found Google Maps URL in gmap-frame: {url}")
                            coords = self.extract_coords_from_url(url)
                            if coords:
                                logging.info(f"Successfully extracted coordinates: {coords}")
                                return coords
                except json.JSONDecodeError as e:
                    logging.error(f"Error parsing JSON from links attribute: {e}")
                    # Try simple string splitting as fallback
                    cleaned_links = links_attr.strip('[]\'\"')
                    map_urls = [url.strip() for url in cleaned_links.split(',')]
                    for url in map_urls:
                        if 'google.com/maps' in url:
                            logging.info(f"Found Google Maps URL in gmap-frame (fallback): {url}")
                            coords = self.extract_coords_from_url(url)
                            if coords:
                                logging.info(f"Successfully extracted coordinates: {coords}")
                                return coords

        # Check for regular Google Maps links
        for link in section.find_all('a', href=True):
            href = link['href']
            if 'google.com/maps' in href:
                logging.info(f"Found Google Maps link: {href}")
                coords = self.extract_coords_from_url(href)
                if coords:
                    return coords

        # Check for regular iframes
        for iframe in section.find_all('iframe'):
            src = iframe.get('src', '')
            if 'google.com/maps' in src:
                logging.info(f"Found Google Maps iframe: {src}")
                coords = self.extract_coords_from_url(src)
                if coords:
                    return coords

        return None

    def find_coordinates(self, soup: BeautifulSoup, location_name: str) -> tuple:
        """
        Find coordinates in sections containing location name and ストリートビュー
        """
        # Extract the main name part before any descriptive text
        base_name = location_name.split('は')[0].strip()
        if len(base_name) > 10:
            base_name = base_name[:10]  # Use first part of name to match

        # First try to find the specific Street View and aerial photos section
        for section in soup.find_all(['div', 'section', 'p']):
            if "ストリートビュー・空中写真" in section.get_text():
                logging.info(f"Found Street View and aerial photos section")
                coords = self.find_coordinates_in_section(section)
                if coords:
                    return coords

        # If not found, try sections containing both location name and Street View
        for section in soup.find_all(['div', 'section', 'p']):
            text = section.get_text()
            if base_name in text and "ストリートビュー" in text:
                logging.info(f"Found section with location name and Street View for: {base_name}")
                coords = self.find_coordinates_in_section(section)
                if coords:
                    return coords

        # Try blog posts as a last resort
        blog_posts_checked = 0
        for link in soup.find_all('a', href=True):
            href = link['href']
            if blog_posts_checked >= 3:  # Limit to 3 blog posts
                break

            # Check if this is a relevant blog post link
            if (any(keyword in href for keyword in ['記事', 'blog', 'entry']) and 
                href not in self.processed_urls):  # Skip already processed URLs

                blog_posts_checked += 1
                logging.info(f"Checking blog post ({blog_posts_checked}/3): {href}")

                blog_html = self.fetch_page(urljoin(BASE_URL, href))
                if blog_html:
                    blog_soup = BeautifulSoup(blog_html, 'html.parser')
                    # Look for Street View section in blog post
                    for section in blog_soup.find_all(['div', 'section', 'p']):
                        if "ストリートビュー" in section.get_text():
                            coords = self.find_coordinates_in_section(section)
                            if coords:
                                return coords

        return None

    def get_location_name(self, soup: BeautifulSoup) -> str:
        """
        Extract location name from the page
        """
        # Try article title first
        for title_elem in soup.find_all(['h1', 'h2', 'h3']):
            if title_elem.text.strip():
                name = title_elem.text.split('は')[0].strip()
                return name

        # Try meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            name = meta_title['content'].split('は')[0].strip()
            return name

        # Try page title
        title = soup.find('title')
        if title and title.text:
            name = title.text.split('は')[0].strip()
            return name

        return "不明な場所"

    def translate_name(self, name: str) -> str:
        """
        Translate Japanese text to English with caching
        """
        if name in self.translation_cache:
            return self.translation_cache[name]

        try:
            translation = self.translator.translate(name, src='ja', dest='en')
            if translation and translation.text:
                translated_text = translation.text.strip()
                self.translation_cache[name] = translated_text
                return translated_text
        except Exception as e:
            logging.error(f"Translation error for '{name}': {str(e)}")

        return "Unknown Location"

    def get_location_links(self, html: str) -> list:
        """
        Extract links to individual location pages
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []

        # Find all article elements that contain location links
        articles = soup.find_all('article')
        for article in articles:
            link = article.find('a', href=True)
            if link and link.get('href'):
                full_url = urljoin(BASE_URL, link['href'])
                links.append(full_url)

        logging.info(f"Found {len(links)} location links")
        return links

    def extract_main_image(self, soup: BeautifulSoup) -> str:
        """
        Extract the URL of the main image from the location page
        """
        # Try to find the main image in various ways
        # First check for large images in the header or main content
        for img in soup.find_all('img', class_=lambda c: c and ('main' in c or 'header' in c or 'hero' in c)):
            if img.get('src'):
                img_url = img['src']
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(BASE_URL, img_url)
                logging.info(f"Found main image: {img_url}")
                return img_url
                
        # Try the first large image
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and not src.endswith(('.gif', '.svg', '.ico')) and not 'icon' in src.lower():
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(BASE_URL, src)
                logging.info(f"Using first image: {src}")
                return src
                
        # If no suitable image found
        return None
    
    def scrape_location(self, url: str) -> dict:
        """
        Scrape a single location page
        """
        html = self.fetch_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Get the name of the location
        ja_name = self.get_location_name(soup)
        en_name = self.translate_name(ja_name)

        # Find coordinates
        coordinates = self.find_coordinates(soup, ja_name)
        
        # Extract main image
        image_url = self.extract_main_image(soup)

        return {
            'ja': ja_name,
            'en': en_name,
            'coordinates': coordinates,
            'image_url': image_url,
            'url': url  # Include the original URL
        }

    def generate_text_file(self, locations: list, filename: str = DEFAULT_TEXT_FILENAME):
        """
        Generate text file with location names, coordinates and image URLs in user-friendly format
        """
        try:
            logging.info(f"Generating text file with {len(locations)} locations")

            with open(filename, 'w', encoding='utf-8') as f:
                f.write("廃墟・廃遊園地・廃ホテル\n")
                f.write("Abandoned Places, Theme Parks, and Hotels\n")
                f.write("====================\n\n")

                for i, location in enumerate(locations, 1):
                    f.write(f"{i}. {location['ja']}\n")
                    f.write(f"   {location['en']}\n")
                    if location.get('coordinates'):
                        lat, lon = location['coordinates']
                        f.write(f"   Coordinates: {lat:.6f}, {lon:.6f}\n")
                    if location.get('image_url'):
                        f.write(f"   Image: {location['image_url']}\n")
                    if location.get('url'):
                        f.write(f"   Source: {location['url']}\n")
                    f.write("\n")

                f.write("\nNote: 日本の興味深い廃墟スポット\n")
                f.write("Note: Interesting abandoned locations in Japan\n")
                f.write("新しい場所は定期的に追加されます。\n")
                f.write("New locations are added regularly.\n")

            logging.info(f"Text file saved successfully as {filename}")

        except Exception as e:
            logging.error(f"Error saving text file: {str(e)}")
            raise

    def scrape_locations(self):
        """
        Main function to scrape locations and generate output files
        """
        try:
            logging.info("Starting location scraping from haikyo.info")

            # Fetch the main page
            html_content = self.fetch_page(BASE_URL)
            if not html_content:
                logging.error("Failed to fetch main page")
                return

            # Get links to individual location pages
            location_links = self.get_location_links(html_content)

            # Visit each location page and extract information
            locations = []
            for link in location_links[:5]:  # Limit to 5 locations
                location = self.scrape_location(link)
                if location:
                    locations.append(location)
                    if location.get('coordinates'):
                        logging.info(f"Found location: {location['ja']} at {location['coordinates']}")
                    else:
                        logging.info(f"Found location: {location['ja']} (no coordinates)")

            if not locations:
                logging.warning("No locations found")
                return

            # Generate output files
            self.generate_text_file(locations)

            logging.info("Scraping completed successfully")

        except Exception as e:
            logging.error(f"Scraping failed: {str(e)}")
            raise

def main():
    scraper = HaikyoScraper()
    try:
        scraper.scrape_locations()
    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()