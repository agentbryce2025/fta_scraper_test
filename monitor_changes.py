#!/usr/bin/env python3
"""
Chile FTA Monitoring Script
This script checks for changes to Chile's FTA pages and sends notifications if changes are detected.
"""

import os
import sys
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.sync_api import sync_playwright
import sqlite3
import hashlib
import schedule
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("monitor.log"), logging.StreamHandler()]
)
logger = logging.getLogger("FTA_Monitor")

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "chile_fta_database.db")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")

# Make sure screenshots directory exists
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# URLs to monitor
URLS_TO_MONITOR = [
    "https://www.aduana.cl/tratado-de-libre-comercio-chile-estados-unidos/",
    # Add more URLs as needed
]

def setup_database():
    """Ensure database and tables exist"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create website_changes table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS website_changes (
        id INTEGER PRIMARY KEY,
        url TEXT,
        check_date TEXT,
        content_hash TEXT,
        change_detected INTEGER
    )
    ''')
    
    # Create notifications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS change_notifications (
        id INTEGER PRIMARY KEY,
        url TEXT,
        notification_date TEXT,
        notification_sent INTEGER,
        notification_message TEXT
    )
    ''')
    
    conn.commit()
    return conn

def check_url_for_changes(url, conn):
    """Check if a URL has changed since last check"""
    try:
        with sync_playwright() as p:
            logger.info(f"Checking {url} for changes...")
            
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Visit the URL
            page.goto(url, wait_until="networkidle")
            
            # Take a screenshot
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"check_{timestamp}_{url.replace('/', '_').replace(':', '')}.png")
            page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Get the content
            content = page.content()
            
            # Calculate hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Close browser
            browser.close()
            
            # Check for changes in database
            cursor = conn.cursor()
            cursor.execute('SELECT content_hash FROM website_changes WHERE url = ? ORDER BY check_date DESC LIMIT 1', (url,))
            result = cursor.fetchone()
            
            change_detected = 0
            if result:
                old_hash = result[0]
                if old_hash != content_hash:
                    change_detected = 1
                    logger.warning(f"Change detected on {url}")
                    
                    # Record the notification
                    cursor.execute('''
                    INSERT INTO change_notifications 
                    (url, notification_date, notification_sent, notification_message)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        url,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        0,  # Not sent yet
                        f"Change detected on {url} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ))
            else:
                logger.info(f"First check for {url}, no previous data to compare")
            
            # Record the check
            cursor.execute('''
            INSERT INTO website_changes (url, check_date, content_hash, change_detected)
            VALUES (?, ?, ?, ?)
            ''', (
                url,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                content_hash,
                change_detected
            ))
            
            conn.commit()
            return change_detected, screenshot_path
            
    except Exception as e:
        logger.error(f"Error checking {url}: {e}")
        return -1, None  # Error

def send_notification(to_email, message, screenshot_path=None):
    """Send an email notification about changes"""
    # This would be configured with real email settings in production
    logger.info(f"Would send notification to {to_email}: {message}")
    logger.info(f"Screenshot attached: {screenshot_path}")
    
    # In a real implementation, you would use the email settings below
    """
    try:
        from_email = "your-notification-email@example.com"
        password = "your-app-password"  # Use app password for Gmail
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = "Chile FTA Website Change Detected"
        
        msg.attach(MIMEText(message, 'plain'))
        
        # Attach screenshot if available
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, 'rb') as f:
                img_data = f.read()
            from email.mime.image import MIMEImage
            image = MIMEImage(img_data, name=os.path.basename(screenshot_path))
            msg.attach(image)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Notification sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False
    """
    # For demo purposes, just return success
    return True

def process_pending_notifications(conn, notification_email=None):
    """Send any pending notifications"""
    if not notification_email:
        logger.info("No notification email provided, skipping notifications")
        return
    
    cursor = conn.cursor()
    cursor.execute('SELECT id, url, notification_date, notification_message FROM change_notifications WHERE notification_sent = 0')
    pending = cursor.fetchall()
    
    for notification_id, url, date, message in pending:
        # Get the most recent screenshot for this URL
        cursor.execute('''
        SELECT check_date FROM website_changes 
        WHERE url = ? AND change_detected = 1
        ORDER BY check_date DESC LIMIT 1
        ''', (url,))
        result = cursor.fetchone()
        
        if result:
            check_date = result[0]
            # Construct screenshot path
            timestamp = datetime.strptime(check_date, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d_%H%M%S')
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"check_{timestamp}_{url.replace('/', '_').replace(':', '')}.png")
            
            # Send notification
            if send_notification(notification_email, message, screenshot_path):
                # Mark as sent
                cursor.execute('UPDATE change_notifications SET notification_sent = 1 WHERE id = ?', (notification_id,))
                conn.commit()
                logger.info(f"Notification for {url} marked as sent")

def check_all_urls(notification_email=None):
    """Check all URLs for changes"""
    conn = setup_database()
    try:
        for url in URLS_TO_MONITOR:
            change_detected, screenshot_path = check_url_for_changes(url, conn)
            
            if change_detected == 1 and notification_email:
                message = f"Change detected on {url} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                send_notification(notification_email, message, screenshot_path)
        
        # Process any pending notifications
        process_pending_notifications(conn, notification_email)
    finally:
        conn.close()

def run_schedule(notification_email=None, interval_hours=24):
    """Run the monitoring on a schedule"""
    logger.info(f"Starting scheduled monitoring every {interval_hours} hours")
    
    # Run once immediately
    check_all_urls(notification_email)
    
    # Then schedule
    schedule.every(interval_hours).hours.do(check_all_urls, notification_email=notification_email)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for pending tasks
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Monitor Chile FTA website for changes")
    parser.add_argument("--email", help="Email to send notifications to")
    parser.add_argument("--interval", type=int, default=24, help="Check interval in hours (default: 24)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    if args.once:
        check_all_urls(args.email)
    else:
        run_schedule(args.email, args.interval)

if __name__ == "__main__":
    main()