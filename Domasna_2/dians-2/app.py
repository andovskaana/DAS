from flask import Flask, render_template, request
import sqlite3
import os
from datetime import datetime
import asyncio
from filters.F1 import filter_1
from filters.F3 import filter_3
from DB import init_createDB, get_last_saved_date, update_data

app = Flask(__name__)

DATABASE = os.path.join('data', 'stock_data.db')

# Initialize the database
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
    """Home page displaying stock data with filtering options."""
    # Fetch query parameters for filters
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    issuer = request.args.get('issuer', 'ALL')

    # Rescrape and update the database
    rescrape_and_update_data()

    # Fetch issuers for the dropdown
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Symbol FROM StockData")
    issuers = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Build query based on filters
    query = "SELECT * FROM StockData WHERE 1=1"
    params = []

    if from_date:
        query += """
        AND CAST(SUBSTR(Date, -4, 4) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, 1, INSTR(Date, '/') - 1) AS INTEGER)) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, INSTR(Date, '/') + 1, LENGTH(Date) - INSTR(Date, '/')) AS INTEGER))
             AS TEXT) >= ?
        """
        params.append(from_date)

    if to_date:
        query += """
        AND CAST(SUBSTR(Date, -4, 4) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, 1, INSTR(Date, '/') - 1) AS INTEGER)) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, INSTR(Date, '/') + 1, LENGTH(Date) - INSTR(Date, '/')) AS INTEGER))
             AS TEXT) <= ?
        """
        params.append(to_date)

    if issuer != "ALL":
        query += " AND Symbol = ?"
        params.append(issuer)
    print(query)
    print(params)
    # Fetch filtered rows from the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    # cursor.execute("SELECT * FROM StockData WHERE Date >= '2/1/2022' AND Date <= '2/28/2022';")
    rows = cursor.fetchall()
    conn.close()
    print(rows)
    # print(f"Fetched rows from database: {rows}")
    # print(f"Issuers: {issuers}")
    return render_template(
        'index.html',
        rows=rows,
        issuers=issuers,
        from_date=from_date,
        to_date=to_date,
        issuer=issuer
    )


@app.route('/dashboard')
def dashboard():

    return render_template('dashboard.html')



@app.route('/analytics/technical-analysis')
def technical_analysis():
    """Technical Analysis page."""
    return render_template('technical_analysis.html')


@app.route('/analytics/fundamental-analysis')
def fundamental_analysis():
    """Fundamental Analysis page."""
    return render_template('fundamental_analysis.html')


@app.route('/analytics/lstm')
def lstm():
    """LSTM page."""
    return render_template('lstm.html')


if __name__ == '__main__':
    app.run(debug=True)
