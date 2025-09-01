#!/usr/bin/env python3
"""
Simania Books Scraper
Scrapes book details and seller information from Simania book detail pages.
Uses two CSV files: books.csv for book details, sellers.csv for seller information.
"""

import requests
import csv
import time
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import logging
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/books_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class SimaniaBooksScraper:
    def __init__(self, base_url="https://simania.co.il"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_page(self, url, retries=3):
        """Fetch a page with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'  # Ensure proper Hebrew text encoding
                return response
            except requests.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    logging.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        return None
    
    def extract_book_details(self, soup, book_id):
        """Extract book details from the page"""
        book_details = {
            'book_id': book_id,
            'title': '',
            'author': '',
            'series': '',
            'publisher': '',
            'year': '',
            'pages': '',
            'category_1': '',
            'category_2': '',
            'category_3': '',
            'category_4': '',
            'category_5': '',
            'category_full': '',
            'book_url': f"{self.base_url}/bookdetails.php?item_id={book_id}"
        }
        
        try:
            # Extract title - found in h2 with specific styling
            title_elem = soup.select_one('h2 span[style*="font-size:2em;color:#9E0B0E"]')
            if title_elem:
                book_details['title'] = title_elem.get_text(strip=True)
            
            # Extract author - found in h3 with author link
            author_elem = soup.select_one('h3 a[href*="authorDetails"]')
            if author_elem:
                book_details['author'] = author_elem.get_text(strip=True)
            
            # Extract series information - found in series link
            series_elem = soup.select_one('a[href*="searchBooks.php?searchType=tabSeries"]')
            if series_elem:
                series_text = series_elem.get_text(strip=True)
                # Clean up the series text (remove extra spaces)
                book_details['series'] = ' '.join(series_text.split())
            
            # Extract publisher - found in publisher link
            publisher_elem = soup.select_one('a[href*="publisherDetails"]')
            if publisher_elem:
                book_details['publisher'] = publisher_elem.get_text(strip=True)
            
            # Extract year, pages, and other details from the "when" div
            when_div = soup.select_one('.when')
            if when_div:
                info_text = when_div.get_text()
                
                # Extract year
                year_match = re.search(r'בשנת\s*(\d{4})', info_text)
                if year_match:
                    book_details['year'] = year_match.group(1)
                
                # Extract pages
                pages_match = re.search(r'מכיל\s*(\d+)\s*עמודים?', info_text)
                if pages_match:
                    book_details['pages'] = pages_match.group(1)
            
            # Extract categories from the "when" div
            if when_div:
                # Look for category links
                category_links = when_div.find_all('a', href=lambda x: x and 'category.php' in x)
                categories = ["", "", "", "", ""]
                
                for i, link in enumerate(category_links[:5]):  # Max 5 levels
                    if i < 5:
                        categories[i] = link.get_text(strip=True)
                
                # Create the full category string
                category_full = " » ".join([cat for cat in categories if cat])
                
                book_details['category_1'] = categories[0]
                book_details['category_2'] = categories[1]
                book_details['category_3'] = categories[2]
                book_details['category_4'] = categories[3]
                book_details['category_5'] = categories[4]
                book_details['category_full'] = category_full
            
        except Exception as e:
            logging.error(f"Error extracting book details for {book_id}: {e}")
        
        return book_details
    
    def extract_sellers(self, soup, book_id):
        """Extract seller information from the page"""
        sellers = []
        
        try:
            # The seller data is embedded as JSON in the HTML, specifically in a privateSellers array
            # Look for this embedded data in the page source
            
            # Method 1: Look for embedded JSON data containing seller information
            # The data is embedded in the HTML as a JavaScript object or data attribute
            
            # Get the raw HTML text to search for JSON patterns
            html_text = str(soup)
            
            # Look for the privateSellers array pattern
            # Pattern: "privateSellers":[{"userId":"...", "userName":"...", ...}]
            private_sellers_pattern = r'"privateSellers":\s*\[(.*?)\]'
            private_sellers_match = re.search(private_sellers_pattern, html_text, re.DOTALL)
            
            if private_sellers_match:
                logging.info(f"Found privateSellers data for book {book_id}")
                
                # Extract the JSON array content
                sellers_json_str = private_sellers_match.group(1)
                
                # The JSON might be incomplete or malformed, so let's parse it carefully
                # Look for individual seller objects
                seller_pattern = r'\{[^}]*"userId"[^}]*\}'
                seller_matches = re.findall(seller_pattern, sellers_json_str, re.DOTALL)
                
                logging.info(f"Found {len(seller_matches)} seller objects in JSON")
                
                for i, seller_json in enumerate(seller_matches):
                    try:
                        # Extract individual fields from the seller JSON
                        seller_data = {}
                        
                        # Extract userId
                        user_id_match = re.search(r'"userId":\s*"([^"]+)"', seller_json)
                        if user_id_match:
                            seller_data['userId'] = user_id_match.group(1)
                        
                        # Extract userName
                        user_name_match = re.search(r'"userName":\s*"([^"]+)"', seller_json)
                        if user_name_match:
                            seller_data['userName'] = user_name_match.group(1)
                        
                        # Extract userImage
                        user_image_match = re.search(r'"userImage":\s*"([^"]+)"', seller_json)
                        if user_image_match:
                            seller_data['userImage'] = user_image_match.group(1)
                        
                        # Extract isFemale
                        is_female_match = re.search(r'"isFemale":\s*"([^"]+)"', seller_json)
                        if is_female_match:
                            seller_data['isFemale'] = is_female_match.group(1)
                        
                        # Extract hasImage
                        has_image_match = re.search(r'"hasImage":\s*"([^"]+)"', seller_json)
                        if has_image_match:
                            seller_data['hasImage'] = has_image_match.group(1)
                        
                        # Extract frozenUser if available
                        frozen_user_match = re.search(r'"frozenUser":\s*"([^"]+)"', seller_json)
                        if frozen_user_match:
                            seller_data['frozenUser'] = frozen_user_match.group(1)
                        
                        # Create seller record
                        if seller_data.get('userId'):
                            seller = {
                                'seller_id': f"{book_id}_{seller_data['userId']}",
                                'book_id': book_id,
                                'condition': '',  # Not available in this data
                                'price': '',  # Not available in this data
                                'seller_url': f"{self.base_url}/userDetails.php?userId={seller_data['userId']}",
                                'last_updated': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            # Note: userImage is available but not included in CSV for now
                            # seller_data.get('userImage') contains the image URL
                            
                            sellers.append(seller)
                            logging.info(f"Extracted seller ID: {seller_data['userId']}")
                    
                    except Exception as e:
                        logging.warning(f"Error parsing seller {i+1}: {e}")
                        continue
            
            # Method 2: Look for any remaining seller information in HTML elements
            # This is a fallback method
            if not sellers:
                logging.info(f"No privateSellers data found, looking for HTML elements")
                
                # Look for elements that might contain seller information
                seller_elements = soup.select('[class*="seller"], [class*="user"], [class*="price"]')
                
                for elem in seller_elements:
                    elem_text = elem.get_text(strip=True)
                    if elem_text and any(keyword in elem_text for keyword in ['₪', 'ש"ח', 'מחיר', 'מצב']):
                        # This might be a seller element
                        seller = {
                            'seller_id': f"{book_id}_html_{len(sellers)+1}",
                            'book_id': book_id,
                            'condition': '',
                            'price': '',
                            'seller_url': '',
                            'last_updated': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        # Try to extract price if present
                        price_match = re.search(r'(\d+)\s*₪|(\d+)\s*ש"ח', elem_text)
                        if price_match:
                            price = price_match.group(1) or price_match.group(2)
                            seller['price'] = f"{price} ₪"
                        
                        # Try to extract condition if present
                        condition_match = re.search(r'(טוב|מצוין|חדש|ישן|בינוני|כחדש)', elem_text)
                        if condition_match:
                            seller['condition'] = condition_match.group(1)
                        
                        sellers.append(seller)
                    
        except Exception as e:
            logging.error(f"Error extracting sellers for {book_id}: {e}")
        
        return sellers
    
    def scrape_book(self, book_id):
        """Scrape a single book's details and sellers"""
        url = f"{self.base_url}/bookdetails.php?item_id={book_id}"
        logging.info(f"Scraping book {book_id}: {url}")
        
        response = self.get_page(url)
        if not response:
            logging.error(f"Failed to fetch book {book_id}")
            return None, []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract book details
        book_details = self.extract_book_details(soup, book_id)
        
        # Extract seller information
        sellers = self.extract_sellers(soup, book_id)
        
        logging.info(f"Extracted {len(sellers)} sellers for book {book_id}")
        
        return book_details, sellers
    
    def save_books_to_csv(self, books, filename):
        """Save books data to CSV file"""
        if not books:
            return
            
        fieldnames = ['book_id', 'title', 'author', 'series', 'publisher', 'year', 'pages', 
                     'category_1', 'category_2', 'category_3', 'category_4', 'category_5', 
                     'category_full', 'book_url']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(books)
    
    def save_sellers_to_csv(self, sellers, filename):
        """Save sellers data to CSV file"""
        if not sellers:
            return
            
        fieldnames = ['seller_id', 'book_id', 'condition', 'price', 'seller_url', 'last_updated']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sellers)
    
    def scrape_multiple_books(self, book_ids):
        """Scrape multiple books"""
        all_books = []
        all_sellers = []
        
        for book_id in book_ids:
            logging.info(f"Processing book {book_id}")
            
            book_details, sellers = self.scrape_book(book_id)
            
            if book_details:
                all_books.append(book_details)
                all_sellers.extend(sellers)
            
            # Add delay to be respectful to the server
            time.sleep(2)
        
        return all_books, all_sellers

def main():
    """Main function"""
    # Book IDs to scrape (example from user-books scraper)
    book_ids = [78021]  # This book has seller info: "טרזן הכובש הפרא - טרזן #8"
    
    # Initialize scraper
    scraper = SimaniaBooksScraper()
    
    try:
        # Scrape books
        books, sellers = scraper.scrape_multiple_books(book_ids)
        
        # Save to CSV files
        if books:
            scraper.save_books_to_csv(books, 'data/books.csv')
            logging.info(f"Saved {len(books)} books to data/books.csv")
        
        if sellers:
            scraper.save_sellers_to_csv(sellers, 'data/sellers.csv')
            logging.info(f"Saved {len(sellers)} sellers to data/sellers.csv")
        
        print(f"\nScraping completed successfully!")
        print(f"Total books scraped: {len(books)}")
        print(f"Total sellers found: {len(sellers)}")
        print(f"Files created: data/books.csv, data/sellers.csv")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        logging.info("Scraping interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
