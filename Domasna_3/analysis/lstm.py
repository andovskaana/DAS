from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import numpy as np
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/stock_data.db')
cursor = conn.cursor()

# Query to get the distinct Symbols from the StockData table
query = "SELECT DISTINCT Symbol FROM StockData"
symbols = pd.read_sql(query, conn)

# Close the connection
conn.close()

# List of all unique symbols
symbols = symbols['Symbol'].tolist()

# Now proceed to train models for each symbol
for symbol in symbols:
    # Function to preprocess and create dataset for each issuer
    # Function to preprocess and create dataset for each issuer
    def preprocess_data(symbol):
        # Connect to the SQLite database
        conn = sqlite3.connect('data/stock_data.db')
        query = f"SELECT Date, Max, Min, Volume FROM StockData WHERE Symbol='{symbol}'"
        data = pd.read_sql(query, conn)
        conn.close()

        print(f"\nProcessing data for symbol: {symbol}")
        print(f"Initial data shape: {data.shape}")
        print(f"Initial data preview:\n{data.head()}")

        # Convert Date column to datetime format
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        print(f"After converting 'Date' to datetime. Shape: {data.shape}")
        print(f"Preview:\n{data.head()}")

        # Replace commas with periods in numeric columns and convert to float
        for col in ['Max', 'Min']:
            data[col] = data[col].astype(str).str.replace('.', '', regex=False)  # Remove spaces
            data[col] = data[col].str.replace(',', '.', regex=False)  # Replace commas with periods
            data[col] = pd.to_numeric(data[col], errors='coerce')

        # Handle 'Volume' column
        data['Volume'] = data['Volume'].astype(str).str.replace(' ', '', regex=False)
        data['Volume'] = data['Volume'].str.replace(',', '.', regex=False)
        data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

        # Drop rows with NaN values
        data.dropna(subset=['Max', 'Min', 'Volume'], inplace=True)

        # Sort by Date
        data = data.sort_values('Date')

        # Use only Max, Min, and Volume columns for prediction
        data = data[['Max', 'Min', 'Volume']]

        # Check if the dataset is empty or has fewer than 2 rows
        if data.empty or len(data) < 2:  # Minimum 2 rows needed for model
            print(f"Skipping symbol {symbol} due to insufficient data.")
            return None, None

        # Normalize the data
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(data)

        return scaled_data, scaler


    # Adjust the main loop for dynamic time_step
    for symbol in symbols:
        scaled_data, scaler = preprocess_data(symbol)

        if scaled_data is None:
            continue

        # Dynamically set time_step
        time_step = min(60, len(scaled_data))  # Use length of available data if less than 60


        def create_dataset(data, time_step):
            print(f"Creating dataset with time_step: {time_step}")
            print(f"Data shape: {data.shape}")

            if len(data) < time_step:
                print(f"Insufficient data for the given time_step. Data length: {len(data)}, Time step: {time_step}")
                return [], []  # Return empty arrays if not enough data for at least one sequence

            X, y = [], []
            for i in range(time_step, len(data) + 1):  # Allow the loop to run one additional iteration
                X.append(data[i - time_step:i])  # Use previous 'time_step' values as features
                y.append(data[i - 1, 0])  # Predict the 'Max' column

                # Debug each step (optional, could produce many logs if dataset is large)
                # if len(X) <= 5:  # Limit printing to first few sequences for readability
                #     print(f"Sequence {i - time_step} to {i}: X[-1]={X[-1]}, y[-1]={y[-1]}")

            print(f"Final dataset size: X={len(X)}, y={len(y)}")
            return np.array(X), np.array(y)


        # Create datasets
        X, y = create_dataset(scaled_data, time_step)

        if len(X) == 0 or len(X) == 1:
            print(f"Skipping symbol {symbol} due to insufficient data for time_step {time_step}.")
            continue

        # Proceed with training as usual
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3, shuffle=False)

        X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], X_train.shape[2])
        X_val = X_val.reshape(X_val.shape[0], X_val.shape[1], X_val.shape[2])

        model = Sequential()
        model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])))
        model.add(Dropout(0.2))
        model.add(LSTM(units=50, return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(units=1))

        model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')

        model.fit(X_train, y_train, epochs=10, batch_size=32, validation_data=(X_val, y_val), verbose=1)

        y_pred = model.predict(X_val)

        y_pred_inv = scaler.inverse_transform(np.concatenate((y_pred, np.zeros((y_pred.shape[0], 2))), axis=1))[:, 0]
        y_val_inv = scaler.inverse_transform(
            np.concatenate((y_val.reshape(-1, 1), np.zeros((y_val.shape[0], 2))), axis=1))[:, 0]

        mse = mean_squared_error(y_val_inv, y_pred_inv)
        rmse = np.sqrt(mse)

        print(f"Model evaluation for {symbol}:")
        print(f'Mean Squared Error: {mse}')
        print(f'Root Mean Squared Error: {rmse}')

        last_data = scaled_data[-time_step:].reshape(1, time_step, 3)
        next_price_scaled = model.predict(last_data)
        next_price = scaler.inverse_transform(
            np.concatenate((next_price_scaled, np.zeros((next_price_scaled.shape[0], 2))), axis=1))[:, 0]

        print(f'Predicted Next Stock Price for {symbol}: {next_price[0]}')
