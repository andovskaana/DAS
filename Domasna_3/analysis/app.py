from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime
import asyncio
from filters.F1 import filter_1
from filters.F3 import filter_3
from filters.F3 import reformat_number
from DB import init_createDB, get_last_saved_date, update_data
import pandas as pd
from technical_analysis import extend_to_time_frames
import mplfinance as mpf
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


@app.route('/analytics/technical-analysis', methods=['GET', 'POST'])
def technical_analysis():
    """Technical Analysis page using extended logic."""
    # Fetch available issuers from the database
    data_folder = 'data'
    db_path = os.path.join(data_folder, 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Symbol FROM StockData")
    issuers = [row[0] for row in cursor.fetchall()]
    conn.close()

    candlestick_data = None
    final_signals = None
    chart_path = None

    if request.method == 'POST':
        stock_symbol = request.form.get('symbol')

        # Fetch historical data for the selected stock
        conn = sqlite3.connect(db_path)
        query = """
            SELECT Date, LastTradePrice, Max, Min, Volume
            FROM StockData
            WHERE Symbol = ?
            ORDER BY Date ASC
        """
        historical_data = pd.read_sql_query(query, conn, params=(stock_symbol,))
        conn.close()

        if historical_data.empty:
            return render_template(
                'technical_analysis.html',
                issuers=issuers,
                error="No data found for the selected stock symbol."
            )

        # Preprocess data
        historical_data['Date'] = pd.to_datetime(historical_data['Date'], format='%m/%d/%Y')
        historical_data['LastTradePrice'] = historical_data['LastTradePrice'].replace(',', '', regex=True).astype(float)
        historical_data['Max'] = historical_data['Max'].replace(',', '', regex=True).astype(float)
        historical_data['Min'] = historical_data['Min'].replace(',', '', regex=True).astype(float)
        historical_data['Volume'] = historical_data['Volume'].replace(',', '', regex=True).astype(float)
        historical_data = historical_data.sort_values(by='Date').reset_index(drop=True)

        # Extend to timeframes and calculate signals using provided logic
        df_daily, df_weekly, df_monthly = extend_to_time_frames(historical_data)

        # Generate candlestick data for frontend
        df_candlestick = df_daily[['Date', 'LastTradePrice', 'Max', 'Min']].copy()
        df_candlestick.columns = ['date', 'close', 'high', 'low']
        df_candlestick['open'] = df_candlestick['close']  # Add Open column
        candlestick_data = df_candlestick.to_dict(orient='records')

        # Plot the candlestick chart and save it
        df_candlestick.set_index('date', inplace=True)
        chart_filename = f"candlestick_{stock_symbol}.png"
        chart_path = os.path.join('static', 'charts', chart_filename)
        mpf.plot(df_candlestick, type='candle', style='charles', title=f'Candlestick Chart for {stock_symbol}', volume=False, savefig=chart_path)

        # Final signals
        final_signals = {
            "daily": df_daily[['Date', 'LastTradePrice', 'Final_Signal']].tail().to_dict(orient='records'),
            "weekly": df_weekly[['Date', 'LastTradePrice', 'Final_Signal']].tail().to_dict(orient='records'),
            "monthly": df_monthly[['Date', 'LastTradePrice', 'Final_Signal']].tail().to_dict(orient='records')
        }

    return render_template(
        'technical_analysis.html',
        issuers=issuers,
        candlestick_data=candlestick_data,
        selected_symbol=stock_symbol if request.method == 'POST' else None,
        chart_path=chart_path,
        final_signals=final_signals
    )


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
