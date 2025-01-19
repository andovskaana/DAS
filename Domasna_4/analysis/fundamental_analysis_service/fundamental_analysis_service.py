import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://localhost:5005/api/db/cursor")

def execute_query(query, params=None, fetchone=False):
    payload = {
        "query": query,
        "params": params or [],
        "fetchone": fetchone
    }
    try:
        response = requests.post(DB_SERVICE_URL, json=payload)
        response.raise_for_status()
        return response.json()  # Returns query results as raw tuples
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

def get_recommendation_counts(issuer):
    """Fetch recommendation counts from the database."""
    query ="""
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
        """
    params = [issuer, issuer, issuer]

    data = execute_query(query, params)
    results = [(item['recommendation'], item['COUNT(*)']) for item in data]

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
        app.run(port=5002, debug=True)
    except Exception as e:
        print(f"Failed to start the application: {e}")
