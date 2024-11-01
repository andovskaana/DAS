import sqlite3
import os
import csv

# Funkcija za kreiranje na Data Bazite potrebni
def init_createDB():

    data_folder = 'data'
    db_path = os.path.join(data_folder, 'stock_data.db')
    os.makedirs(data_folder, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # DB za cuvanje na glavnite podatoci vo DB kako datum i symbol
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SymbolTracking (
        Symbol TEXT PRIMARY KEY,
        LastDate TEXT
    )
    ''')

    # Glavna DB so site detalni informacii
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
        TurnoverInBEST REAL,
        TotalTurnover REAL,
        PRIMARY KEY (Symbol, Date),
        FOREIGN KEY (Symbol) REFERENCES SymbolTracking(Symbol)
    )
    ''')

    # Vnesuvanje na inicijalni filteri vo Trackerot
    with open(os.path.join(".", 'symbols.csv'), 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            symbol = row['issuer_code']
            cursor.execute('''
                INSERT OR IGNORE INTO SymbolTracking (Symbol, LastDate) VALUES (?, NULL)
            ''', (symbol,))
    conn.commit()
    conn.close()
    print(f"DB uspeshno kreirani!")

# Prikaz na trackerot (testing)
def view_trackerDB():
    db_path = os.path.join('data', 'stock_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Retrieve all symbols from SymbolTracking
    cursor.execute('SELECT * FROM SymbolTracking')
    symbols = cursor.fetchall()

    conn.close()

    # Display the symbols
    print("Symbols in SymbolTracking:")
    for symbol, last_date in symbols:
        print(f"Symbol: {symbol}, Last Date: {last_date if last_date else 'NULL'}")

