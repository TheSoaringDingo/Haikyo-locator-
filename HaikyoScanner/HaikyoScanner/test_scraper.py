#!/usr/bin/env python3
"""
Test script for the haikyo.info web scraper.
"""

import sys
import traceback
from scraper import Scraper

def test_search_url(url, expected_count=1):
    """Test scraping a search URL."""
    print(f"Testing search URL: {url}")
    scraper = Scraper()
    try:
        # For testing, set max_pages=1 and disable full enrichment to avoid excessive requests
        locations = scraper.scrape_locations(url, max_pages=1, enrich_data=False)
        print(f"Found {len(locations)} locations")
        
        # Display sample data from first result
        if locations:
            first_location = locations[0]
            print("Sample location data:")
            for key, value in first_location.items():
                if value:  # Only print non-empty values
                    print(f"  {key}: {value[:100] if isinstance(value, str) and len(value) > 100 else value}")
        
        if len(locations) >= expected_count:
            print("Test PASSED ✓")
            return True
        else:
            print(f"Test FAILED ✗ - Expected at least {expected_count} locations, got {len(locations)}")
            return False
    except Exception as e:
        print(f"Test FAILED ✗ - Error: {str(e)}")
        traceback.print_exc()
        return False

def test_location_url(url):
    """Test scraping a direct location URL."""
    print(f"Testing location URL: {url}")
    scraper = Scraper()
    try:
        locations = scraper.scrape_locations(url)
        if not locations:
            print("Test FAILED ✗ - No location data returned")
            return False
            
        location = locations[0]
        print("Location data:")
        for key, value in location.items():
            if value:  # Only print non-empty values
                print(f"  {key}: {value}")
        
        # Check if we got essential information
        if location.get('name') and location.get('url'):
            print("Test PASSED ✓")
            return True
        else:
            print("Test FAILED ✗ - Missing essential data (name or URL)")
            return False
    except Exception as e:
        print(f"Test FAILED ✗ - Error: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run tests for the scraper."""
    tests_passed = 0
    tests_total = 0
    
    # Test search URLs
    print("\n=== Testing Search URLs ===")
    search_tests = [
        ("https://haikyo.info/search.php?sw=神戸", 1),
        ("https://haikyo.info/a/13.html", 1),  # Tokyo prefecture listing
        ("https://haikyo.info/list.php?k=5", 1),  # Theme park category
        ("https://haikyo.info/", 1)  # Main page
    ]
    
    for url, expected_count in search_tests:
        tests_total += 1
        if test_search_url(url, expected_count):
            tests_passed += 1
        print("")
    
    # Test direct location URLs
    print("\n=== Testing Location URLs ===")
    location_tests = [
        "https://haikyo.info/s/1283.html",  # ワンダーランドASAMUSHI
        "https://haikyo.info/s/10204.html"  # 世界平和観音堂（大澄山）
    ]
    
    for url in location_tests:
        tests_total += 1
        if test_location_url(url):
            tests_passed += 1
        print("")
    
    # Print summary
    print(f"\n=== Summary: {tests_passed}/{tests_total} tests passed ===")
    return 0 if tests_passed == tests_total else 1

if __name__ == '__main__':
    sys.exit(main())