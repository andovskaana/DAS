import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import sqlite3
import os
import matplotlib.pyplot as plt

from Domasna_4.analysis.DB import DatabaseConnection


def preprocess_data(symbol):
    #Use Singleton to get the shared database connection
    db = DatabaseConnection().get_connection()
    query = f"SELECT Date, Max, Min, Volume FROM StockData WHERE Symbol='{symbol}'"
    data = pd.read_sql(query, db)
    if data.empty:
        return None, None

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
        return None, None, None, None  # Ensure 4 return values even when insufficient data

    time_step = min(time_step, len(scaled_data))
    X, y = create_dataset(scaled_data, time_step)

    if X is None or len(X) < 2:
        return None, None, None, None  # Ensure 4 return values

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

    y_val_pred = model.predict(X_val)
    mse = mean_squared_error(y_val, y_val_pred)
    rmse = np.sqrt(mse)

    last_data = scaled_data[-time_step:].reshape(1, time_step, 3)
    next_price_scaled = model.predict(last_data)
    next_price = scaler.inverse_transform(
        np.concatenate((next_price_scaled, np.zeros((next_price_scaled.shape[0], 2))), axis=1)
    )[:, 0].tolist()

    last_prices = scaler.inverse_transform(scaled_data[-time_step:, :3])[:, 0].tolist()

    graph_path = generate_graph(last_prices, next_price[0], symbol)

    return float(next_price[0]), last_prices, [mse, rmse], graph_path

def generate_graph(last_prices, predicted_price, symbol):
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(last_prices)), last_prices, label="Last Prices", color="blue")
    plt.scatter(len(last_prices), predicted_price, color="red", label="Predicted Price")
    plt.axvline(len(last_prices) - 1, linestyle="--", color="gray", label="Prediction Point")
    plt.title(f"{symbol} Price Prediction")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)

    graph_path = os.path.join("../static", "graphs", f"{symbol}_prediction.png")
    os.makedirs(os.path.dirname(graph_path), exist_ok=True)
    plt.savefig(graph_path)
    plt.close()
    return graph_path