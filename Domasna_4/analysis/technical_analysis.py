# import sqlite3
# import pandas as pd
# import ta
# from flask import Flask, render_template
#
# app = Flask(__name__)
#
#
# # Function to fetch stock data from the SQLite database
# def fetch_stock_data_from_db():
#     conn = sqlite3.connect('stock_data.db')
#     query = 'SELECT Date, LastTradePrice, Max, Min FROM StockData'
#     df = pd.read_sql(query, conn)
#     conn.close()
#     return df
#
#
# # Function to calculate technical indicators
# def calculate_technical_indicators(df):
#     # Moving Averages (MA)
#     df['SMA_20'] = df['LastTradePrice'].rolling(window=20).mean()  # Simple Moving Average
#     df['EMA_20'] = df['LastTradePrice'].ewm(span=20, adjust=False).mean()  # Exponential Moving Average
#     df['SMA_50'] = df['LastTradePrice'].rolling(window=50).mean()
#     df['EMA_50'] = df['LastTradePrice'].ewm(span=50, adjust=False).mean()
#     df['SMA_200'] = df['LastTradePrice'].rolling(window=200).mean()
#
#     # Oscillators
#     df['RSI'] = ta.momentum.RSIIndicator(df['LastTradePrice'], window=14).rsi()  # Relative Strength Index
#     df['Stochastic'] = ta.momentum.StochasticOscillator(df['Max'], df['Min'], df['LastTradePrice'], window=14,
#                                                         smooth_window=3).stoch()
#     df['CCI'] = ta.trend.CCIIndicator(df['Max'], df['Min'], df['LastTradePrice'],
#                                       window=20).cci()  # Commodity Channel Index
#     df['MACD'] = ta.trend.MACD(df['LastTradePrice']).macd()  # Moving Average Convergence Divergence
#     df['MFI'] = ta.volume.MFIIndicator(df['Max'], df['Min'], df['LastTradePrice'], df['Volume'],
#                                        window=14).money_flow_index()  # Money Flow Index
#
#     return df
#
#
# # Function to calculate indicators for different time periods
# def calculate_indicators_for_time_periods(df):
#     df['1_day'] = df['LastTradePrice'].rolling(window=1).mean()
#     df['1_week'] = df['LastTradePrice'].rolling(window=5).mean()  # assuming 5 trading days in a week
#     df['1_month'] = df['LastTradePrice'].rolling(window=20).mean()  # assuming 20 trading days in a month
#
#     # Calculate technical indicators
#     df = calculate_technical_indicators(df)
#
#     return df
#
#
# @app.route('/')
# def index():
#     # Fetch stock data from the database
#     df = fetch_stock_data_from_db()
#
#     # Calculate indicators
#     df = calculate_indicators_for_time_periods(df)
#
#     # Prepare data for oscillators and moving averages to display
#     oscillators = {
#         'RSI': df['RSI'].iloc[-1],
#         'Stochastic': df['Stochastic'].iloc[-1],
#         'CCI': df['CCI'].iloc[-1],
#         'MACD': df['MACD'].iloc[-1],
#         'MFI': df['MFI'].iloc[-1]
#     }
#
#     moving_averages = {
#         'SMA_20': df['SMA_20'].iloc[-1],
#         'EMA_20': df['EMA_20'].iloc[-1],
#         'SMA_50': df['SMA_50'].iloc[-1],
#         'EMA_50': df['EMA_50'].iloc[-1],
#         'SMA_200': df['SMA_200'].iloc[-1]
#     }
#
#     # Render the HTML template and pass data to it
#     return render_template('index.html', oscillators=oscillators, moving_averages=moving_averages)
#
#
# if __name__ == '__main__':
#     app.run(debug=True)
import os
import sqlite3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf

