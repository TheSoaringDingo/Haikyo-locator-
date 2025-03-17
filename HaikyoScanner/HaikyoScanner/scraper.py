"""
Scraper module for HaikyoLocator.
Handles web scraping from haikyo.info.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class Scraper:
    """A class to scrape haikyo (abandoned places) information from haikyo.info."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.base_url = "https://haikyo.info"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8'
        }
    
    def _make_request(self, url):
        """Make a request to the given URL and return the BeautifulSoup object."""
        try:
            # Add timeout to prevent hanging
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Warning: Error making request to {url}: {str(e)}")
            raise Exception(f"Error making request to {url}: {str(e)}")
    
    def _is_search_url(self, url):
        """Check if the URL is a search URL."""
        parsed_url = urlparse(url)
        # Original search path
        if parsed_url.netloc == 'haikyo.info' and parsed_url.path == '/search.php':
            return True
        # Category or prefecture listing pages
        if parsed_url.netloc == 'haikyo.info' and (
            parsed_url.path.startswith('/list') or
            parsed_url.path.startswith('/a/') or
            parsed_url.path.startswith('/list.php')
        ):
            return True
        # Main page is also treated as a search page (has listings)
        if parsed_url.netloc == 'haikyo.info' and parsed_url.path == '/':
            return True
        return False
    
    def _extract_location_cards(self, soup):
        """Extract location cards from search results page."""
        # Find all spot_panel articles (primary structure on haikyo.info as of 2025)
        cards = soup.find_all('article', class_='spot_panel')
        if cards:
            return cards
            
        # Try to extract JavaScript data from scripts
        script_data = []
        for script in soup.find_all('script'):
            script_text = script.string
            if script_text:
                # Look for location data in site's JavaScript
                if 'spotList' in script_text or 'spot_list' in script_text:
                    # Try to extract spot data
                    # Pattern for new format /s/ID.html
                    pattern = r'"/s/(\d+)\.html".*?"([^"]+)"'
                    matches = re.findall(pattern, script_text)
                    for spot_id, title in matches:
                        script_data.append({
                            'id': spot_id,
                            'title': title,
                            'url': f"https://haikyo.info/s/{spot_id}.html"
                        })
        
        if script_data:
            return script_data
            
        # Traditional approach - find elements by class or pattern
        if not cards:
            cards = soup.select('.entry, .post, article, .card, .item')
        
        # If no standard card found, try to find links that look like location entries
        if not cards:
            cards = soup.find_all('a', href=re.compile(r'/s/\d+\.html'))
            
        # Also check for older pattern
        if not cards:
            cards = soup.find_all('a', href=re.compile(r'/explorer/\d+/'))
            
        return cards
    
    def _extract_location_data(self, card, enrich_data=True):
        """
        Extract data from a location card.
        
        Args:
            card: The BeautifulSoup element or dictionary containing location data
            enrich_data: Whether to fetch additional data from the detail page
            
        Returns:
            dict: Location data
        """
        location = {
            'id': "",
            'name': "",
            'image_url': "",
            'url': "",
            'description': "",
            'address': "",
            'prefecture': "",
            'category': ""
        }
        
        # Check if card is already a dictionary (from script data extraction)
        if isinstance(card, dict):
            location['id'] = card.get('id', "")
            location['name'] = card.get('title', "")
            location['url'] = card.get('url', "")
            # If we have a URL to the detail page and enrich_data is True, scrape more information
            if enrich_data and location['url']:
                try:
                    self._enrich_location_data(location)
                except Exception as e:
                    print(f"Error enriching data for {location['name']}: {str(e)}")
            return location
            
        # For the modern spot_panel format, use the dedicated method
        if hasattr(card, 'get') and card.get('class') and 'spot_panel' in card.get('class'):
            return self._extract_spot_panel_data(card, enrich_data)
            
        # Generic extraction for other card types
        # Try to find the link to the detail page (handle various formats)
        link = None
        if hasattr(card, 'find'):
            # First try the current format (/s/ID.html)
            link = card.find('a', href=re.compile(r'/s/\d+\.html'))
            
            # If not found, try the older format (/explorer/ID/)
            if not link:
                link = card.find('a', href=re.compile(r'/explorer/\d+/'))
        
        # If card is an 'a' tag itself
        if not link and hasattr(card, 'name') and card.name == 'a':
            # Check all possible URL patterns
            if (card.get('href') and 
                (re.search(r'/s/\d+\.html', card.get('href', '')) or 
                 re.search(r'/explorer/\d+/', card.get('href', '')))):
                link = card
            
        if link:
            location['url'] = urljoin(self.base_url, link.get('href', ''))
            
            # Extract ID from URL based on format
            match = re.search(r'/s/(\d+)\.html', location['url']) or re.search(r'/explorer/(\d+)/', location['url'])
            if match:
                location['id'] = match.group(1)
        
        # Try to extract name from various elements
        if not location.get('name') and hasattr(card, 'find'):
            title_element = card.find(['h2', 'h3', 'h4']) or card.find(class_=['title', 'name', 'sp_spot_name']) or link
            
            if title_element and hasattr(title_element, 'get_text'):
                location['name'] = title_element.get_text(strip=True)
        
        # Try to find an image
        if not location.get('image_url') and hasattr(card, 'find'):
            # Try modern v-lazy-image first
            img = card.find('v-lazy-image')
            if img and img.get('src'):
                location['image_url'] = urljoin(self.base_url, img.get('src'))
            else:
                # Fall back to standard img tag
                img = card.find('img')
                if img and img.get('src'):
                    location['image_url'] = urljoin(self.base_url, img.get('src'))
        
        # Try to extract description
        if not location.get('description') and hasattr(card, 'find'):
            descr = card.find(class_=['sp_spot_descr', 'description', 'content'])
            if descr:
                location['description'] = descr.get_text(strip=True)
        
        # If we have a URL to the detail page, scrape more information if needed
        if enrich_data and location['url'] and (not location.get('address') or not location.get('prefecture')):
            try:
                self._enrich_location_data(location)
            except Exception as e:
                print(f"Error enriching data for {location['name'] or location['id']}: {str(e)}")
        
        return location
    
    def _enrich_location_data(self, location):
        """Get additional data from the location's detail page."""
        detail_soup = self._make_request(location['url'])
        
        # Try to extract address
        address_element = detail_soup.find(string=re.compile(r'住所|Address', re.IGNORECASE))
        if address_element and hasattr(address_element, 'parent'):
            parent = address_element.parent
            # Look for the address text in nearby elements
            if parent and hasattr(parent, 'find_next'):
                next_element = parent.find_next(['p', 'div', 'span'])
                if next_element:
                    location['address'] = next_element.get_text(strip=True)
        
        # Direct meta information extraction
        meta_info = detail_soup.find('meta', attrs={'name': 'description'})
        if meta_info and meta_info.get('content'):
            meta_content = meta_info.get('content')
            # Extract address from meta description
            address_match = re.search(r'所在地：([^。]+)', meta_content)
            if address_match and not location.get('address'):
                location['address'] = address_match.group(1).strip()
                
            # Extract description if not already found
            if not location.get('description'):
                location['description'] = meta_content[:200] + '...' if len(meta_content) > 200 else meta_content
        
        # Try to find address in structured data
        script_elements = detail_soup.find_all('script', attrs={'type': 'application/ld+json'})
        for script in script_elements:
            if script.string:
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict):
                        # Extract address from JSON-LD
                        if 'address' in json_data and not location.get('address'):
                            location['address'] = json_data['address'].get('addressRegion', '') + json_data['address'].get('addressLocality', '')
                        
                        # Extract name if missing
                        if 'name' in json_data and not location.get('name'):
                            location['name'] = json_data['name']
                            
                        # Extract image if missing
                        if 'image' in json_data and not location.get('image_url'):
                            image_url = json_data['image']
                            if isinstance(image_url, list) and len(image_url) > 0:
                                location['image_url'] = image_url[0]
                            elif isinstance(image_url, str):
                                location['image_url'] = image_url
                except:
                    pass
        
        # If address not found, try different approach
        if not location.get('address'):
            for element in detail_soup.find_all(['p', 'div', 'span']):
                text = element.get_text(strip=True)
                if '県' in text and ('市' in text or '町' in text or '村' in text):
                    location['address'] = text
                    break
        
        # Try to extract prefecture
        if location.get('address'):
            prefecture_match = re.search(r'(.+?)[都道府県]', location['address'])
            if prefecture_match:
                location['prefecture'] = prefecture_match.group(0)
        
        # Try to extract category
        category_element = detail_soup.find(string=re.compile(r'カテゴリ|Category', re.IGNORECASE))
        if category_element and hasattr(category_element, 'parent'):
            parent = category_element.parent
            # Look for category text
            if parent and hasattr(parent, 'find_next'):
                next_element = parent.find_next(['p', 'div', 'span', 'a'])
                if next_element:
                    location['category'] = next_element.get_text(strip=True)
        
        # Also try to find category in meta keywords
        if not location.get('category'):
            keywords = detail_soup.find('meta', attrs={'name': 'keywords'})
            if keywords and keywords.get('content'):
                keyword_list = keywords.get('content').split(',')
                if len(keyword_list) > 0:
                    location['category'] = keyword_list[0].strip()
        
        # Extract a description if not already found
        if not location.get('description'):
            description_candidates = detail_soup.find_all(['p', 'div.content', 'div.description'])
            for candidate in description_candidates:
                text = candidate.get_text(strip=True)
                if len(text) > 50 and not re.match(r'^(https?:|www\.|住所|Address|カテゴリ|Category)', text):
                    location['description'] = text[:200] + '...' if len(text) > 200 else text
                    break
                    
        # If we still don't have a name, try to extract from title
        if not location.get('name'):
            title_element = detail_soup.find('title')
            if title_element:
                title_text = title_element.get_text(strip=True)
                # Remove site name from title
                title_text = re.sub(r'\s*[-|]\s*.*$', '', title_text)
                if title_text:
                    location['name'] = title_text
    
    def _get_next_page_url(self, soup, current_url):
        """Get the URL of the next page if pagination exists."""
        next_link = soup.find('a', string=re.compile(r'次へ|Next', re.IGNORECASE)) or \
                   soup.find('a', attrs={'rel': 'next'})
        
        if next_link and next_link.get('href'):
            return urljoin(current_url, next_link['href'])
        return None
    
    def scrape_locations(self, url, max_pages=5, enrich_data=True):
        """
        Scrape location data from the given URL.
        
        Args:
            url (str): The URL to scrape. Can be a search URL or direct URL to a location.
            max_pages (int): Maximum number of pages to scrape if pagination exists.
            enrich_data (bool): Whether to scrape additional data from each location's detail page.
                                Setting to False improves performance but returns less detailed data.
            
        Returns:
            list: A list of dictionaries containing location data.
        """
        # Check if URL is valid
        if not url.startswith('http'):
            url = f"https://{url}"
        
        if not url.startswith('https://haikyo.info'):
            raise ValueError("URL must be from haikyo.info")
        
        # Check if this is a search URL or a direct location URL
        if self._is_search_url(url):
            return self._scrape_search_results(url, max_pages, enrich_data)
        else:
            # Assume it's a direct location URL
            location = {'url': url}
            if enrich_data:
                self._enrich_location_data(location)
            else:
                # If not enriching, try to at least extract basic info from the URL
                match = re.search(r'/s/(\d+)\.html', url)
                if match:
                    location['id'] = match.group(1)
            return [location] if enrich_data and location.get('name') else [location]
    
    def _scrape_search_results(self, url, max_pages=5, enrich_data=True):
        """
        Scrape location data from search results.
        
        Args:
            url (str): The URL to scrape
            max_pages (int): Maximum number of pages to scrape
            enrich_data (bool): Whether to fetch additional data from each location's detail page
        
        Returns:
            list: A list of location dictionaries
        """
        all_locations = []
        current_url = url
        page_count = 0
        
        while current_url and page_count < max_pages:
            soup = self._make_request(current_url)
            cards = self._extract_location_cards(soup)
            
            for card in cards:
                # Extract basic data
                if isinstance(card, dict):
                    # This is pre-processed data from script extraction
                    location = {
                        'id': card.get('id', ""),
                        'name': card.get('title', ""),
                        'url': card.get('url', ""),
                        'image_url': card.get('image_url', ""),
                        'description': card.get('description', ""),
                        'address': "",
                        'prefecture': "",
                        'category': ""
                    }
                # Spot panel format (current structure)
                elif hasattr(card, 'get') and card.get('class') and 'spot_panel' in card.get('class'):
                    location = self._extract_spot_panel_data(card, enrich_data)
                else:
                    # Fall back to generic extraction
                    location = self._extract_location_data(card, enrich_data)
                
                # Only add if we got at least a name or ID
                if location.get('name') or location.get('id'):
                    all_locations.append(location)
            
            # Check for next page
            next_url = self._get_next_page_url(soup, current_url)
            if next_url == current_url:  # Avoid infinite loop
                break
            
            current_url = next_url
            page_count += 1
        
        return all_locations
        
    def _extract_spot_panel_data(self, card, enrich_data=True):
        """
        Extract data from a spot_panel element (current haikyo.info format).
        
        Args:
            card: The BeautifulSoup element containing the spot panel
            enrich_data: Whether to fetch additional data from the detail page
            
        Returns:
            dict: Location data
        """
        location = {
            'id': "",
            'name': "",
            'image_url': "",
            'url': "",
            'description': "",
            'address': "",
            'prefecture': "",
            'category': ""
        }
        
        # Get the main link (contains URL and image)
        main_link = card.find('a', class_='sp_a')
        if main_link:
            location['url'] = urljoin(self.base_url, main_link.get('href', ''))
            
            # Extract ID from URL (format: /s/1234.html)
            match = re.search(r'/s/(\d+)\.html', location['url'])
            if match:
                location['id'] = match.group(1)
            
            # Extract name from spot_name
            name_element = main_link.find('h4', class_='sp_spot_name')
            if name_element:
                location['name'] = name_element.get_text(strip=True)
            
            # Extract description
            descr_element = main_link.find(class_='sp_spot_descr')
            if descr_element:
                location['description'] = descr_element.get_text(strip=True)
            
            # Extract image URL
            img_element = main_link.find('v-lazy-image')
            if img_element and img_element.get('src'):
                location['image_url'] = urljoin(self.base_url, img_element.get('src'))
            
            # Extract category and prefecture
            cat_div = card.find('div', class_='sp_spot_cat')
            if cat_div:
                category_links = cat_div.find_all('a')
                if len(category_links) > 0 and category_links[0].has_attr('href') and category_links[0]['href'].startswith('/list.php?k='):
                    location['category'] = category_links[0].get_text(strip=True)
                if len(category_links) > 1 and category_links[1].has_attr('href') and category_links[1]['href'].startswith('/a/'):
                    location['prefecture'] = category_links[1].get_text(strip=True)
        
        # If we need to get full address and enrich_data is True, scrape the detail page
        if enrich_data and location['url'] and not location.get('address'):
            try:
                self._enrich_location_data(location)
            except Exception as e:
                print(f"Error enriching data for {location['name']}: {str(e)}")
            
        return location
