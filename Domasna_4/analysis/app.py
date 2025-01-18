import requests
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime
import asyncio
from filters.F1 import filter_1
from filters.F3 import filter_3
from filters.F3 import reformat_number
from DB import init_createDB, get_last_saved_date, update_data, fetch_issuers, extract_issuer_rows, retrieve_top_10, \
    DatabaseConnection, fetch_symbols
import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Initialize the database
init_createDB()

def rescrape_and_update_data():
    """Rescrape data and update the database."""
    print("Starting rescraping process...")
    issuers = filter_1()
    today_date = datetime.now().strftime('%m/%d/%Y')

    for issuer in issuers:
        last_saved_date = get_last_saved_date(issuer)
        if not last_saved_date or last_saved_date != today_date:
            print(f"Updating data for issuer: {issuer}")
            raw_data = asyncio.run(filter_3(issuer, last_saved_date or "11/10/2014"))

            # Reformat numeric fields in the fetched data
            formatted_data = []
            for row in raw_data:
                formatted_row = [
                    row[0],  # Date
                    reformat_number(row[1]),  # LastTradePrice
                    reformat_number(row[2]),  # Max
                    reformat_number(row[3]),  # Min
                    reformat_number(row[4]),  # AvgPrice
                    reformat_number(row[5]),  # PercentageChange
                    str(reformat_number(row[6])),  # Volume
                    str(reformat_number(row[7])),  # TurnoverInBEST
                    str(reformat_number(row[8]))  # TotalTurnover
                ]
                formatted_data.append(formatted_row)

            update_data(issuer, formatted_data, today_date)

    print("Rescraping process completed.")

# @app.teardown_appcontext
# def close_db_connection(exception=None):
#     """Close the database connection on application teardown."""
#     DatabaseConnection().close_connection()
#     print("Database connection closed.")

@app.route('/')
def index():
    """Home page displaying stock data with filtering options."""
    # Fetch query parameters for filters
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    issuer = request.args.get('issuer', 'ALL')
    # Rescrape and update the database
    rescrape_and_update_data()
    # Fetch issuers for the dropdown
    issuers = fetch_symbols()
    # Build query based on filters
    rows = extract_issuer_rows(from_date, issuer, to_date)
    # Render the template with fetched data
    return render_template(
        'index.html',
        rows=rows,
        issuers=issuers,
        from_date=from_date,
        to_date=to_date,
        issuer=issuer
    )

@app.route('/dashboard')
def dashboard():
    stocks = retrieve_top_10()
    print(stocks)  # Debugging output to verify fetched data
    return render_template('dashboard.html', stocks=stocks)


@app.route('/analytics/technical-analysis', methods=['GET'])
def technical_analysis():
    symbols = fetch_symbols()

    return render_template(
        'technical_analysis.html',
        issuers=symbols,
        candlestick_data=None,
        selected_symbol= None,
        chart_path=None,
        final_signals=None
    )

@app.route('/analytics/technical-analysis', methods=['POST'])
def technical_analysis_post():
    symbols = fetch_symbols()  # Retrieve available stock symbols for the dropdown
    selected_symbol = request.form.get('symbol')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # Handle case when no symbol is selected
    if not selected_symbol:
        return render_template(
            'technical_analysis.html',
            issuers=symbols,
            candlestick_data=None,
            selected_symbol=None,
            chart_path=None,
            final_signals=None,
            error="Please select a stock symbol."
        )

    # Prepare the payload for the API request
    payload = {
        "symbol": selected_symbol,  # Adjust key to match expected API payload
        "start_date": start_date,
        "end_date": end_date
    }

    try:
        # Call the technical analysis service
        response = requests.post('http://localhost:5001/api/technical_analysis',  json={"symbol": selected_symbol})

        if response.status_code == 200:
            # Parse the API response
            analysis_data = response.json()

            return render_template(
                'technical_analysis.html',
                issuers=symbols,
                candlestick_data=analysis_data.get('candlestick_data'),
                selected_symbol=selected_symbol,
                chart_path=analysis_data.get('chart_path'),
                final_signals=analysis_data.get('final_signals'),
                error=None
            )
        else:
            # Handle API error response
            return render_template(
                'technical_analysis.html',
                issuers=symbols,
                candlestick_data=None,
                selected_symbol=selected_symbol,
                chart_path=None,
                final_signals=None,
                error="Failed to fetch technical analysis data. Please try again later."
            )

    except requests.exceptions.RequestException as e:
        # Handle connection errors or other request exceptions
        return render_template(
            'technical_analysis.html',
            issuers=symbols,
            candlestick_data=None,
            selected_symbol=selected_symbol,
            chart_path=None,
            final_signals=None,
            error=f"An error occurred while contacting the analysis service: {str(e)}"
        )

