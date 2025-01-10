import requests
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime
import asyncio
from filters.F1 import filter_1
from filters.F3 import filter_3
from filters.F3 import reformat_number
from DB import init_createDB, get_last_saved_date, update_data
import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
from lstm import train_and_predict

DATABASE = os.path.join('data', 'stock_data.db')

# Initialize the database
init_createDB()

def get_stock_data(symbol, start_date, end_date):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    query = """
        SELECT Date, LastTradePrice, Max, Min, Volume
        FROM StockData
        WHERE Symbol = ? AND Date BETWEEN ? AND ?
        ORDER BY Date DESC
    """
    cursor.execute(query, (symbol, start_date, end_date))
    data = cursor.fetchall()
    conn.close()
    return [
        {'date': row[0], 'last_transaction': row[1], 'max_value': row[2], 'min_value': row[3], 'volume': row[4]}
        for row in data
    ]

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

    # Find the latest date in the database
    latest_date_query = """
    SELECT Date 
    FROM StockData
    ORDER BY CAST(SUBSTR(Date, 7, 4) || SUBSTR(Date, 1, 2) || SUBSTR(Date, 4, 2) AS INTEGER) DESC
    LIMIT 1
    """
    cursor.execute(latest_date_query)
    latest_date = cursor.fetchone()
    latest_date = latest_date[0] if latest_date else None

    if not latest_date:
        # No data in the database
        stocks = []
    else:
        # Retrieve the top 10 most tradeable stocks
        query = """
        SELECT 
            Symbol, 
            AvgPrice,
            PercentageChange,
            CAST(REPLACE(Volume, '.', '') AS INTEGER) AS DailyTotalVolume,
            TotalTurnover
        FROM StockData
        WHERE Date = ?
        ORDER BY DailyTotalVolume DESC
        LIMIT 10
        """
        cursor.execute(query, (latest_date,))
        stocks = cursor.fetchall()

    conn.close()
    print(stocks)  # Debugging output to verify fetched data

    return render_template('dashboard.html', stocks=stocks)


@app.route('/technical-analysis', methods=['POST'])
def technical_analysis():
    """Calls the technical analysis microservice"""
    symbol = request.form.get('symbol')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # Prepare the payload for the API request
    payload = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date
    }

    # Call the technical analysis service
    response = requests.post('http://localhost:5001/api/technical-analysis', json=payload)

    if response.status_code == 200:
        analysis_data = response.json()
        return render_template('technical_analysis.html', analysis_data=analysis_data)
    else:
        return render_template('technical_analysis.html', error="Failed to fetch technical analysis data")


#
@app.route('/analytics/fundamental-analysis', methods=['GET'])
def fundamental_analysis():
    issuers = get_issuers()
    return render_template('fundamental_analysis.html', issuers=issuers)

# @app.route('/analytics/fundamental-analysis', methods=['POST'])
# def get_fundamental_data():
#     issuer_name = request.json.get('issuer')
#     if issuer_name:
#         data = get_recommendation_counts(issuer_name)
#         return jsonify(data)
#     return jsonify({})

@app.route('/analytics/fundamental-analysis', methods=['POST'])
def get_fundamental_data():
    issuer_name = request.json.get('issuer')
    if issuer_name:
        # Call the fundamental analysis microservice
        try:
            response = requests.post(
                'http://localhost:5002/api/fundamental-analysis',
                json={"issuer": issuer_name}
            )
            logging.debug(f"Microservice response: {response.status_code}, {response.text}")
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({"error": "Failed to fetch data from the microservice"}), response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error contacting microservice: {e}")
            return jsonify({"error": str(e)}), 500


# @app.route('/analytics/lstm')
# def lstm():
#     """LSTM page."""
#     return render_template('lstm.html')

@app.route('/analytics/lstm', methods=['GET', 'POST'])
def lstm():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Symbol FROM StockData")
    issuers = [row[0] for row in cursor.fetchall()]
    conn.close()

    predicted_price = None
    last_prices = None
    graph_path = None
    recommendation = None
    error_message = None
    metrics = None
    selected_symbol = None

    if request.method == 'POST':
        selected_symbol = request.form.get('symbol')
        predicted_price, last_prices, metrics, graph_path = train_and_predict(selected_symbol)

        if predicted_price is not None and last_prices is not None:
            last_price = last_prices[-1]
            if predicted_price > last_price * 1.05:
                recommendation = "Sell"
            elif predicted_price < last_price * 0.95:
                recommendation = "Buy"
            else:
                recommendation = "Hold"
        else:
            error_message = "Not enough data for prediction."
            recommendation = "Hold"

    return render_template(
        'lstm.html',
        issuers=issuers,
        predicted_price=predicted_price,
        recommendation=recommendation,
        graph_path=graph_path,
        metrics=metrics,
        error_message=error_message,
        selected_symbol=selected_symbol
    )

if __name__ == '__main__':
    app.run(debug=True)
