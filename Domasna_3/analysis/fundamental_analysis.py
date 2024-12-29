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


async def fetch_attachment(session, attachment_id, issuer, last_scraped_date, file_name, attachment_ids_map):
    base_url = "https://api.seinet.com.mk/public/documents/attachment/"
    url = f"{base_url}{attachment_id}"  # Construct the URL for the specific attachment

    # Check if the file is a PDF
    if not file_name.lower().endswith('.pdf'):
        # print(f"Skipping non-PDF file: {file_name}")
        return

    try:
        async with session.get(url) as response:
            if response.status == 200:
                with io.BytesIO(await response.read()) as file:
                    with pdfplumber.open(file) as pdf:
                        all_text = ""
                        for page in pdf.pages:
                            all_text += page.extract_text()

                        if not all_text.strip():
                            return

                        # Define the recommendation based on sentiment
                        sentiment = TextBlob(all_text).sentiment.polarity
                        if sentiment > 0:
                            recommendation = actions["positive"]
                        elif sentiment < 0:
                            recommendation = actions["negative"]
                        else:
                            recommendation = actions["neutral"]

                        save_to_database('all_info', (issuer, recommendation, last_scraped_date))
                        update_last_scraped_date(issuer, last_scraped_date)

                        # Add attachment ID to the map for the issuer
                        if issuer not in attachment_ids_map:
                            attachment_ids_map[issuer] = []
                        attachment_ids_map[issuer].append(attachment_id)
            else:
                print(f"Failed to fetch attachment {attachment_id}: {response.status}")
    except Exception as e:
        print(f"Error extracting text from attachment {attachment_id}: {e}")


async def fetch_documents(session, issuer_id, attachment_ids_map):
    search_url = f"https://www.seinet.com.mk/search/{issuer_id}"
    date_from = get_last_scraped_date(issuer_id)
    date_to = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    try:
        async with session.get(search_url) as response:
            if response.status == 200:
                # Simulate loading the page and triggering the POST request
                data = {
                    "issuerId": issuer_id,
                    "languageId": 1,
                    "channelId": 1,
                    "dateFrom": date_from,
                    "dateTo": date_to,
                }

                post_url = "https://api.seinet.com.mk/public/documents"

                # print(f"Starting to fetch documents for Issuer ID {issuer_id}")

                async with session.post(post_url, json=data) as post_response:
                    if post_response.status == 200:
                        post_data = await post_response.json()
                        print(
                            f"Fetched {len(post_data.get('data', []))} documents for Issuer ID {issuer_id}")  # Logging result count
                        for document in post_data.get("data", []):
                            # issuer = document["issuer"].get("localizedTerms", [{}])[0].get("displayName")
                            issuer = issuers.get(issuer_id)
                            published_date = document.get("publishedDate")

                            for attachment in document.get("attachments", []):
                                attachment_id = attachment.get("attachmentId")
                                file_name = attachment.get("fileName")
                                await fetch_attachment(session, attachment_id, issuer, date_from, file_name,
                                                       attachment_ids_map)

                    else:
                        print(
                            f"Failed to retrieve documents for Issuer ID {issuer_id}. Status code: {post_response.status}")
            else:
                print(f"Failed to load search page for Issuer ID {issuer_id}. Status code: {response.status}")
    except Exception as e:
        print(f"Error processing Issuer ID {issuer_id}: {e}")


async def fetch_all_issuer_documents(session, issuer_ids):
    attachment_ids_map = {}  # Dictionary to store attachment IDs by issuer
    for issuer_id in issuer_ids:
        # Fetch and save all documents and attachments for one issuer before moving to the next
        await fetch_documents(session, issuer_id, attachment_ids_map)

    # Print attachment IDs and their count for each issuer
    for issuer, attachment_ids in attachment_ids_map.items():
        print(f"Issuer: {issuer} -> Attachment IDs: {attachment_ids}")
        print(f"Issuer: {issuer} -> Number of Attachments: {len(attachment_ids)}")


def calculate_final_recommendations():
    connection = sqlite3.connect('data/stock_data.db')
    cursor = connection.cursor()

    # Fetch all sentiments grouped by issuer
    cursor.execute("SELECT issuer, recommendation FROM all_info")
    rows = cursor.fetchall()

    # Group recommendations by issuer
    issuer_sentiments = defaultdict(list)
    for issuer, sentiment in rows:
        issuer_sentiments[issuer].append(sentiment)

    # Calculate the most common sentiment for each issuer
    for issuer, sentiments in issuer_sentiments.items():
        most_common_sentiment = Counter(sentiments).most_common(1)[0][0]

        # Save the final sentiment to the recommendations table
        save_to_database('recommendations', (issuer, most_common_sentiment))

    connection.close()


# Main function remains unchanged
async def main():
    setup_database()  # Ensure the database is set up
    async with aiohttp.ClientSession() as session:
        # Fetch documents for all issuers sequentially
        await fetch_all_issuer_documents(session, issuer_ids)

    # Calculate the final recommendations after all issuers are processed
    calculate_final_recommendations()


asyncio.run(main())
