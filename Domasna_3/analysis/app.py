from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime
import asyncio
from filters.F1 import filter_1
from filters.F3 import filter_3
from filters.F3 import reformat_number
from DB import init_createDB, get_last_saved_date, update_data

app = Flask(__name__)

DATABASE = os.path.join('data', 'stock_data.db')

# Initialize the database
init_createDB()


def get_recommendation_counts(issuer):
    # Query the database to count recommendations for the selected issuer
    conn = sqlite3.connect('data/stock_data.db')  # Replace with your database
    cursor = conn.cursor()
    cursor.execute("""
            SELECT 'buy' AS recommendation, COUNT(*) 
            FROM all_info 
            WHERE issuer = ? AND recommendation = 'buy'
            UNION
            SELECT 'sell' AS recommendation, COUNT(*) 
            FROM all_info 
            WHERE issuer = ? AND recommendation = 'sell'
            UNION
            SELECT 'hold' AS recommendation, COUNT(*) 
            FROM all_info 
            WHERE issuer = ? AND recommendation = 'hold'
        """, (issuer, issuer, issuer))
    results = cursor.fetchall()
    conn.close()

    # Process the results into a dictionary
    counts = {"Buy": 0, "Sell": 0, "Hold": 0}
    for recommendation, count in results:
        recommendation = recommendation.capitalize()  # Converts 'hold' to 'Hold'
        if recommendation in counts:
            counts[recommendation] = count

    if counts["Buy"] > counts["Sell"]:
        recommendation = "Buy"
    elif counts["Sell"] > counts["Buy"]:
        recommendation = "Sell"
    else:
        recommendation = "Hold"

    return {**counts, "Recommendation": recommendation}

    # return counts


def get_issuers():
    # Connect to your database and fetch issuer names
    conn = sqlite3.connect('data/stock_data.db')  # Replace with your database
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT issuer FROM recommendations")  # Assuming `issuers` table exists
    issuers = cursor.fetchall()
    conn.close()
    return issuers



def rescrape_and_update_data():
    """Rescrape data and update the database."""
    print("Starting rescraping process...")
    issuers = filter_1()
    today_date = datetime.now().strftime('%m/%d/%Y')

    for issuer in issuers:
        last_saved_date = get_last_saved_date(issuer)
        if not last_saved_date or last_saved_date != today_date:
            print(f"Updating data for issuer: {issuer}")
            raw_data = asyncio.run(filter_3(issuer, last_saved_date or "11/10/2014"))

            # Reformat numeric fields in the fetched data
            formatted_data = []
            for row in raw_data:
                formatted_row = [
                    row[0],  # Date
                    reformat_number(row[1]),  # LastTradePrice
                    reformat_number(row[2]),  # Max
                    reformat_number(row[3]),  # Min
                    reformat_number(row[4]),  # AvgPrice
                    reformat_number(row[5]),  # PercentageChange
                    str(reformat_number(row[6])),  # Volume
                    str(reformat_number(row[7])),  # TurnoverInBEST
                    str(reformat_number(row[8]))  # TotalTurnover
                ]
                formatted_data.append(formatted_row)

            update_data(issuer, formatted_data, today_date)

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
    query = """
        SELECT * 
        FROM StockData 
        WHERE 1=1
    """
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

    # Add ORDER BY clause to sort by date
    query += """
    ORDER BY CAST(SUBSTR(Date, -4, 4) || '-' ||
                  printf('%02d', CAST(SUBSTR(Date, 1, INSTR(Date, '/') - 1) AS INTEGER)) || '-' ||
                  printf('%02d', CAST(SUBSTR(Date, INSTR(Date, '/') + 1, LENGTH(Date) - INSTR(Date, '/')) AS INTEGER))
              AS TEXT) DESC
    """

    # Fetch filtered rows from the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Render the template with fetched data
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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # SQL query to calculate the 10 most tradeable stocks based on volume and turnover
    query = """
SELECT 
    Symbol, 
    AvgPrice,
    PercentageChange,
    CAST(REPLACE(Volume, ',', '') AS INTEGER) AS DailyTotalVolume,
    TotalTurnover
FROM StockData
WHERE Date = (
    SELECT COALESCE(
        (SELECT CAST(STRFTIME('%m', 'now', 'localtime') AS INTEGER) || '/' || 
                CAST(STRFTIME('%d', 'now', 'localtime') AS INTEGER) || '/' || 
                STRFTIME('%Y', 'now', 'localtime')
         FROM StockData
         WHERE Date = CAST(STRFTIME('%m', 'now', 'localtime') AS INTEGER) || '/' || 
                      CAST(STRFTIME('%d', 'now', 'localtime') AS INTEGER) || '/' || 
                      STRFTIME('%Y', 'now', 'localtime')
         LIMIT 1),
        (SELECT CAST(STRFTIME('%m', 'now', 'localtime') AS INTEGER) || '/' || 
                CAST(STRFTIME('%d', 'now', 'localtime') - 1 AS INTEGER) || '/' || 
                STRFTIME('%Y', 'now', 'localtime')
         FROM StockData
         WHERE Date = CAST(STRFTIME('%m', 'now', 'localtime') AS INTEGER) || '/' || 
                      CAST(STRFTIME('%d', 'now', 'localtime') - 1 AS INTEGER) || '/' || 
                      STRFTIME('%Y', 'now', 'localtime')
         LIMIT 1)
    )
)
ORDER BY DailyTotalVolume DESC
LIMIT 10;"""
    cursor.execute(query)
    stocks = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', stocks=stocks)


@app.route('/analytics/technical-analysis')
def technical_analysis():
    """Technical Analysis page."""
    return render_template('technical_analysis.html')


@app.route('/analytics/fundamental-analysis', methods=['GET'])
def fundamental_analysis():
    issuers = get_issuers()
    return render_template('fundamental_analysis.html', issuers=issuers)


@app.route('/analytics/fundamental-analysis', methods=['POST'])
def get_fundamental_data():
    issuer_name = request.json.get('issuer')
    if issuer_name:
        data = get_recommendation_counts(issuer_name)
        return jsonify(data)
    return jsonify({})


@app.route('/analytics/lstm')
def lstm():
    """LSTM page."""
    return render_template('lstm.html')


if __name__ == '__main__':
    app.run(debug=True)
