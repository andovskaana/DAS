from flask import Flask, request, jsonify
import sqlite3
import pandas as pd

app = Flask(__name__)

# Singleton connection for the database
def get_db_connection():
    conn = sqlite3.connect('stock_data.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/db/query', methods=['POST'])
def query_db():
    """
    Endpoint to query the database.
    Expects JSON input with:
    - `query`: SQL query string
    """
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        conn = get_db_connection()
        result = pd.read_sql_query(query, conn)
        return jsonify(result.to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/db/cursor', methods=['POST'])
def cursor_db():
    """
    Endpoint to execute raw SQL queries.
    Expects JSON input with:
    - `query`: The raw SQL query string.
    - `params`: Optional parameters for the query (list or tuple).
    """
    data = request.json
    query = data.get('query')
    params = data.get('params', [])
    fetchone = data.get('fetchone', False)  # Default to False (fetch all rows)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print(f"Query: {query}, params {params}")
        cursor.execute(query, params)

        if query.strip().lower().startswith("select"):
            # Fetch results based on the `fetchone` flag
            if fetchone:
                row = cursor.fetchone()
                if row is not None:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                else:
                    result = None  # No rows found
            else:
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]

            return jsonify(result)
        else:
            # For non-SELECT queries, commit the transaction
            conn.commit()
            return jsonify({"message": "Query executed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(port=5005)
