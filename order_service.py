import os

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import psycopg2

app = Flask(__name__)
CORS(app)

# 🔗 Services
INVENTORY_URL = "http://127.0.0.1:5001"
PAYMENT_URL   = "http://127.0.0.1:5002"

# 🔑 DB connection
def get_conn():
    return psycopg2.connect(
        host="aws-1-ap-south-1.pooler.supabase.com",
        database="postgres",
        user="postgres.ttnaunhyqdtwrordkfft",
        password="rikajin1108",
        port=6543
    )

# ─────────────────────────────────────────────
# PLACE ORDER (JSON)
# ─────────────────────────────────────────────
@app.route('/order', methods=['POST'])
def place_order():
    data = request.json
    print("ORDER RECEIVED:", data)

    manga_id = data.get("manga_id")
    quantity = int(data.get("quantity", 1))
    buyer    = data.get("buyer", "Guest")

    if not manga_id:
        return jsonify({"status": "failed", "message": "Missing manga_id"}), 400

    # 🔹 Get manga list
    try:
        inv_res = requests.get(f"{INVENTORY_URL}/manga")
        manga_list = inv_res.json().get("manga", [])
    except Exception as e:
        print("Inventory Error:", e)
        return jsonify({"status": "failed", "message": "Inventory unreachable"}), 500

    manga = next((m for m in manga_list if m["id"] == manga_id), None)

    if not manga:
        return jsonify({"status": "failed", "message": "Manga not found"}), 404

    if manga["stock"] < quantity:
        return jsonify({"status": "failed", "message": "Not enough stock"}), 400

    total = manga["price"] * quantity

    # 🔹 Update stock
    try:
        stock_res = requests.put(
            f"{INVENTORY_URL}/manga/{manga_id}/stock",
            json={"stock": manga["stock"] - quantity}
        )
        if not stock_res.ok:
            return jsonify({"status": "failed", "message": "Stock update failed"}), 500
    except Exception as e:
        print("Stock Update Error:", e)
        return jsonify({"status": "failed", "message": "Inventory error"}), 500

    # 🔹 Process payment
    try:
        pay_res = requests.post(f"{PAYMENT_URL}/process_payment", json={
            "amount": total,
            "buyer": buyer
        })
        pay_data = pay_res.json()
    except Exception as e:
        print("Payment Error:", e)
        return jsonify({"status": "failed", "message": "Payment unreachable"}), 500

    if pay_data.get("status") != "success":
        return jsonify({"status": "failed", "message": "Payment failed"}), 400

    txn_id = pay_data.get("transaction_id")

    # 🔹 SAVE TO DATABASE
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO orders (manga_id, title, buyer, quantity, total, transaction_id)
            VALUES (%s,%s,%s,%s,%s,%s)
            """, (
            manga_id,
            manga["title"],
            buyer,
            quantity,
            total,
            txn_id
        ))

        conn.commit()

    except Exception as e:
        print("DB ERROR:", e)
        return jsonify({"status": "failed", "message": "Database error"}), 500

    finally:
        if conn:
            conn.close()

    return jsonify({
        "status": "success",
        "title": manga["title"],
        "quantity": quantity,
        "total": total,
        "transaction_id": txn_id
    })


# ─────────────────────────────────────────────
# GET ORDERS
# ─────────────────────────────────────────────
@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
        rows = cur.fetchall()

        orders = []
        for r in rows:
            orders.append({
                "id": r[0],
                "manga_id": r[1],
                "title": r[2],
                "buyer": r[3],
                "quantity": r[4],
                "total": float(r[5]),
                "transaction_id": r[6],
                "created_at": str(r[7])
            })

        return jsonify({"orders": orders})

    except Exception as e:
        print("FETCH ORDERS ERROR:", e)
        return jsonify({"orders": []}), 500

    finally:
        if conn:
            conn.close()

@app.route('/analytics', methods=['GET'])
def get_analytics():
    conn = get_conn()
    cur = conn.cursor()

    # total revenue
    cur.execute("SELECT COALESCE(SUM(total),0) FROM orders")
    revenue = float(cur.fetchone()[0])

    # total units sold
    cur.execute("SELECT COALESCE(SUM(quantity),0) FROM orders")
    units = int(cur.fetchone()[0])

    # average order value
    cur.execute("SELECT COALESCE(AVG(total),0) FROM orders")
    avg = float(cur.fetchone()[0])

    conn.close()

    return jsonify({
        "revenue": revenue,
        "units_sold": units,
        "avg_order": avg
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)