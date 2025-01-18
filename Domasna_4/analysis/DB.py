import sqlite3
import os
import csv

class DatabaseConnection:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseConnection, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_connection()
        return cls._instance

    def _initialize_connection(self):
        """Initialize the database connection."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, 'data', 'stock_data.db')
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)

    def get_connection(self):
        """Get the database connection, reopening it if necessary."""
        try:
            # Test the connection with a simple query
            self.connection.execute("SELECT 1")
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            print("Reopening closed database connection...")
            self._initialize_connection()  # Reinitialize the connection
        return self.connection

    def close_connection(self):
        """Close the database connection."""
        if hasattr(self, 'connection'):
            self.connection.close()
            self.connection = None

def test_database_connection():
    """Check if the database connection is successful at startup."""
    try:
        db = DatabaseConnection().get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT 1")  # Simple test query
        print("Database connection successful!")
        cursor.close()
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

# Function to create the database and necessary tables
def init_createDB():
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
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
            Volume TEXT,
            TurnoverInBEST TEXT,
            TotalTurnover TEXT,
            PRIMARY KEY (Symbol, Date),
            FOREIGN KEY (Symbol) REFERENCES SymbolTracking(Symbol)
        )
        ''')

        # Insert initial symbols from the CSV file into SymbolTracking
        with open(os.path.join("../", 'symbols.csv'), 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                symbol = row['issuer_code']
                cursor.execute('''
                INSERT OR IGNORE INTO SymbolTracking (Symbol, LastDate) VALUES (?, NULL)
                ''', (symbol,))
        db.commit()
    finally:
        cursor.close()


# Update the last date scraped for a given symbol
def update_last_date(symbol, last_date):
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute('''
        UPDATE SymbolTracking
        SET LastDate = ?
        WHERE Symbol = ?
        ''', (last_date, symbol))
        db.commit()
    finally:
        cursor.close()


# Insert stock data into StockData table
def insert_stock_data(symbol, data):
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
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
        db.commit()
    finally:
        cursor.close()


# Update or insert stock data and update the last date scraped for a given symbol
def update_data(symbol, data, last_date):
    # Insert or update stock data in the StockData table
    insert_stock_data(symbol, data)

    # Update the last date scraped for the symbol
    update_last_date(symbol, last_date)


# Retrieve the last saved date for a symbol to resume scraping
def get_last_saved_date(symbol):
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute('''
        SELECT LastDate FROM SymbolTracking WHERE Symbol = ?
        ''', (symbol,))
        result = cursor.fetchone()
        db.commit()
    finally:
        cursor.close()
    return result[0] if result else None


# Testing function to view the tracker database
def view_trackerDB():
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute('SELECT * FROM SymbolTracking')
        symbols = cursor.fetchall()
        db.commit()
    finally:
        cursor.close()

    print("Symbols in SymbolTracking:")
    for symbol, last_date in symbols:
        print(f"Symbol: {symbol}, Last Date: {last_date if last_date else 'NULL'}")


# Testing function to view the stock data
def view_stock_data():
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute('SELECT * FROM StockData')
        stock_data = cursor.fetchall()
        db.commit()
    finally:
        cursor.close()

    print("Stock data:")
    for row in stock_data:
        print(row)

#Fetch symbols to populate drop down
def fetch_symbols():
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT DISTINCT Symbol FROM StockData")
        issuers = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
    return issuers if issuers else None
def fetch_issuers():
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT DISTINCT issuer FROM recommendations")
        issuers = cursor.fetchall()
    finally:
        cursor.close()
    return issuers if issuers else None

def extract_issuer_rows(from_date, issuer, to_date):
    query = """
        SELECT * 
        FROM StockData 
        WHERE 1=1
    """
    params = []
    if from_date:
        query += """
        AND CAST(SUBSTR(Date, -4, 4) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, 1, INSTR(Date, '/') - 1) AS INTEGER)) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, INSTR(Date, '/') + 1, LENGTH(Date) - INSTR(Date, '/')) AS INTEGER))
             AS TEXT) >= ?
        """
        params.append(from_date)
    if to_date:
        query += """
        AND CAST(SUBSTR(Date, -4, 4) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, 1, INSTR(Date, '/') - 1) AS INTEGER)) || '-' ||
                 printf('%02d', CAST(SUBSTR(Date, INSTR(Date, '/') + 1, LENGTH(Date) - INSTR(Date, '/')) AS INTEGER))
             AS TEXT) <= ?
        """
        params.append(to_date)
    if issuer != "ALL":
        query += " AND Symbol = ?"
        params.append(issuer)
    # Add ORDER BY clause to sort by date
    query += """
    ORDER BY CAST(SUBSTR(Date, -4, 4) || '-' ||
                  printf('%02d', CAST(SUBSTR(Date, 1, INSTR(Date, '/') - 1) AS INTEGER)) || '-' ||
                  printf('%02d', CAST(SUBSTR(Date, INSTR(Date, '/') + 1, LENGTH(Date) - INSTR(Date, '/')) AS INTEGER))
              AS TEXT) DESC
    """
    # Fetch filtered rows from the database
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    finally:
        cursor.close()
    return rows if rows else None

def retrieve_top_10():
    db = DatabaseConnection().get_connection()
    cursor = db.cursor()
    try:
    # Find the latest date in the database
        latest_date_query = """
        SELECT Date 
        FROM StockData
        ORDER BY CAST(SUBSTR(Date, 7, 4) || SUBSTR(Date, 1, 2) || SUBSTR(Date, 4, 2) AS INTEGER) DESC
        LIMIT 1
        """
        cursor.execute(latest_date_query)
        latest_date = cursor.fetchone()
        latest_date = latest_date[0] if latest_date else None
        if not latest_date:
            # No data in the database
            stocks = []
        else:
            # Retrieve the top 10 most tradeable stocks
            query = """
            SELECT 
                Symbol, 
                AvgPrice,
                PercentageChange,
                CAST(REPLACE(Volume, '.', '') AS INTEGER) AS DailyTotalVolume,
                TotalTurnover
            FROM StockData
            WHERE Date = ?
            ORDER BY DailyTotalVolume DESC
            LIMIT 10
            """
            cursor.execute(query, (latest_date,))
            stocks = cursor.fetchall()
    finally:
        cursor.close()
    return stocks