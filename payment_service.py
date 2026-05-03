import os

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# PROCESS PAYMENT (JSON)
# ─────────────────────────────────────────────
@app.route('/process_payment', methods=['POST'])
def process_payment():
    data = request.json

    try:
        amount = float(data.get("amount", 0))
        buyer  = data.get("buyer", "Guest")

        if amount <= 0:
            return jsonify({
                "status": "failed",
                "message": "Invalid amount"
            }), 400

        # 🔹 Generate fake transaction ID
        txn_id = "MD-" + str(uuid.uuid4())[:8].upper()

        return jsonify({
            "status": "success",
            "message": "Payment processed successfully",
            "transaction_id": txn_id,
            "amount": amount,
            "buyer": buyer
        })

    except Exception as e:
        print("Payment Error:", e)
        return jsonify({
            "status": "failed",
            "message": "Payment error"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)