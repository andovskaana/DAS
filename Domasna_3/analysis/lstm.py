import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import sqlite3
import matplotlib.pyplot as plt

DATABASE = 'data/stock_data.db'

def preprocess_data(symbol):
    conn = sqlite3.connect(DATABASE)
    query = f"SELECT Date, Max, Min, Volume FROM StockData WHERE Symbol='{symbol}'"
    data = pd.read_sql(query, conn)
    conn.close()

    # Convert Date column to datetime
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')

    # Clean numeric columns
    for col in ['Max', 'Min']:
        data[col] = data[col].astype(str).str.replace('.', '', regex=False)
        data[col] = data[col].str.replace(',', '.', regex=False)
        data[col] = pd.to_numeric(data[col], errors='coerce')

    data['Volume'] = data['Volume'].astype(str).str.replace(' ', '', regex=False)
    data['Volume'] = data['Volume'].str.replace(',', '.', regex=False)
    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    data.dropna(subset=['Max', 'Min', 'Volume'], inplace=True)
    data = data.sort_values('Date')
    data = data[['Max', 'Min', 'Volume']]

    if len(data) < 2:
        return None, None  # Insufficient data

    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data)
    return scaled_data, scaler

def create_dataset(data, time_step):
    if len(data) < time_step:
        return None, None

    X, y = [], []
    for i in range(time_step, len(data)):
        X.append(data[i - time_step:i])
        y.append(data[i - 1, 0])  # Predicting the 'Max' column
    return np.array(X), np.array(y)

def train_and_predict(symbol, time_step=60):
    scaled_data, scaler = preprocess_data(symbol)
    if scaled_data is None:
        return None, None, "Not enough data for prediction"

    time_step = min(time_step, len(scaled_data))
    X, y = create_dataset(scaled_data, time_step)

    # Return only the last prices if there isn't enough data for training
    if X is None or len(X) < 2:
        # Only take the first 3 columns for inverse transform (Max, Min, Volume)
        last_prices = scaler.inverse_transform(scaled_data[-time_step:, :3])[:, 0]  # Take the first column (Max)
        return None, last_prices, "Not enough data for prediction"

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3, shuffle=False)
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')
    model.fit(X_train, y_train, epochs=10, batch_size=32, validation_data=(X_val, y_val), verbose=0)

    last_data = scaled_data[-time_step:].reshape(1, time_step, scaled_data.shape[1])
    next_price_scaled = model.predict(last_data)

    # Prepare the data for inverse transformation
    # Append zeros for the remaining columns to match the scaler input dimensions
    next_price_full = np.concatenate(
        (next_price_scaled, np.zeros((next_price_scaled.shape[0], scaled_data.shape[1] - 1))),
        axis=1
    )
    next_price = scaler.inverse_transform(next_price_full)[:, 0]

    # Get the last actual prices (use only the first 3 columns for inverse transform)
    last_prices = scaler.inverse_transform(scaled_data[-time_step:, :3])[:, 0]

    return next_price[0], last_prices, None


def generate_graph(last_prices, predicted_price, symbol, is_prediction_available=True):
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(last_prices)), last_prices, label="Last Prices", color="blue")

    if is_prediction_available:
        plt.scatter(len(last_prices), predicted_price, color="red", label="Predicted Price")
        plt.axvline(len(last_prices) - 1, linestyle="--", color="gray", label="Prediction Point")

    plt.title(f"{symbol} Price Prediction")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)

    # Save the graph to a file
    graph_path = f"static/graphs/{symbol}_prediction.png"
    plt.savefig(graph_path)
    plt.close()
    return graph_path