import os

import numpy as np
import pandas as pd
import requests

from flask import Flask, jsonify, request

from strategies.rsi import RSIIndicator
from strategies.momentum import MomentumIndicator
from strategies.sma import SMAIndicator
from strategies.ema import EMAIndicator
from strategies.williams_percent_range import WilliamsPercentRangeIndicator
from strategies.bollinger_bands import BollingerBandsIndicator
from strategies.stochastic_oscillator import StochasticOscillatorIndicator
from technical_analysis import TechnicalAnalysisContext
from visualisation import generate_candlestick_data

app = Flask(__name__)
# Get DB_SERVICE_URL from environment, default to localhost if not set
DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://localhost:5005/api/db/query")


@app.route('/api/technical_analysis', methods=['POST'])
def technical_analysis():
    data = request.json
    symbol = data['symbol']
    if not symbol:
        return jsonify({"error": "Symbol not provided"}), 400
    try:
        historical_data = get_historical_data(symbol)
        result = process_historical_data(historical_data, symbol)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_historical_data(stock_symbol):
    query = f"SELECT Date, LastTradePrice, Max, Min, Volume FROM StockData WHERE Symbol = '{stock_symbol}' ORDER BY Date ASC"
    response = requests.post(DB_SERVICE_URL, json={"query": query})

    if response.status_code != 200:
        raise Exception(f"Database query failed: {response.json().get('error')}")

    historical_data = pd.DataFrame(response.json())

    return historical_data


def initialize_strategy_context():
    # Initialize the strategy context
    context = TechnicalAnalysisContext()
    context.add_strategy('RSI', RSIIndicator())
    context.add_strategy('Momentum', MomentumIndicator())
    context.add_strategy('SMA', SMAIndicator())
    context.add_strategy('EMA', EMAIndicator())
    context.add_strategy('Williams', WilliamsPercentRangeIndicator())
    context.add_strategy('BollingerBands', BollingerBandsIndicator())
    context.add_strategy('StochasticOscillator', StochasticOscillatorIndicator())
    return context


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

    # Apply strategies for indicators
    context = initialize_strategy_context()
    # Analyze data using the strategies
    historical_data = analyze_data(historical_data, context)

    # Generate signals (if not already generated in analyze_data)
    df_monthly, df_weekly, historical_data = resample_data(historical_data)

    # Generate candlestick data
    candlestick_data, chart_path = generate_candlestick_data(historical_data, stock_symbol)

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


def resample_data(historical_data):
    historical_data = generate_signals(historical_data)
    # Resample data for weekly and monthly signals
    historical_data.set_index('Date', inplace=True)
    try:
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
    except Exception as e:
        df_weekly = pd.DataFrame(columns=['Date', 'LastTradePrice', 'Final_Signal'])
        df_weekly['Final_Signal'] = 'Not Sufficient Information'
    if df_weekly.empty:
        df_weekly = pd.DataFrame(columns=['Date', 'LastTradePrice', 'Final_Signal'])
        df_weekly['Final_Signal'] = 'Not Sufficient Information'
    else:
        df_weekly = generate_signals(df_weekly)
    try:
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
    except Exception as e:
        df_monthly = pd.DataFrame(columns=['Date', 'LastTradePrice', 'Final_Signal'])
        df_monthly['Final_Signal'] = 'Not Sufficient Information'
    if df_monthly.empty:
        df_monthly = pd.DataFrame(columns=['Date', 'LastTradePrice', 'Final_Signal'])
        df_monthly['Final_Signal'] = 'Not Sufficient Information'
    else:
        df_monthly = generate_signals(df_monthly)
    # Reset indices for JSON serialization
    df_weekly.reset_index(inplace=True)
    df_monthly.reset_index(inplace=True)
    return df_monthly, df_weekly, historical_data


def clean_numeric_column(value):
    """Converts numeric strings with thousands separators ('.') and decimal commas (',') to float."""
    if isinstance(value, str):
        try:
            return float(value.replace('.', '').replace(',', '.'))
        except ValueError:
            return 0
    elif isinstance(value, (int, float)):
        return value  # Already numeric
    else:
        return 0


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


def analyze_data(df, context):
    # Apply the strategies
    df['RSI'] = context.execute_strategy('RSI', df['LastTradePrice'])
    df['Momentum'] = context.execute_strategy('SMA', df['LastTradePrice'].diff(),
                                              window=10)  # Assuming momentum uses SMA logic
    df['Williams_%R'] = context.execute_strategy(
        'Williams',
        df['LastTradePrice'],
        high=df['Max'],
        low=df['Min'],
        window=14
    )
    df['Stochastic_Oscillator'] = context.execute_strategy(
        'StochasticOscillator',
        df['LastTradePrice'],
        high=df['Max'],
        low=df['Min'],
        window=14
    )
    df['BB_MA'], df['BB_Upper'], df['BB_Lower'] = context.execute_strategy(
        'BollingerBands',
        df['LastTradePrice'],
        window=10
    )
    df['SMA_10'] = context.execute_strategy('SMA', df['LastTradePrice'], window=10)
    df['SMA_20'] = context.execute_strategy('SMA', df['LastTradePrice'], window=20)
    df['SMA_50'] = context.execute_strategy('SMA', df['LastTradePrice'], window=50)
    df['EMA_10'] = context.execute_strategy('EMA', df['LastTradePrice'], window=10)
    df['EMA_20'] = context.execute_strategy('EMA', df['LastTradePrice'], window=20)
    df['EMA_50'] = context.execute_strategy('EMA', df['LastTradePrice'], window=50)
    df['BB_MA'], df['BB_Upper'], df['BB_Lower'] = context.execute_strategy('BollingerBands', df['LastTradePrice'],
                                                                           window=10)

    # Ultimate Oscillator calculation (not part of the strategies yet)
    df['Ultimate_Oscillator'] = (df['LastTradePrice'] - df['Min']) / (df['Max'] - df['Min'])  # Placeholder logic

    # Generate signals
    df = generate_signals(df)

    return df


if __name__ == '__main__':
    app.run(port=5001)