def clean_numeric_column(value):
    """Converts numeric strings with thousands separators ('.') and decimal commas (',') to float."""
    if isinstance(value, str):
        try:
            return float(value.replace('.', '').replace(',', '.'))
        except ValueError:
            return np.nan
    elif isinstance(value, (int, float)):
        return value  # Already numeric
    else:
        return np.nan

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_momentum(data, window):
    return (data - data.shift(window)) / data.shift(window) * 100

def calculate_williams_percent_range(data, high, low, window):
    highest_high = high.rolling(window=window).max()
    lowest_low = low.rolling(window=window).min()
    return -100 * (highest_high - data) / (highest_high - lowest_low)

def calculate_stochastic_oscillator(data, high, low, window):
    highest_high = high.rolling(window=window).max()
    lowest_low = low.rolling(window=window).min()
    return 100 * (data - lowest_low) / (highest_high - lowest_low)

def calculate_sma(data, window):
    return data.rolling(window=window).mean()

def calculate_ema(data, window):
    return data.ewm(span=window, adjust=False).mean()

def calculate_bollinger_bands(data, window):
    sma = calculate_sma(data, window)
    std_dev = data.rolling(window=window).std()
    upper_band = sma + (2 * std_dev)
    lower_band = sma - (2 * std_dev)
    return sma, upper_band, lower_band

def calculate_ultimate_oscillator(data, high, low, window1=7, window2=14, window3=28):
    buying_pressure = data - low
    true_range = high - low

    avg1 = buying_pressure.rolling(window=window1).sum() / true_range.rolling(window=window1).sum()
    avg2 = buying_pressure.rolling(window=window2).sum() / true_range.rolling(window=window2).sum()
    avg3 = buying_pressure.rolling(window=window3).sum() / true_range.rolling(window=window3).sum()

    ultimate_oscillator = 100 * ((4 * avg1) + (2 * avg2) + avg3) / 7
    return ultimate_oscillator

def generate_signals(df):
    # Check if required columns exist
    required_columns = ['RSI', 'Momentum', 'Williams_%R', 'Stochastic_Oscillator']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        df['Final_Signal'] = 'Not Sufficient Information'
        return df

    # Generate individual signals
    df['RSI_Signal'] = np.where(df['RSI'] < 30, 'Buy',
                                np.where(df['RSI'] > 70, 'Sell', 'Hold'))
    df['Momentum_Signal'] = np.where(df['Momentum'] > 0, 'Buy', 'Sell')
    df['WPR_Signal'] = np.where(df['Williams_%R'] < -80, 'Buy',
                                 np.where(df['Williams_%R'] > -20, 'Sell', 'Hold'))
    df['Stochastic_Signal'] = np.where(df['Stochastic_Oscillator'] < 20, 'Buy',
                                        np.where(df['Stochastic_Oscillator'] > 80, 'Sell', 'Hold'))

    # Safely compute the mode for Final_Signal
    signal_mode = df[['RSI_Signal', 'Momentum_Signal', 'WPR_Signal', 'Stochastic_Signal']].mode(axis=1)
    if signal_mode.empty:
        df['Final_Signal'] = 'Hold'
    else:
        df['Final_Signal'] = signal_mode[0].fillna('Hold')  # Default to 'Hold' for NaN values

    return df



def plot_charts(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], df['LastTradePrice'], label='Price', color='blue')
    plt.plot(df['Date'], df['SMA_10'], label='SMA (10)', color='orange')
    plt.fill_between(df['Date'], df['BB_Lower'], df['BB_Upper'], color='gray', alpha=0.3, label='Bollinger Bands')
    plt.legend()
    plt.title('Stock Price with Technical Indicators')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], df['RSI'], label='RSI', color='purple')
    plt.axhline(70, color='red', linestyle='--', label='Overbought (70)')
    plt.axhline(30, color='green', linestyle='--', label='Oversold (30)')
    plt.legend()
    plt.title('Relative Strength Index (RSI)')
    plt.xlabel('Date')
    plt.ylabel('RSI')
    plt.grid()
    plt.show()


