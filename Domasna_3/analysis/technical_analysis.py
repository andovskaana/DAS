import os
import sqlite3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf


# # Define necessary functions
# data_folder = 'data'
# db_path = os.path.join(data_folder, 'stock_data.db')
#
# # Connect to the SQLite database
# conn = sqlite3.connect(db_path)
#
# # Define the stock name you want to filter by
# stock_name = 'YourSpecificStockName'
#
# # Execute the query to retrieve the relevant data for the specific stock
# query = f"SELECT Date, LastTradePrice, Max, Min, Volume FROM stock_data WHERE StockName = ? ORDER BY Date;"
# df = pd.read_sql(query, conn, params=(stock_name,))

# # Close the connection
# conn.close()
def clean_numeric_column(value):
    """Converts numeric strings with thousands separators and commas to float."""
    try:
        return float(value.replace('.', '').replace(',', '.'))
    except ValueError:
        return np.nan


def calculate_moving_average(df, window):
    df[f'MA_{window}'] = df['LastTradePrice'].rolling(window=window).mean()
    return df


def calculate_rsi(df, window=14):
    delta = df['LastTradePrice'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def calculate_bollinger_bands(df, window=5):
    df['BB_MA'] = df['LastTradePrice'].rolling(window=window).mean()
    df['BB_Upper'] = df['BB_MA'] + (df['LastTradePrice'].rolling(window=window).std() * 2)
    df['BB_Lower'] = df['BB_MA'] - (df['LastTradePrice'].rolling(window=window).std() * 2)
    return df


def generate_signals(df):
    # Moving Average Signal
    df['MA_Signal'] = np.where(df['MA_3'] > df['LastTradePrice'], 'Sell',
                               np.where(df['MA_3'] < df['LastTradePrice'], 'Buy', 'Hold'))

    # RSI Signal
    df['RSI_Signal'] = np.where(df['RSI'] < 30, 'Buy',
                                np.where(df['RSI'] > 70, 'Sell', 'Hold'))

    # Bollinger Bands Signal
    df['BB_Signal'] = np.where(df['LastTradePrice'] > df['BB_Upper'], 'Sell',
                               np.where(df['LastTradePrice'] < df['BB_Lower'], 'Buy', 'Hold'))

    # Final Signal
    df['Final_Signal'] = df[['MA_Signal', 'RSI_Signal', 'BB_Signal']].mode(axis=1)[0]
    return df


def extend_to_time_frames(df):
    # Resample data
    df_weekly = df.resample('W-Mon', on='Date').agg({
        'LastTradePrice': 'mean',
        'Max': 'max',
        'Min': 'min',
        'Volume': 'sum'
    }).reset_index()

    df_monthly = df.resample('ME', on='Date').agg({
        'LastTradePrice': 'mean',
        'Max': 'max',
        'Min': 'min',
        'Volume': 'sum'
    }).reset_index()

    # Apply indicator calculations
    df_daily = calculate_moving_average(df, 3)
    df_daily = calculate_moving_average(df_daily, 5)
    df_daily = generate_signals(calculate_bollinger_bands(calculate_rsi(df_daily, 3), 5))

    df_weekly = calculate_moving_average(df_weekly, 3)
    df_weekly = calculate_moving_average(df_weekly, 5)
    df_weekly = generate_signals(calculate_bollinger_bands(calculate_rsi(df_weekly, 3), 5))

    df_monthly = calculate_moving_average(df_monthly, 3)
    df_monthly = calculate_moving_average(df_monthly, 5)
    df_monthly = generate_signals(calculate_bollinger_bands(calculate_rsi(df_monthly, 3), 5))

    return df_daily, df_weekly, df_monthly


def plot_charts(df):
    # Line Chart with Moving Averages and Bollinger Bands
    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], df['LastTradePrice'], label='Price', color='blue')
    plt.plot(df['Date'], df['MA_3'], label='3-Day MA', color='orange')
    plt.plot(df['Date'], df['MA_5'], label='5-Day MA', color='green')
    plt.fill_between(df['Date'], df['BB_Lower'], df['BB_Upper'], color='gray', alpha=0.3, label='Bollinger Bands')
    plt.legend()
    plt.title('Stock Price with Moving Averages and Bollinger Bands')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid()
    plt.show()

    # RSI Chart
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

    # Volume and Price Overlay
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(df['Date'], df['Volume'], color='gray', alpha=0.5, label='Volume')
    ax1.set_ylabel('Volume')
    ax1.set_xlabel('Date')
    ax2 = ax1.twinx()
    ax2.plot(df['Date'], df['LastTradePrice'], color='blue', label='Price')
    ax2.set_ylabel('Price')
    fig.suptitle('Price and Volume')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.show()

    # Candlestick Chart
    df_candlestick = df[['Date', 'LastTradePrice', 'Max', 'Min']].copy()
    df_candlestick.columns = ['Date', 'Close', 'High', 'Low']  # Rename columns for mplfinance
    df_candlestick['Open'] = df_candlestick['Close']  # Add Open column (if missing)
    df_candlestick.set_index('Date', inplace=True)
    mpf.plot(df_candlestick, type='candle', style='charles', title='Candlestick Chart', volume=False)




