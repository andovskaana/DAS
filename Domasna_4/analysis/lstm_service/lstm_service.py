from flask import Flask, jsonify, request
from lstm import train_and_predict

app = Flask(__name__)

@app.route('/api/lstm', methods=['POST'])
def predict():
    data = request.json
    symbol = data['symbol']
    if not symbol:
        return jsonify({"error": "Symbol not provided"}), 400
    try:
        predicted_price, last_prices, metrics, graph_path = train_and_predict(symbol)
        return jsonify({
            "predicted_price": predicted_price,
            "last_prices": last_prices,
            "metrics": metrics,
            "graph_path": graph_path
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5004)
