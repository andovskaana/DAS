import asyncio
from datetime import datetime, timedelta
import aiohttp
import sqlite3
from collections import defaultdict, Counter
from textblob import TextBlob
import pdfplumber
import io
import os
from playwright.sync_api import sync_playwright

def scraping():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://seinet.com.mk")
        try:
            page.wait_for_selector('#root > nav > div.header-panel-container.w-100 > div > ul > div > button',
                                   state="visible", timeout=60000)
            page.click('#root > nav > div.header-panel-container.w-100 > div > ul > div > button')
            print("Dropdown menu clicked.")
        except Exception as e:
            print(f"Failed to click the dropdown menu: {e}")

            # Wait for the English language option to appear and click it
        try:
            page.wait_for_selector('[data-key="en-GB"]', state="visible", timeout=60000)
            page.click('[data-key="en-GB"]')
            print("Switched to English successfully.")
        except Exception as e:
            print(f"Failed to switch to English: {e}")
        page.click('[data-key="en-GB"]')
        page.wait_for_selector("#formIssuerId")
        options = page.query_selector_all("#formIssuerId option")
        issuers = {option.get_attribute("value"): option.text_content().strip() for option in options if
                   option.get_attribute("value")}
        print(issuers)
        browser.close()
        return issuers
def get_default_date_from():
    """Calculate one year ago today."""
    return (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%S')


def get_last_scraped_date(issuer):
    """Get the last scraped date from the database for a specific issuer."""
    db_path = 'data/stock_data.db'
    default_date_from = get_default_date_from()

    # Check if database exists
    if not os.path.exists(db_path):
        return default_date_from

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Check if `all_info` table exists
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='all_info';
    """)
    table_exists = cursor.fetchone()

    if not table_exists:
        connection.close()
        return default_date_from

    # Fetch the last_scraped_date for the issuer
    cursor.execute("""
        SELECT last_scraped_date FROM all_info WHERE issuer = ?;
    """, (issuer,))
    last_scraped_date = cursor.fetchone()
    connection.close()

    # Return last scraped date if exists, otherwise default date
    if last_scraped_date and last_scraped_date[0]:
        return last_scraped_date[0]
    else:
        return default_date_from


def update_last_scraped_date(issuer, scrape_date):
    """Update the last scraped date in the database."""
    db_path = 'data/stock_data.db'
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Check if the issuer already exists in the table
    cursor.execute("SELECT COUNT(*) FROM all_info WHERE issuer = ?", (issuer,))
    row_count = cursor.fetchone()[0]

    if row_count > 0:
        # If the issuer exists, update the last scraped date
        cursor.execute("""
            UPDATE all_info
            SET last_scraped_date = ?
            WHERE issuer = ?
        """, (scrape_date, issuer))
    else:
        # If the issuer doesn't exist, insert a new record
        cursor.execute("""
            INSERT INTO all_info (issuer, last_scraped_date)
            VALUES (?, ?)
        """, (issuer, scrape_date))

    connection.commit()
    connection.close()


issuers = scraping()
print(issuers)
issuer_ids = list(issuers.keys())[1:]

# Semaphore to limit the number of concurrent requests
semaphore = asyncio.Semaphore(20)  # Limit to 5 concurrent requests

# Mapping sentiment analysis to stock market actions
actions = {"positive": "buy", "negative": "sell", "neutral": "hold"}

# Database setup
def setup_database():
    connection = sqlite3.connect('data/stock_data.db')  # Connect to stock_data.db
    cursor = connection.cursor()

    cursor.execute('''
         CREATE TABLE IF NOT EXISTS all_info (
             issuer TEXT,
             recommendation TEXT,
             last_scraped_date TEXT
         )
     ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            issuer TEXT PRIMARY KEY,
            current_recommendation TEXT
        )
    ''')

    connection.commit()
    connection.close()


def save_to_database(table, data):
    connection = sqlite3.connect('data/stock_data.db')  # Connect to stock_data.db
    cursor = connection.cursor()

    if table == 'all_info':
        cursor.execute('INSERT INTO all_info (issuer, recommendation, last_scraped_date) VALUES (?, ?, ?)', data)
    elif table == 'recommendations':
        cursor.execute('INSERT OR REPLACE INTO recommendations (issuer, current_recommendation) VALUES (?, ?)', data)

    connection.commit()
    connection.close()