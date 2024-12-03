from flask import Flask, render_template
import sqlite3
import os
from datetime import datetime
import asyncio
from filters.F1 import filter_1
from filters.F3 import filter_3
from DB import init_createDB, get_last_saved_date, update_data

app = Flask(__name__)

DATABASE = os.path.join('data', 'stock_data.db')

init_createDB()


def rescrape_and_update_data():
    """Rescrape data and update the database."""
    print("Starting rescraping process...")
    issuers = filter_1()
    today_date = datetime.now().strftime('%m/%d/%Y')

    for issuer in issuers:
        last_saved_date = get_last_saved_date(issuer)
        if not last_saved_date or last_saved_date != today_date:
            print(f"Updating data for issuer: {issuer}")
            data = asyncio.run(filter_3(issuer, last_saved_date or "11/10/2014"))
            update_data(issuer, data, today_date)

    print("Rescraping process completed.")


@app.route('/')
def index():
    """Home page displaying stock data."""
    # Run rescraping logic before fetching data
    rescrape_and_update_data()

    # Fetch data from the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM StockData')
    rows = cursor.fetchall()
    conn.close()

    print(f"Fetched rows from database: {rows}")
    return render_template('index.html', rows=rows)


if __name__ == '__main__':
    app.run(debug=True)
