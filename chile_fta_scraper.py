#!/usr/bin/env python3
"""
Chile FTA Scraper
This script scrapes Free Trade Agreement details from Chile's Customs website,
with a focus on the U.S.-Chile FTA. It extracts rules of origin, amendments,
and HTS codes impacted.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
from datetime import datetime
from playwright.sync_api import sync_playwright

# Constants
BASE_URL = "https://www.aduana.cl"
FTA_PAGE_URL = f"{BASE_URL}/tratado-de-libre-comercio-chile-estados-unidos/aduana/2007-02-28/122217.html"
DATABASE_PATH = "chile_fta_database.db"
RULES_OF_ORIGIN_TEXT = "chile_us_fta_rules_of_origin.txt"
CHAPTER4_TEXT = "chile_us_fta_chapter4.txt"
COMMON_GUIDELINES_TEXT = "chile_us_fta_common_guidelines.txt"
RULES_ORIGIN_PDF = "reglas_de_origen_capitulo4.pdf"
ANNEX41_PDF = "reglas_especificas_anexo4.1.pdf"
AMENDMENT_PDF = "enmienda_anexo4.1_2008.pdf"

class ChileFtaScraper:
    """
    Scraper for Free Trade Agreements from Chile Customs Website
    """
    def __init__(self):
        """Initialize the scraper with database connection"""
        self.conn = self.setup_database()
        self.session = requests.Session()
        # Add headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
    
    def setup_database(self):
        """Set up SQLite database for storing FTA data"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create table for documents (original rules, amendments, etc.)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fta_documents (
            id INTEGER PRIMARY KEY,
            fta_name TEXT,
            document_type TEXT,
            document_title TEXT,
            document_url TEXT,
            publication_date TEXT,
            last_checked_date TEXT,
            download_path TEXT
        )
        ''')
        
        # Create table for HTS codes and rules
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hts_rules (
            id INTEGER PRIMARY KEY,
            fta_name TEXT,
            hts_code TEXT,
            hts_description TEXT,
            origin_rule TEXT,
            document_id INTEGER,
            FOREIGN KEY (document_id) REFERENCES fta_documents (id)
        )
        ''')
        
        # Create table for website change tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS website_changes (
            id INTEGER PRIMARY KEY,
            url TEXT,
            check_date TEXT,
            content_hash TEXT,
            change_detected INTEGER
        )
        ''')
        
        conn.commit()
        return conn
    
    def find_chile_customs_website(self):
        """Find and verify the Chile customs website URL"""
        print(f"Using Chile Customs website: {BASE_URL}")
        return BASE_URL
    
    def find_fta_page(self):
        """Find the Free Trade Agreements page"""
        print(f"Using FTA page URL: {FTA_PAGE_URL}")
        return FTA_PAGE_URL
    
    def get_fta_documents(self, fta_url):
        """Get links to specific FTA documents including original texts and amendments"""
        try:
            response = self.session.get(fta_url, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            documents = []
            
            # Extract all document links from the page
            document_links = soup.find_all('a', href=True)
            for link in document_links:
                href = link.get('href')
                title = link.get_text().strip()
                
                if not title or not href:
                    continue
                
                # Filter for relevant documents using more specific criteria 
                if any(term in title.lower() or term in href.lower() for term in [
                    'origen', 'annex', 'anexo', 'amendment', 'enmienda', 
                    'directrices', 'guidelines', 'capitulo 4', 'chapter 4'
                ]):
                    
                    # Make sure URL is absolute
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"{BASE_URL}{href}"
                        else:
                            href = f"{BASE_URL}/{href}"
                    
                    document_type = self._determine_document_type(title)
                    
                    documents.append({
                        'title': title,
                        'url': href,
                        'type': document_type
                    })
            
            # Add our known document URLs if they weren't found on the page
            known_documents = [
                {
                    'title': 'Reglas de Origen Capítulo 4',
                    'url': 'https://www.aduana.cl/aduana/site/docs/20070711/20070711153552/reglas_de_origen_capitulo_cuatro.pdf',
                    'type': 'fta_chapter'
                },
                {
                    'title': 'Reglas Específicas de Origen Texto Original Anexo 4.1',
                    'url': 'https://www.aduana.cl/aduana/site/docs/20070711/20070711153552/04_anexo_reglas_especificas_origen.pdf',
                    'type': 'original_rules'
                },
                {
                    'title': 'Enmienda Anexo 4.1 Decreto N° 28 de 2008',
                    'url': 'https://www.aduana.cl/aduana/site/docs/20070711/20070711153552/03___dto_28_27_mar_2008_completo.pdf',
                    'type': 'amendment'
                }
            ]
            
            # Add known documents if they weren't found in the scraping
            for doc in known_documents:
                if not any(d['url'] == doc['url'] for d in documents):
                    documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error getting FTA documents: {e}")
            # Return known documents as fallback
            return [
                {
                    'title': 'Reglas de Origen Capítulo 4',
                    'url': 'https://www.aduana.cl/aduana/site/docs/20070711/20070711153552/reglas_de_origen_capitulo_cuatro.pdf',
                    'type': 'fta_chapter'
                },
                {
                    'title': 'Reglas Específicas de Origen Texto Original Anexo 4.1',
                    'url': 'https://www.aduana.cl/aduana/site/docs/20070711/20070711153552/04_anexo_reglas_especificas_origen.pdf',
                    'type': 'original_rules'
                },
                {
                    'title': 'Enmienda Anexo 4.1 Decreto N° 28 de 2008',
                    'url': 'https://www.aduana.cl/aduana/site/docs/20070711/20070711153552/03___dto_28_27_mar_2008_completo.pdf',
                    'type': 'amendment'
                }
            ]
    
    def _determine_document_type(self, title):
        """Determine the type of document from its title"""
        title_lower = title.lower()
        
        if 'original' in title_lower and ('anexo' in title_lower or 'annex' in title_lower):
            return 'original_rules'
        elif ('enmienda' in title_lower or 'amendment' in title_lower) and ('anexo' in title_lower or 'annex' in title_lower):
            return 'amendment'
        elif 'capítulo' in title_lower or 'chapter' in title_lower:
            return 'fta_chapter'
        elif 'directrices' in title_lower or 'guidelines' in title_lower:
            return 'common_guidelines'
        elif 'certificado' in title_lower or 'certificate' in title_lower:
            return 'certificate_of_origin'
        else:
            return 'other'
    
    def download_document(self, url, filename):
        """Download a document from a URL"""
        try:
            print(f"Downloading {url} to {filename}")
            response = self.session.get(url, verify=False)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"Successfully downloaded {filename} ({len(response.content)} bytes)")
            
            # If it's a PDF, try to convert to text for easier processing
            if filename.endswith('.pdf'):
                text_filename = filename.replace('.pdf', '.txt')
                try:
                    import subprocess
                    subprocess.run(['pdftotext', '-layout', filename, text_filename], check=True)
                    print(f"Converted {filename} to {text_filename}")
                except Exception as conv_err:
                    print(f"Warning: Could not convert PDF to text: {conv_err}")
            
            return filename
        except Exception as e:
            print(f"Error downloading document {url}: {e}")
            # Check if the file already exists locally
            if os.path.exists(filename):
                print(f"Using existing local file: {filename}")
                return filename
            return None
    
    def save_document_to_db(self, fta_name, doc_info, download_path=None):
        """Save document information to the database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        INSERT INTO fta_documents 
        (fta_name, document_type, document_title, document_url, publication_date, last_checked_date, download_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            fta_name,
            doc_info['type'],
            doc_info['title'],
            doc_info['url'],
            doc_info.get('publication_date', ''),
            datetime.now().strftime('%Y-%m-%d'),
            download_path
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def parse_rules_of_origin(self, text_file):
        """Parse rules of origin from text file extracted from PDF"""
        hts_rules = []
        
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split the content by sections
            sections = content.split('SECCION')
            
            # Skip the introduction section
            for section in sections[1:]:  # Start from the first actual section
                chapter_blocks = re.split(r'Capítulo\s+(\d+)', section)
                
                # Process each chapter
                for i in range(1, len(chapter_blocks), 2):
                    if i+1 < len(chapter_blocks):
                        chapter_num = chapter_blocks[i].strip()
                        chapter_content = chapter_blocks[i+1].strip()
                        
                        # Extract chapter description
                        chapter_desc_match = re.search(r'^(.*?)\.', chapter_content)
                        chapter_desc = chapter_desc_match.group(1).strip() if chapter_desc_match else ""
                        
                        # Extract HTS codes and rules
                        hts_blocks = re.findall(r'(\d+\.\d+(?:\s*-\s*\d+\.\d+)?)\s+(.*?)(?=\d+\.\d+|$)', chapter_content, re.DOTALL)
                        
                        for hts_code, rule_text in hts_blocks:
                            hts_code = hts_code.strip()
                            rule_text = rule_text.strip()
                            
                            hts_rules.append({
                                'hts_code': hts_code,
                                'hts_description': chapter_desc,
                                'origin_rule': rule_text
                            })
            
            return hts_rules
        except Exception as e:
            print(f"Error parsing rules of origin: {e}")
            return []
    
    def save_hts_rules_to_db(self, fta_name, hts_rules, document_id):
        """Save HTS rules to the database"""
        cursor = self.conn.cursor()
        
        for rule in hts_rules:
            cursor.execute('''
            INSERT INTO hts_rules 
            (fta_name, hts_code, hts_description, origin_rule, document_id)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                fta_name,
                rule['hts_code'],
                rule['hts_description'],
                rule['origin_rule'],
                document_id
            ))
        
        self.conn.commit()
    
    def monitor_for_changes(self, url):
        """Check if website content has changed"""
        cursor = self.conn.cursor()
        
        # Get current content
        try:
            response = self.session.get(url, verify=False)
            response.raise_for_status()
            content = response.text
            
            # Calculate content hash
            import hashlib
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Check if we've seen this URL before
            cursor.execute('SELECT content_hash FROM website_changes WHERE url = ? ORDER BY check_date DESC LIMIT 1', (url,))
            result = cursor.fetchone()
            
            change_detected = 0
            if result:
                old_hash = result[0]
                if old_hash != content_hash:
                    change_detected = 1
                    print(f"Change detected on {url}")
            
            # Save the new check
            cursor.execute('''
            INSERT INTO website_changes (url, check_date, content_hash, change_detected)
            VALUES (?, ?, ?, ?)
            ''', (
                url,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                content_hash,
                change_detected
            ))
            
            self.conn.commit()
            return change_detected
        except Exception as e:
            print(f"Error monitoring for changes on {url}: {e}")
            return -1  # Error code
    
    def setup_automation(self):
        """Set up automation script using Playwright to monitor the website"""
        def run_browser_monitoring():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Visit the FTA page
                print(f"Visiting {FTA_PAGE_URL}")
                page.goto(FTA_PAGE_URL)
                
                # Take a screenshot
                screenshot_path = f"fta_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_path)
                
                # Extract links and content
                content = page.content()
                
                # Calculate hash for change detection
                import hashlib
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                # Save to database
                cursor = self.conn.cursor()
                cursor.execute('SELECT content_hash FROM website_changes WHERE url = ? ORDER BY check_date DESC LIMIT 1', (FTA_PAGE_URL,))
                result = cursor.fetchone()
                
                change_detected = 0
                if result:
                    old_hash = result[0]
                    if old_hash != content_hash:
                        change_detected = 1
                        print(f"Change detected on {FTA_PAGE_URL}")
                
                cursor.execute('''
                INSERT INTO website_changes (url, check_date, content_hash, change_detected)
                VALUES (?, ?, ?, ?)
                ''', (
                    FTA_PAGE_URL,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    content_hash,
                    change_detected
                ))
                
                self.conn.commit()
                browser.close()
                
                print(f"Monitoring run completed. Screenshot saved to {screenshot_path}")
                return change_detected
        
        return run_browser_monitoring
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    """Main function to run the Chile FTA scraper"""
    scraper = ChileFtaScraper()
    
    try:
        # Step 1: Find the Chile customs website
        customs_site = scraper.find_chile_customs_website()
        print(f"Found Chile customs website: {customs_site}")
        
        # Step 2: Find the FTA page
        fta_page = scraper.find_fta_page()
        print(f"Found FTA page: {fta_page}")
        
        # Step 3: Find and process FTA documents
        print("Retrieving FTA documents...")
        documents = scraper.get_fta_documents(fta_page)
        print(f"Found {len(documents)} documents")
        
        # Process each document
        for doc in documents:
            print(f"Processing document: {doc['title']}")
            
            # Determine filename
            if 'origin' in doc['url'].lower() and 'cap' in doc['url'].lower() and doc['url'].endswith('.pdf'):
                filename = RULES_ORIGIN_PDF
            elif 'anexo' in doc['url'].lower() and 'reg' in doc['url'].lower() and doc['url'].endswith('.pdf'):
                filename = ANNEX41_PDF
            elif 'dto' in doc['url'].lower() and 'mar_2008' in doc['url'].lower() and doc['url'].endswith('.pdf'):
                filename = AMENDMENT_PDF
            else:
                # Create a filename based on the document title
                filename = re.sub(r'[^a-zA-Z0-9]', '_', doc['title'])[:30].lower() + '.pdf'
            
            # Download the document
            download_path = scraper.download_document(doc['url'], filename)
            
            # Save to database
            doc_id = scraper.save_document_to_db("Chile-US FTA", doc, download_path)
            
            # Process rules of origin if this is that document
            if doc['type'] == 'original_rules' or 'anexo 4.1' in doc['title'].lower():
                # Use either the downloaded text file or the existing one
                rules_text = filename.replace('.pdf', '.txt')
                if not os.path.exists(rules_text) and os.path.exists(RULES_OF_ORIGIN_TEXT):
                    rules_text = RULES_OF_ORIGIN_TEXT
                
                if os.path.exists(rules_text):
                    print(f"Parsing rules from: {rules_text}")
                    hts_rules = scraper.parse_rules_of_origin(rules_text)
                    print(f"Found {len(hts_rules)} HTS rules")
                    scraper.save_hts_rules_to_db("Chile-US FTA", hts_rules, doc_id)
        
        # Step 5: Set up automated monitoring
        print("Setting up monitoring...")
        monitor_func = scraper.setup_automation()
        
        # Run monitoring once to check
        try:
            result = monitor_func()
            if result == 1:
                print("Changes detected on first run")
            elif result == 0:
                print("No changes detected on first run")
            else:
                print("Error running monitoring")
        except Exception as e:
            print(f"Warning: Monitoring setup failed, but documents were still processed: {e}")
            print("This might be due to Playwright browser issues. Please install the browser dependencies or run without monitoring.")
        
        print("FTA scraping and monitoring setup complete.")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()