import os

from flask import Flask, request, Response, jsonify
from flask import Flask, render_template
import xml.etree.ElementTree as ET
from flask_cors import CORS
import psycopg2

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# 🔑 Supabase connection
def get_conn():
    return psycopg2.connect(
        host="aws-1-ap-south-1.pooler.supabase.com",
        database="postgres",
        user="postgres.ttnaunhyqdtwrordkfft",
        password="rikajin1108",
        port=5432  
    )

# ── XML RESPONSE HELPER (used by other services) ─────────────
def xresp(root, status=200):
    ET.indent(root, space='  ')
    return Response(
        ET.tostring(root, encoding='unicode'),
        mimetype='application/xml',
        status=status
    )

# ── GET ALL MANGA (JSON for frontend) ───────────────────────
@app.route('/manga', methods=['GET'])
def list_manga():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM manga ORDER BY id")
    rows = cur.fetchall()

    manga_list = []
    for r in rows:
        manga_list.append({
            "id": r[0],
            "title": r[1],
            "author": r[2],
            "genre": r[3],
            "price": float(r[4]),
            "stock": r[5],
            "volume": r[6],
            "description": r[7],
            "cover_url": r[8]
        })

    conn.close()
    return jsonify({"manga": manga_list})

# ── ADD MANGA (XML) ─────────────────────────────────────────
@app.route('/manga', methods=['POST'])
def add_manga():
    data = request.json

    try:
        title = data.get('title')
        author = data.get('author')
        genre = data.get('genre')
        price = float(data.get('price', 0))
        stock = int(data.get('stock', 0))
        volume = int(data.get('volume', 1))
        description = data.get('description')
        cover = data.get('cover_url')

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO manga (title, author, genre, price, stock, volume, description, cover)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (title, author, genre, price, stock, volume, description, cover))

        new_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "id": new_id})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"status": "failed"}), 400

# ── UPDATE ─────────────────────────────────────────────────
@app.route('/manga/<manga_id>', methods=['PUT'])
def update_manga(manga_id):
    data = request.json

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE manga SET
        title=%s, author=%s, genre=%s, price=%s,
        stock=%s, volume=%s, description=%s, cover=%s
        WHERE id=%s
    """, (
        data.get('title'),
        data.get('author'),
        data.get('genre'),
        data.get('price'),
        data.get('stock'),
        data.get('volume'),
        data.get('description'),
        data.get('cover_url'),
        manga_id
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

# ── DELETE ─────────────────────────────────────────────────
@app.route('/manga/<manga_id>', methods=['DELETE'])
def delete_manga(manga_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM manga WHERE id=%s", (manga_id,))
    conn.commit()
    conn.close()

    r = ET.Element('DeleteResponse')
    ET.SubElement(r, 'Status').text = 'Success'
    return jsonify({"status": "success"})
    return xresp(r)

# ── DEDUCT STOCK (used by order service) ───────────────────
@app.route('/deduct_stock', methods=['POST'])
def deduct_stock():
    root = ET.fromstring(request.data)

    manga_id = root.findtext('MangaID')
    qty = int(root.findtext('Quantity'))

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT stock, price, title FROM manga WHERE id=%s", (manga_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return xresp(ET.Element('Error'), 404)

    stock, price, title = row

    if stock < qty:
        conn.close()
        r = ET.Element('InventoryResponse')
        ET.SubElement(r, 'Status').text = 'Failed'
        ET.SubElement(r, 'Message').text = 'Insufficient stock'
        return xresp(r)

    cur.execute(
        "UPDATE manga SET stock = stock - %s WHERE id=%s",
        (qty, manga_id)
    )
    conn.commit()
    conn.close()

    r = ET.Element('InventoryResponse')
    ET.SubElement(r, 'Status').text = 'Success'
    ET.SubElement(r, 'Title').text = title
    ET.SubElement(r, 'TotalAmount').text = str(price * qty)
    ET.SubElement(r, 'RemainingStock').text = str(stock - qty)
    return xresp(r)

@app.route('/manga/<int:manga_id>/stock', methods=['PUT'])
def update_stock(manga_id):
    data = request.json
    new_stock = int(data.get("stock", 0))

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "UPDATE manga SET stock=%s WHERE id=%s",
        (new_stock, manga_id)
    )

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)