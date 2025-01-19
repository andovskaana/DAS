import os
import matplotlib.pyplot as plt
import mplfinance as mpf

def generate_candlestick_data(historical_data, stock_symbol):
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
    return candlestick_data, chart_path

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