import sqlite3
import os
import pandas as pd
import mplfinance as mpf

from flask import Flask, jsonify, request
from technical_analysis import plot_charts, generate_signals, calculate_bollinger_bands, calculate_rsi, clean_numeric_column, calculate_sma, calculate_stochastic_oscillator, calculate_ema, calculate_williams_percent_range, calculate_momentum

app = Flask(__name__)

@app.route('/api/technical_analysis', methods=['POST'])
def technical_analysis():
    data = request.json
    symbol = data['symbol']
    if not symbol:
        return jsonify({"error": "Symbol not provided"}), 400
    try:
        data_folder = '../data'
        db_path = os.path.join(data_folder, 'stock_data.db')
        historical_data = get_historical_data(db_path, symbol)
        result = process_historical_data(historical_data, symbol)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_historical_data(db_path, stock_symbol):
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
    return historical_data

def process_historical_data(historical_data, stock_symbol):
    """
    Processes historical stock data to generate candlestick data, chart path, and final signals.

    Args:
        historical_data (pd.DataFrame): The input historical data.
        stock_symbol (str): The stock symbol for naming outputs.

    Returns:
        dict: A dictionary containing candlestick_data, chart_path, and final_signals.
    """
    if historical_data.empty:
        return {
            "error": "No data found for the selected stock symbol.",
            "candlestick_data": None,
            "chart_path": None,
            "final_signals": None
        }

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
        historical_data['LastTradePrice'], 10
    )
    historical_data = generate_signals(historical_data)

    # Resample data for weekly and monthly signals
    historical_data.set_index('Date', inplace=True)

    # Weekly resampling
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
    df_monthly = historical_data.resample('ME').agg({
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

    # Reset indices for JSON serialization
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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(current_dir, '..', 'static', 'charts')
    chart_path = os.path.join(static_dir, chart_filename)
    mpf.plot(df_candlestick, type='candle', style='charles', title=f'Candlestick Chart for {stock_symbol}',
             volume=False, savefig=chart_path)

    # Extended `final_signals` to include additional values:
    final_signals = {
        "daily": historical_data.reset_index()[[
            'Date', 'LastTradePrice', 'Final_Signal', 'RSI',
            'Momentum', 'Stochastic_Oscillator', 'SMA_10', 'EMA_10'
        ]].tail().to_dict(orient='records'),
        "weekly": df_weekly[['Date', 'LastTradePrice', 'Final_Signal', 'RSI', 'Momentum',
                             'Stochastic_Oscillator', 'SMA_10', 'EMA_10']].tail().to_dict(orient='records'),
        "monthly": df_monthly[['Date', 'LastTradePrice', 'Final_Signal', 'RSI', 'Momentum',
                               'Stochastic_Oscillator', 'SMA_10', 'EMA_10']].tail().to_dict(orient='records')
    }

    return {
        "candlestick_data": candlestick_data,
        "chart_path": chart_path,
        "final_signals": final_signals
    }

if __name__ == '__main__':
    app.run(port=5001)