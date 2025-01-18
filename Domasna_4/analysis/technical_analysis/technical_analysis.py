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