# def analyze_data(df):
#     df['RSI'] = calculate_rsi(df['LastTradePrice'])
#     df['Momentum'] = calculate_momentum(df['LastTradePrice'], 10)
#     df['Williams_%R'] = calculate_williams_percent_range(df['LastTradePrice'], df['Max'], df['Min'], 14)
#     df['Stochastic_Oscillator'] = calculate_stochastic_oscillator(df['LastTradePrice'], df['Max'], df['Min'], 14)
#     df['SMA_10'] = calculate_sma(df['LastTradePrice'], 10)
#     df['SMA_20'] = calculate_sma(df['LastTradePrice'], 20)  # New Indicator
#     df['EMA_10'] = calculate_ema(df['LastTradePrice'], 10)
#     df['EMA_50'] = calculate_ema(df['LastTradePrice'], 50)  # New Indicator
#     df['BB_MA'], df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['LastTradePrice'], 10)
#     df['Ultimate_Oscillator'] = calculate_ultimate_oscillator(df['LastTradePrice'], df['Max'], df['Min'])
#
#     df = generate_signals(df)
#   return df
def analyze_data(df):
    df['RSI'] = calculate_rsi(df['LastTradePrice'])
    df['Momentum'] = calculate_momentum(df['LastTradePrice'], 10)
    df['Williams_%R'] = calculate_williams_percent_range(df['LastTradePrice'], df['Max'], df['Min'], 14)
    df['Stochastic_Oscillator'] = calculate_stochastic_oscillator(df['LastTradePrice'], df['Max'], df['Min'], 14)
    df['SMA_10'] = calculate_sma(df['LastTradePrice'], 10)
    df['SMA_20'] = calculate_sma(df['LastTradePrice'], 20)  # New SMA
    df['SMA_50'] = calculate_sma(df['LastTradePrice'], 50)  # New SMA
    df['EMA_10'] = calculate_ema(df['LastTradePrice'], 10)
    df['EMA_20'] = calculate_ema(df['LastTradePrice'], 20)  # New EMA
    df['EMA_50'] = calculate_ema(df['LastTradePrice'], 50)  # New EMA
    df['BB_MA'], df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['LastTradePrice'], 10)
    df['Ultimate_Oscillator'] = calculate_ultimate_oscillator(df['LastTradePrice'], df['Max'], df['Min'])

    df = generate_signals(df)
    return df

def get_technical_analysis(symbol, start_date, end_date):
    # Example: Fetch the stock data from the database
    # Assume you have a function `get_stock_data_from_db` that queries the database
    stock_data = get_stock_data_from_db(symbol, start_date, end_date)

    if stock_data is None or stock_data.empty:
        return None

    stock_data['RSI'] = calculate_rsi(stock_data['LastTradePrice'])
    stock_data['Momentum'] = calculate_momentum(stock_data['LastTradePrice'], 10)
    stock_data['SMA'] = calculate_sma(stock_data['LastTradePrice'], 10)

    # You can extend the logic to include other indicators or signals

    # Create signals based on analysis
    stock_data['Signal'] = stock_data['RSI'].apply(lambda x: 'Buy' if x > 70 else ('Sell' if x < 30 else 'Hold'))

    # Returning the analysis as a dictionary
    return stock_data[['Date', 'RSI', 'Momentum', 'SMA', 'Signal']].to_dict(orient='records')

# Function to fetch stock data from your database
def get_stock_data_from_db(symbol, start_date, end_date):
    # Connect to the database and query the stock data for the given symbol and date range
    # You can use the existing function you have for fetching data from SQLite
    conn = sqlite3.connect('data/stock_data.db')
    query = """
        SELECT Date, LastTradePrice, Max, Min, Volume
        FROM StockData
        WHERE Symbol = ? AND Date BETWEEN ? AND ?
        ORDER BY Date ASC
    """
    return pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))