# Chile FTA Scraper

This project scrapes Free Trade Agreement (FTA) information from the Chilean Customs website (aduana.cl), with a focus on the Chile-U.S. FTA. It extracts rules of origin, amendments, and HTS codes from the agreements.

## Current Status (March 2025)

The Chile-US FTA scraper has been updated to work with the current structure of the Aduana.cl website. Key changes:

1. Fixed FTA page URL which has been updated to follow the format: `https://www.aduana.cl/tratado-de-libre-comercio-chile-estados-unidos/aduana/2007-02-28/122217.html`
2. Added hardcoded fallback for key document URLs in case web scraping fails
3. Improved document handling with local caching and PDF-to-text conversion
4. Enhanced error handling throughout the application

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
```
git clone https://github.com/agentbryce2025/fta_scraper_test.git
cd fta_scraper_test
```

2. Install requirements:
```
pip install -r requirements.txt
```

3. Install Playwright browsers:
```
playwright install
```

4. Install additional dependencies for PDF processing:
```
# For Ubuntu/Debian
sudo apt-get install -y poppler-utils

# For macOS
brew install poppler

# For Windows
# Install xpdf tools from: https://www.xpdfreader.com/download.html
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
- PDF documents:
  - `reglas_de_origen_capitulo4.pdf`: Chapter 4 (Rules of Origin) of the FTA
  - `reglas_especificas_anexo4.1.pdf`: Annex 4.1 (Specific Rules of Origin)
  - `enmienda_anexo4.1_2008.pdf`: 2008 Amendment to Annex 4.1
- Text versions of the documents:
  - `reglas_de_origen_capitulo4.txt`: Text version of Chapter 4
  - `reglas_especificas_anexo4.1.txt`: Text version of Annex 4.1
  - `enmienda_anexo4.1_2008.txt`: Text version of the 2008 Amendment

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

## Troubleshooting

### Common Issues

1. **404 Error**: If you encounter a "404 Client Error: Not Found" for the main FTA URL, check the current URL structure on the Aduana.cl website. The URL structure may have changed since this code was last updated.

2. **SSL Certificate Verification**: The script disables SSL certificate verification with `verify=False` due to potential issues with the Aduana.cl SSL certificate. While this allows the script to run, it's recommended to use proper certificate verification in production environments.

3. **PDF Extraction Issues**: If the PDF-to-text conversion fails, ensure you have installed the correct version of the poppler-utils package for your operating system.

4. **Playwright Issues**: If you encounter errors with Playwright, try reinstalling the browsers:
   ```
   playwright install chromium
   ```

## Future Improvements

- Add support for other Chile FTAs
- Implement a front-end dashboard for viewing extracted data
- Add email notifications for detected changes
- Create containerized version with Docker

## License

MIT
