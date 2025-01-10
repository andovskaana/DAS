from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

DATABASE = '../data/stock_data.db'


def test_database_connection():
    """Check if the database connection is successful at startup."""
    try:
        if not os.path.exists(DATABASE):
            raise FileNotFoundError(f"Database file not found at {DATABASE}")

        conn = sqlite3.connect(DATABASE)
        conn.execute("SELECT 1")  # Test a simple query
        conn.close()
        print("Database connection successful.")
    except Exception as e:
        print(f"Database connection error: {e}")
        raise


def get_recommendation_counts(issuer):
    """Fetch recommendation counts from the database."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 'buy' AS recommendation, COUNT(*) 
            FROM all_info 
            WHERE issuer = ? AND recommendation = 'buy'
            UNION
            SELECT 'sell' AS recommendation, COUNT(*) 
            FROM all_info 
            WHERE issuer = ? AND recommendation = 'sell'
            UNION
            SELECT 'hold' AS recommendation, COUNT(*) 
            FROM all_info 
            WHERE issuer = ? AND recommendation = 'hold'
        """, (issuer, issuer, issuer))
        results = cursor.fetchall()
        conn.close()
    except sqlite3.Error as db_error:
        raise Exception(f"Database query error: {db_error}")
    except Exception as e:
        raise Exception(f"Unexpected error: {e}")

    # Process the results into a dictionary
    counts = {"Buy": 0, "Sell": 0, "Hold": 0}
    for recommendation, count in results:
        recommendation = recommendation.capitalize()
        if recommendation in counts:
            counts[recommendation] = count

    if counts["Buy"] > counts["Sell"]:
        recommendation = "Buy"
    elif counts["Sell"] > counts["Buy"]:
        recommendation = "Sell"
    else:
        recommendation = "Hold"

    return {**counts, "Recommendation": recommendation}


@app.route('/api/fundamental-analysis', methods=['POST'])
def analyze_fundamentals():
    data = request.json
    issuer = data.get('issuer')

    if not issuer:
        return jsonify({"error": "Issuer not provided"}), 400

    try:
        recommendation_data = get_recommendation_counts(issuer)
        return jsonify(recommendation_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    try:
        test_database_connection()  # Test the connection at startup
        app.run(port=5002, debug=True)
    except Exception as e:
        print(f"Failed to start the application: {e}")
