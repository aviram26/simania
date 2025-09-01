#!/usr/bin/env python3
"""
Simania Book Scraper
Scrapes used books for sale from Simania marketplace for specified user IDs.
"""

import requests
import csv
import time
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class SimaniaScraper:
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
    
    def parse_book_table(self, soup):
        """Extract book data from the table"""
        books = []
        table = soup.select_one('.table1')
        
        if not table:
            logging.warning("No table found on page")
            return books
            
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                try:
                    # Extract book title and link
                    title_cell = cells[0]
                    title_link = title_cell.find('a')
                    title = title_link.get_text(strip=True) if title_link else title_cell.get_text(strip=True)
                    book_url = urljoin(self.base_url, title_link['href']) if title_link else ''
                    
                    # Extract author name and link
                    author_cell = cells[1]
                    author_link = author_cell.find('a')
                    author = author_link.get_text(strip=True) if author_link else author_cell.get_text(strip=True)
                    author_url = urljoin(self.base_url, author_link['href']) if author_link else ''
                    
                    # Extract book condition
                    condition = cells[2].get_text(strip=True)
                    
                    # Extract price and clean it
                    price_cell = cells[3]
                    price_text = price_cell.get_text(strip=True)
                    # Remove "הוסף לסל" (Add to Cart) text and extract just the price
                    price = price_text.split('הוסף')[0].strip() if 'הוסף' in price_text else price_text
                    
                    # Extract book ID from URL if available
                    book_id = ''
                    if book_url:
                        parsed_url = urlparse(book_url)
                        query_params = parse_qs(parsed_url.query)
                        book_id = query_params.get('item_id', [''])[0]
                    
                    # Skip rows with missing essential data
                    if not title or not author:
                        logging.warning(f"Skipping row with missing title or author: title='{title}', author='{author}'")
                        continue
                    
                    books.append({
                        'book_id': book_id,
                        'title': title,
                        'author': author,
                        'condition': condition,
                        'price': price,
                        'book_url': book_url,
                        'author_url': author_url
                    })
                    
                except Exception as e:
                    logging.error(f"Error parsing row: {e}")
                    continue
                    
        return books
    
    def scrape_user_books(self, user_id, max_pages=None, output_file=None):
        """Scrape all books for a specific user"""
        if output_file is None:
            output_file = f"simania_books_user_{user_id}.csv"
            
        all_books = []
        page_num = 1
        total_pages = 0
        
        logging.info(f"Starting to scrape books for user {user_id}")
        
        # If max_pages is None, scrape all pages (infinity)
        if max_pages is None:
            logging.info("No page limit set - will scrape all available pages")
        
        while max_pages is None or page_num <= max_pages:
            url = f"{self.base_url}/user_books_for_sale.php?page_num={page_num}&search[displayType]=&search[orderBy]=authorLastName&userId={user_id}"
            logging.info(f"Scraping page {page_num}: {url}")
            
            response = self.get_page(url)
            if not response:
                logging.error(f"Failed to fetch page {page_num}")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if we've reached the end (no more results)
            books = self.parse_book_table(soup)
            if not books:
                logging.info(f"No more books found on page {page_num}. Stopping.")
                break
            
            all_books.extend(books)
            logging.info(f"Found {len(books)} books on page {page_num}")
            
            # Check if this is the last page by looking for pagination
            pagination = soup.select('.pagination input[type="submit"]')
            if pagination:
                # Find the highest page number
                page_numbers = []
                for input_elem in pagination:
                    try:
                        page_numbers.append(int(input_elem.get('value', 0)))
                    except ValueError:
                        continue
                
                if page_numbers:
                    total_pages = max(page_numbers)
                    logging.info(f"Total pages detected: {total_pages}")
            
            # Add delay to be respectful to the server
            time.sleep(1)
            page_num += 1
            
            if max_pages is not None:
                logging.info(f"Completed page {page_num-1}/{max_pages}")
            else:
                logging.info(f"Completed page {page_num-1}")
            
            # Safety check to prevent infinite loops (only when scraping all pages)
            if max_pages is None and page_num > 10000:
                logging.warning("Reached safety limit of 10000 pages. Stopping.")
                break
        
        # Filter out records with empty title before saving
        filtered_books = [book for book in all_books if book.get('title', '').strip()]
        logging.info(f"Filtered {len(all_books)} books down to {len(filtered_books)} books with valid titles")
        
        # Save to CSV
        if filtered_books:
            self.save_to_csv(filtered_books, output_file)
            logging.info(f"Successfully scraped {len(filtered_books)} books. Saved to {output_file}")
        else:
            logging.warning(f"No books found for user {user_id}")
            
        return filtered_books
    
    def save_to_csv(self, books, filename):
        """Save books data to CSV file"""
        if not books:
            return
            
        fieldnames = ['book_id', 'title', 'author', 'condition', 'price', 'book_url', 'author_url']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(books)
    
    def scrape_multiple_users(self, user_ids, max_pages=None):
        """Scrape books for multiple users"""
        all_books = []
        
        for user_id in user_ids:
            logging.info(f"Processing user {user_id}")
            user_books = self.scrape_user_books(user_id, max_pages, f"simania_books_user_{user_id}.csv")
            all_books.extend(user_books)
            
            # Add delay between users
            time.sleep(2)
        
        return all_books

def main():
    """Main function"""
    # User IDs to scrape
    user_ids = [162798, 104283]
    
    # Number of pages to scrape (None = all pages, 5 = first 5 pages for testing)
    max_pages = 5  # Change to 5 for testing, None for all pages
    
    # Initialize scraper
    scraper = SimaniaScraper()
    
    try:
        # Scrape books for all users
        all_books = scraper.scrape_multiple_users(user_ids, max_pages)
        
        print(f"\nScraping completed successfully!")
        print(f"Total books scraped: {len(all_books)}")
        print(f"Individual user files created for each user")
        if max_pages:
            print(f"Limited to first {max_pages} pages per user")
        else:
            print(f"Scraped all available pages per user")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        logging.info("Scraping interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
