# Chile FTA Scraper

This project scrapes Free Trade Agreement (FTA) information from the Chilean Customs website (aduana.cl), with a focus on the Chile-U.S. FTA. It extracts rules of origin, amendments, and HTS codes from the agreements.

## Features

- Scrapes the Chilean Customs website to find FTA documents
- Extracts rules of origin and HTS codes from the Chile-U.S. FTA
- Stores structured data in a SQLite database
- Monitors the FTA pages for changes using Playwright
- Sends notifications when changes are detected

## Requirements

- Python 3.8+
- Dependencies listed in requirements.txt

## Installation

1. Clone this repository
2. Install requirements:
```
pip install -r requirements.txt
```
3. Install Playwright browsers:
```
playwright install
```

## Usage

### One-time Scraping

Run the main scraper to extract FTA information and set up the database:

```
python chile_fta_scraper.py
```

### Monitoring for Changes

To monitor the FTA pages for changes:

```
python monitor_changes.py --email your-email@example.com --interval 24
```

Options:
- `--email`: Email address to send notifications to (optional)
- `--interval`: Check interval in hours (default: 24)
- `--once`: Run the check once and exit (don't schedule recurring checks)

## Project Structure

- `chile_fta_scraper.py`: Main scraper script that extracts FTA data
- `monitor_changes.py`: Script to monitor FTA pages for changes
- `requirements.txt`: Python dependencies
- `chile_fta_database.db`: SQLite database storing FTA data and monitoring results
- `/screenshots`: Directory storing screenshots from monitoring runs

## Database Schema

### `fta_documents` Table
- `id`: Primary key
- `fta_name`: Name of the FTA (e.g., "Chile-US FTA")
- `document_type`: Type of document (e.g., "original_rules", "amendment")
- `document_title`: Title of the document
- `document_url`: URL of the document
- `publication_date`: Date when the document was published
- `last_checked_date`: Date when the document was last checked
- `download_path`: Local path where the document is stored

### `hts_rules` Table
- `id`: Primary key
- `fta_name`: Name of the FTA
- `hts_code`: HTS/HS code
- `hts_description`: Description of the HTS code
- `origin_rule`: Rule of origin text for this HTS code
- `document_id`: Foreign key to fta_documents table

### `website_changes` Table
- `id`: Primary key
- `url`: URL that was checked
- `check_date`: Date and time of the check
- `content_hash`: MD5 hash of the page content
- `change_detected`: 1 if a change was detected, 0 otherwise

## License

MIT