@app.route('/analytics/fundamental-analysis', methods=['GET'])
def fundamental_analysis():
    issuers = fetch_issuers()
    return render_template('fundamental_analysis.html', issuers=issuers)

@app.route('/analytics/fundamental-analysis', methods=['POST'])
def get_fundamental_data():
    issuer_name = request.json.get('issuer')
    if issuer_name:
        # Call the fundamental analysis microservice
        try:
            response = requests.post(
                'http://localhost:5002/api/fundamental-analysis',
                json={"issuer": issuer_name}
            )
            logging.debug(f"Microservice response: {response.status_code}, {response.text}")
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({"error": "Failed to fetch data from the microservice"}), response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error contacting microservice: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/analytics/lstm', methods=['GET'])
def lstm():
    symbols = fetch_symbols()

    return render_template(
        'lstm.html',
        issuers=symbols,
        predicted_price=None,
        recommendation=None,
        graph_path=None,
        metrics=None,
        error_message=None,
        selected_symbol=None
    )


@app.route('/analytics/lstm', methods=['POST'])
def lstm_post():
    symbols = fetch_symbols()

    # Default values
    predicted_price = None
    last_prices = None
    graph_path = None
    recommendation = None
    error_message = None
    metrics = None

    selected_symbol = request.form.get('symbol')
    if not selected_symbol:
        return render_template(
            'lstm.html',
            issuers=symbols,
            predicted_price=predicted_price,
            recommendation=recommendation,
            graph_path=graph_path,
            metrics=metrics,
            error_message="Symbol not provided",
            selected_symbol=selected_symbol
        )
    try:
        # Call the LSTM microservice
        response = requests.post(
            'http://localhost:5004/api/lstm',
            json={"symbol": selected_symbol}
        )
        logging.debug(f"LSTM microservice response: {response.status_code}, {response.text}")

        if response.status_code == 200:
            data = response.json()
            # Parse the response data
            predicted_price = data.get('predicted_price')
            last_prices = data.get('last_prices')
            metrics = data.get('metrics')
            graph_path = data.get('graph_path')

            # To ensure that metrics are in proper format
            if not isinstance(metrics, list) or len(metrics) != 2:
                metrics = [None, None]

            if predicted_price is not None and last_prices:
                last_price = last_prices[-1]
                if predicted_price > last_price * 1.05:
                    recommendation = "Sell"
                elif predicted_price < last_price * 0.95:
                    recommendation = "Buy"
                else:
                    recommendation = "Hold"
            else:
                recommendation = "Hold"
                error_message = "Not enough data for prediction."

            return render_template(
                'lstm.html',
                issuers=symbols,
                predicted_price=predicted_price,
                recommendation=recommendation,
                graph_path=graph_path,
                metrics=metrics,
                error_message=error_message,
                selected_symbol=selected_symbol
            )
        else:
            logging.error(f"Failed to fetch data from the LSTM service: {response.status_code}")
            return render_template(
                'lstm.html',
                issuers=symbols,
                predicted_price=predicted_price,
                recommendation=recommendation,
                graph_path=graph_path,
                metrics=metrics,
                error_message="Failed to fetch data from the LSTM service ",
                selected_symbol=selected_symbol
            )
    except requests.exceptions.RequestException as e:
        logging.error(f"Error contacting LSTM service: {e}")
        return render_template(
            'lstm.html',
            issuers=symbols,
            predicted_price=predicted_price,
            recommendation=recommendation,
            graph_path=graph_path,
            metrics=metrics,
            error_message="Failed to establish a new connection",
            selected_symbol=selected_symbol
        )

if __name__ == '__main__':
    app.run(debug=True)
