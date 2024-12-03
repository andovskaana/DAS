import sqlite3
import os
import csv


# Function to create the database and necessary tables
def init_createDB():
    data_folder = 'data'
    db_path = os.path.join(data_folder, 'stock_data.db')
    os.makedirs(data_folder, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table for tracking the last date scraped for each symbol
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SymbolTracking (
        Symbol TEXT PRIMARY KEY,
        LastDate TEXT
    )
    ''')

    # Main table for storing detailed stock data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS StockData (
        Symbol TEXT,
        Date TEXT,
        LastTradePrice REAL,
        Max REAL,
        Min REAL,
        AvgPrice REAL,
        PercentageChange REAL,
        Volume INTEGER,
        TurnoverInBEST TEXT,
        TotalTurnover TEXT,
        PRIMARY KEY (Symbol, Date),
        FOREIGN KEY (Symbol) REFERENCES SymbolTracking(Symbol)
    )
    ''')

    # Insert initial symbols from the CSV file into SymbolTracking
    with open(os.path.join(".", 'symbols.csv'), 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            symbol = row['issuer_code']
            cursor.execute('''
            INSERT OR IGNORE INTO SymbolTracking (Symbol, LastDate) VALUES (?, NULL)
            ''', (symbol,))

    conn.commit()
    conn.close()
   # print("Database successfully created!")


# Update the last date scraped for a given symbol
def update_last_date(symbol, last_date):
    db_path = os.path.join('data', 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    UPDATE SymbolTracking
    SET LastDate = ?
    WHERE Symbol = ?
    ''', (last_date, symbol))

    conn.commit()
    conn.close()


# Insert stock data into StockData table
def insert_stock_data(symbol, data):
    # db_path = os.path.join('data', 'stock_data.db')
    # conn = sqlite3.connect(db_path)
    # cursor = conn.cursor()
    #
    # for row in data:
    #     date, last_trade_price, max_price, min_price, avg_price, percentage_change, volume, turnover_best, total_turnover = row
    #     cursor.execute('''
    #     INSERT OR IGNORE INTO StockData (
    #         Symbol, Date, LastTradePrice, Max, Min, AvgPrice, PercentageChange,
    #         Volume, TurnoverInBEST, TotalTurnover
    #     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    #     ''', (symbol, date, last_trade_price, max_price, min_price, avg_price,
    #           percentage_change, volume, turnover_best, total_turnover))
    #
    # conn.commit()
    # conn.close()
    db_path = os.path.join('data', 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Prepare data in the format needed for executemany
    bulk_data = [
        (symbol, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8])
        for row in data
    ]

    cursor.executemany('''
           INSERT OR IGNORE INTO StockData (
               Symbol, Date, LastTradePrice, Max, Min, AvgPrice, PercentageChange,
               Volume, TurnoverInBEST, TotalTurnover
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       ''', bulk_data)

    conn.commit()
    conn.close()


# Update or insert stock data and update the last date scraped for a given symbol
def update_data(symbol, data, last_date):
    # Insert or update stock data in the StockData table
    insert_stock_data(symbol, data)

    # Update the last date scraped for the symbol
    update_last_date(symbol, last_date)


# Retrieve the last saved date for a symbol to resume scraping
def get_last_saved_date(symbol):
    db_path = os.path.join('data', 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    SELECT LastDate FROM SymbolTracking WHERE Symbol = ?
    ''', (symbol,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else None


# Testing function to view the tracker database
def view_trackerDB():
    db_path = os.path.join('data', 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM SymbolTracking')
    symbols = cursor.fetchall()

    conn.close()

    print("Symbols in SymbolTracking:")
    for symbol, last_date in symbols:
        print(f"Symbol: {symbol}, Last Date: {last_date if last_date else 'NULL'}")


# Testing function to view the stock data
def view_stock_data():
    db_path = os.path.join('data', 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM StockData')
    stock_data = cursor.fetchall()

    conn.close()

    print("Stock data:")
    for row in stock_data:
        print(row)
