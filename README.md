# Simania Book Scraper

A comprehensive Python project for scraping book data from Simania's used book marketplace. The project includes two main scrapers that extract different types of data from the Simania website.

## Project Structure

```
simania/
├── src/                           # Source code directory
│   ├── simania_user_books_scraper.py  # Scraper for user-specific book listings
│   └── books_scraper.py               # Scraper for book details and seller information
├── data/                          # Data output directory
│   ├── user-books/                # User-specific book listings
│   │   ├── simania_books_user_162798.csv
│   │   └── simania_books_user_104283.csv
│   ├── books.csv                  # Book details
│   └── sellers.csv                # Seller information
├── logs/                          # Log files
│   ├── scraper.log               # User books scraper logs
│   └── books_scraper.log         # Books scraper logs
├── venv/                         # Python virtual environment
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## Setup

1. Create virtual environment:

```bash
python -m venv venv
```

2. Activate virtual environment:

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Generate requirements.txt (after adding new packages):

```bash
pip freeze > requirements.txt
```

## Dependencies

- `requests`: HTTP library for making web requests
- `beautifulsoup4`: HTML parsing library with lxml backend
- `pandas`: Data manipulation and CSV export
- `lxml`: XML/HTML parser backend for BeautifulSoup
- `numpy`: Numerical computing library (pandas dependency)

## Scrapers

### 1. User Books Scraper (`simania_user_books_scraper.py`)

Scrapes book listings from user-specific pages on Simania.

**Features:**

- Iterates through multiple pages of user book listings
- Extracts book details: title, author, condition, price, book ID
- Filters out records with empty titles
- Supports multiple user IDs
- Configurable page limits for testing

**Usage:**

```bash
python src/simania_user_books_scraper.py
```

**Output:** CSV files in `data/user-books/` directory with format:

- `simania_books_user_{user_id}.csv`

**CSV Fields:**

- `book_id`: Unique book identifier
- `title`: Book title
- `author`: Book author
- `condition`: Book condition (Hebrew)
- `price`: Book price
- `book_url`: Direct link to book details page

### 2. Books Scraper (`books_scraper.py`)

Scrapes detailed book information and seller data from individual book detail pages.

**Features:**

- Extracts comprehensive book details
- Finds seller information embedded in JSON data
- Handles Hebrew text encoding
- Creates separate CSV files for books and sellers
- Supports category hierarchy (up to 5 levels)

**Usage:**

```bash
python src/books_scraper.py
```

**Output:** Two CSV files in `data/` directory:

- `books.csv`: Book details
- `sellers.csv`: Seller information

**Books CSV Fields:**

- `book_id`: Unique book identifier
- `title`: Book title
- `author`: Book author
- `series`: Book series (if applicable)
- `publisher`: Publisher name
- `year`: Publication year
- `pages`: Number of pages
- `category_1` to `category_5`: Category hierarchy levels
- `category_full`: Full category path (e.g., "נוער » קלאסיקה")
- `book_url`: Direct link to book details page

**Sellers CSV Fields:**

- `seller_id`: Unique seller identifier (book_id + user_id)
- `book_id`: Associated book identifier
- `condition`: Book condition (if available)
- `price`: Book price (if available)
- `seller_url`: Link to seller's profile page
- `last_updated`: Date when data was scraped

## Data Sources

### User Books Scraper

- **URL Pattern:** `https://simania.co.il/user_books_for_sale.php?page_num={page}&userId={user_id}`
- **Example:** `https://simania.co.il/user_books_for_sale.php?page_num=37&userId=162798`

### Books Scraper

- **URL Pattern:** `https://simania.co.il/bookdetails.php?item_id={book_id}`
- **Example:** `https://simania.co.il/bookdetails.php?item_id=78021`

## Technical Details

### Seller Data Extraction

The books scraper uses advanced techniques to extract seller information:

1. **JSON Data Parsing:** Seller data is embedded as JSON in the HTML page source
2. **Regex Pattern Matching:** Uses regex to find and parse the `privateSellers` array
3. **Field Extraction:** Extracts individual seller fields (userId, userName, userImage, etc.)
4. **Fallback Methods:** Includes fallback HTML parsing if JSON data is not found

### Hebrew Text Support

- All scrapers properly handle Hebrew text encoding (UTF-8)
- CSV files are saved with UTF-8 encoding
- Logging supports Hebrew characters

### Error Handling

- Retry logic for failed HTTP requests
- Graceful handling of missing data
- Comprehensive logging to both file and console
- Exponential backoff for rate limiting

## Configuration

### User Books Scraper Configuration

Edit the `main()` function in `simania_user_books_scraper.py`:

```python
user_ids = [162798, 104283]  # List of user IDs to scrape
max_pages = 5  # Limit pages for testing, set to None for all pages
```

### Books Scraper Configuration

Edit the `main()` function in `books_scraper.py`:

```python
book_ids = [78021]  # List of book IDs to scrape
```

## Logging

Both scrapers create detailed logs in the `logs/` directory:

- `scraper.log`: User books scraper logs
- `books_scraper.log`: Books scraper logs

Logs include:

- Processing status for each page/book
- Error messages and warnings
- Data extraction statistics
- Performance metrics

## Example Results

### User Books Scraper

Successfully scraped 2 users with multiple pages each, extracting hundreds of book listings.

### Books Scraper

Successfully extracted:

- **Book Details:** Complete information including title, author, series, publisher, year, pages, and category hierarchy
- **Seller Information:** 14 sellers found for book ID 78021 ("טרזן הכובש הפרא - טרזן #8")

## Future Enhancements

- Add price and condition extraction for sellers
- Implement dynamic seller data loading (handle "Show More" functionality)
- Add support for additional book detail fields
- Implement database storage option
- Add data validation and cleaning
- Create data analysis and visualization tools

## Notes

- The project respects Simania's servers with appropriate delays between requests
- All data is stored in CSV format for easy analysis
- The scrapers are designed to be robust and handle various edge cases
- Hebrew text is properly encoded and displayed in CSV files
