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
import mplfinance as mpf
app = Flask(__name__)
from technical_analysis import plot_charts, generate_signals, calculate_bollinger_bands, calculate_rsi, clean_numeric_column, calculate_sma, calculate_stochastic_oscillator, calculate_ema, calculate_williams_percent_range, calculate_momentum
import numpy as np
import pandas as pd
from lstm import train_and_predict, preprocess_data
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from keras import Sequential
from keras.api.layers import LSTM, Dense, Dropout
from keras.api.optimizers import Adam
from sklearn.metrics import mean_squared_error



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



@app.route('/analytics/technical-analysis', methods=['GET', 'POST'])
def technical_analysis():
    """Technical Analysis page using extended logic."""
    data_folder = 'data'
    db_path = os.path.join(data_folder, 'stock_data.db')

    # Fetch available issuers
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
        try:
            query = """
                SELECT Date, LastTradePrice, Max, Min, Volume
                FROM StockData
                WHERE Symbol = ?
                ORDER BY Date ASC
            """
            historical_data = pd.read_sql_query(query, conn, params=(stock_symbol,))
        finally:
            conn.close()

        if historical_data.empty:
            return render_template(
                'technical_analysis.html',
                issuers=issuers,
                error="No data found for the selected stock symbol."
            )

        # Preprocess data
        historical_data['Date'] = pd.to_datetime(historical_data['Date'], format='%m/%d/%Y')
        numerical_cols = ['LastTradePrice', 'Max', 'Min', 'Volume']
        for col in numerical_cols:
            historical_data[col] = historical_data[col].apply(clean_numeric_column)

        historical_data = historical_data.sort_values(by='Date').reset_index(drop=True)

        # Perform calculations for daily indicators
        historical_data['RSI'] = calculate_rsi(historical_data['LastTradePrice'])
        historical_data['Momentum'] = calculate_momentum(historical_data['LastTradePrice'], 10)
        historical_data['Williams_%R'] = calculate_williams_percent_range(
            historical_data['LastTradePrice'],
            historical_data['Max'],
            historical_data['Min'],
            14
        )
        historical_data['Stochastic_Oscillator'] = calculate_stochastic_oscillator(
            historical_data['LastTradePrice'],
            historical_data['Max'],
            historical_data['Min'],
            14
        )
        historical_data['SMA_10'] = calculate_sma(historical_data['LastTradePrice'], 10)
        historical_data['EMA_10'] = calculate_ema(historical_data['LastTradePrice'], 10)
        historical_data['BB_MA'], historical_data['BB_Upper'], historical_data['BB_Lower'] = calculate_bollinger_bands(
            historical_data['LastTradePrice'], 10)
        historical_data = generate_signals(historical_data)

        # Extend to time frames (daily, weekly, monthly)
        historical_data.set_index('Date', inplace=True)

        # # Weekly and monthly resampling with appropriate aggregations
        # df_weekly = historical_data.resample('W').agg({
        #     'LastTradePrice': 'last',
        #     'Max': 'max',
        #     'Min': 'min',
        #     'Volume': 'sum',
        #     # 'RSI': 'last',
        #     # 'Momentum': 'last',
        #     # 'Williams_%R': 'last',
        #     # 'Stochastic_Oscillator': 'last',
        #     # 'Final_Signal': 'last'
        #     'RSI': 'mean',
        #     'Momentum': 'mean',
        #     'Williams_%R': 'mean',
        #     'Stochastic_Oscillator': 'mean'
        # }).dropna()
        #
        # df_monthly = historical_data.resample('M').agg({
        #     'LastTradePrice': 'last',
        #     'Max': 'max',
        #     'Min': 'min',
        #     'Volume': 'sum',
        #     # 'RSI': 'last',
        #     # 'Momentum': 'last',
        #     # 'Williams_%R': 'last',
        #     # 'Stochastic_Oscillator': 'last',
        #     # 'Final_Signal': 'last'
        #     'RSI': 'mean',
        #     'Momentum': 'mean',
        #     'Williams_%R': 'mean',
        #     'Stochastic_Oscillator': 'mean',
        # }).dropna()
        #
        # # Reset index after resampling
        # df_weekly.reset_index(inplace=True)
        # df_monthly.reset_index(inplace=True)
        #
        # # Generate signals for weekly and monthly timeframes
        # df_weekly = generate_signals(df_weekly)
        # df_monthly = generate_signals(df_monthly)

        # Weekly resampling
        # df_weekly = historical_data.resample('W').agg({
        #     'LastTradePrice': 'last',
        #     'Max': 'max',
        #     'Min': 'min',
        #     'Volume': 'sum',
        #     'RSI': 'mean',
        #     'Momentum': 'mean',
        #     'Williams_%R': 'mean',
        #     'Stochastic_Oscillator': 'mean'
        # }).dropna()
        df_weekly = historical_data.resample('W').agg({
            'LastTradePrice': 'last',
            'Max': 'max',
            'Min': 'min',
            'Volume': 'sum',
            'RSI': 'mean',
            'Momentum': 'mean',
            'Williams_%R': 'mean',
            'Stochastic_Oscillator': 'mean',
            'SMA_10': 'mean',
            'EMA_10': 'mean'
        }).dropna()

        if df_weekly.empty:
            df_weekly = pd.DataFrame(columns=['Date', 'LastTradePrice', 'Final_Signal'])
            df_weekly['Final_Signal'] = 'Not Sufficient Information'
        else:
            df_weekly = generate_signals(df_weekly)

        # Monthly resampling
        # df_monthly = historical_data.resample('M').agg({
        #     'LastTradePrice': 'last',
        #     'Max': 'max',
        #     'Min': 'min',
        #     'Volume': 'sum',
        #     'RSI': 'mean',
        #     'Momentum': 'mean',
        #     'Williams_%R': 'mean',
        #     'Stochastic_Oscillator': 'mean',
        # }).dropna()
        df_monthly = historical_data.resample('M').agg({
            'LastTradePrice': 'last',
            'Max': 'max',
            'Min': 'min',
            'Volume': 'sum',
            'RSI': 'mean',
            'Momentum': 'mean',
            'Williams_%R': 'mean',
            'Stochastic_Oscillator': 'mean',
            'SMA_10': 'mean',
            'EMA_10': 'mean'
        }).dropna()

        if df_monthly.empty:
            df_monthly = pd.DataFrame(columns=['Date', 'LastTradePrice', 'Final_Signal'])
            df_monthly['Final_Signal'] = 'Not Sufficient Information'
        else:
            df_monthly = generate_signals(df_monthly)

        # Reset indices to make them compatible with rendering logic
        df_weekly.reset_index(inplace=True)
        df_monthly.reset_index(inplace=True)

        # Generate candlestick data
        df_candlestick = historical_data[['LastTradePrice', 'Max', 'Min']].reset_index()
        df_candlestick.columns = ['date', 'close', 'high', 'low']
        df_candlestick['open'] = df_candlestick['close']
        candlestick_data = df_candlestick.to_dict(orient='records')

        # Plot candlestick chart
        df_candlestick.set_index('date', inplace=True)
        chart_filename = f"candlestick_{stock_symbol}.png"
        chart_path = os.path.join('static', 'charts', chart_filename)
        mpf.plot(df_candlestick, type='candle', style='charles', title=f'Candlestick Chart for {stock_symbol}',
                 volume=False, savefig=chart_path)

        # # Extract signals for rendering
        # final_signals = {
        #     "daily": historical_data.reset_index()[['Date', 'LastTradePrice', 'Final_Signal']].tail().to_dict(
        #         orient='records'),
        #     "weekly": df_weekly[['Date', 'LastTradePrice', 'Final_Signal']].tail().to_dict(orient='records'),
        #     "monthly": df_monthly[['Date', 'LastTradePrice', 'Final_Signal']].tail().to_dict(orient='records')
        # }
        # Extended `final_signals` to include additional values:
        final_signals = {
            "daily": historical_data.reset_index()[[
                'Date', 'LastTradePrice', 'Final_Signal', 'RSI',
                'Momentum', 'Stochastic_Oscillator', 'SMA_10', 'EMA_10'
            ]].tail().to_dict(orient='records'),
            "weekly": df_weekly[['Date', 'LastTradePrice', 'Final_Signal', 'RSI',
                                 'Momentum', 'Stochastic_Oscillator', 'SMA_10', 'EMA_10']].tail().to_dict(
                orient='records'),
            "monthly": df_monthly[['Date', 'LastTradePrice', 'Final_Signal', 'RSI',
                                   'Momentum', 'Stochastic_Oscillator', 'SMA_10', 'EMA_10']].tail().to_dict(
                orient='records')
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
