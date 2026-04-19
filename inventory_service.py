
from flask import Flask, request, Response
import xml.etree.ElementTree as ET
from flask_cors import CORS
import psycopg2

app = Flask(__name__)
CORS(app)

# 🔑 Replace with YOUR Supabase credentials
def get_conn():
    return psycopg2.connect(
        host="aws-1-ap-south-1.pooler.supabase.com",
        database="postgres",
        user="postgres.ttnaunhyqdtwrordkfft",
        password="rikajin1108",
        port=5432
    )

def xresp(root, status=200):
    ET.indent(root, space='  ')
    return Response(ET.tostring(root, encoding='unicode'),
                    mimetype='application/xml',
                    status=status)

# ── GET ALL MANGA ─────────────────────────────────────────────
@app.route('/manga', methods=['GET'])
def list_manga():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM manga ORDER BY id")
    rows = cur.fetchall()

    root = ET.Element('MangaCollection')

    for r in rows:
        m = ET.SubElement(root, 'Manga', id=str(r[0]))
        ET.SubElement(m, 'Title').text = r[1]
        ET.SubElement(m, 'Author').text = r[2]
        ET.SubElement(m, 'Genre').text = r[3]
        ET.SubElement(m, 'Price').text = str(r[4])
        ET.SubElement(m, 'Stock').text = str(r[5])
        ET.SubElement(m, 'Volume').text = str(r[6])
        ET.SubElement(m, 'Description').text = r[7]
        ET.SubElement(m, 'Cover').text = r[8]

    conn.close()
    return xresp(root)

# ── GET SINGLE ───────────────────────────────────────────────
@app.route('/manga/<manga_id>', methods=['GET'])
def get_manga(manga_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM manga WHERE id=%s", (manga_id,))
    r = cur.fetchone()

    if not r:
        conn.close()
        err = ET.Element('Error')
        err.text = "Not found"
        return xresp(err, 404)

    m = ET.Element('Manga', id=str(r[0]))
    ET.SubElement(m, 'Title').text = r[1]
    ET.SubElement(m, 'Author').text = r[2]
    ET.SubElement(m, 'Genre').text = r[3]
    ET.SubElement(m, 'Price').text = str(r[4])
    ET.SubElement(m, 'Stock').text = str(r[5])
    ET.SubElement(m, 'Volume').text = str(r[6])
    ET.SubElement(m, 'Description').text = r[7]
    ET.SubElement(m, 'Cover').text = r[8]

    conn.close()
    return xresp(m)

# ── ADD MANGA ────────────────────────────────────────────────
@app.route('/manga', methods=['POST'])
def add_manga():
    try:
        root = ET.fromstring(request.data)
    except Exception as e:
        print("XML Error:", e)
        return xresp(ET.Element('Error'), 400)

    # Extract safely
    title = root.findtext('Title', '').strip()
    author = root.findtext('Author', '').strip()
    genre = root.findtext('Genre', '').strip()
    price = root.findtext('Price', '0').strip()
    stock = root.findtext('Stock', '0').strip()
    volume = root.findtext('Volume', '1').strip()
    description = root.findtext('Description', '').strip()
    cover = root.findtext('Cover', '').strip()

    try:
        price = float(price)
        stock = int(stock)
        volume = int(volume)
    except ValueError:
        return xresp(ET.Element('Error'), 400)

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

    r = ET.Element('AddResponse')
    ET.SubElement(r, 'Status').text = 'Success'
    ET.SubElement(r, 'AssignedID').text = str(new_id)

    return xresp(r, 201)

# ── UPDATE ───────────────────────────────────────────────────
@app.route('/manga/<manga_id>', methods=['PUT'])
def update_manga(manga_id):
    root = ET.fromstring(request.data)

    conn = get_conn()
    cur = conn.cursor()

    for child in root:
        cur.execute(f"""
            UPDATE manga SET {child.tag.lower()} = %s
            WHERE id = %s
        """, (child.text, manga_id))

    conn.commit()
    conn.close()

    r = ET.Element('UpdateResponse')
    ET.SubElement(r, 'Status').text = 'Success'
    return xresp(r)

# ── DELETE ───────────────────────────────────────────────────
@app.route('/manga/<manga_id>', methods=['DELETE'])
def delete_manga(manga_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM manga WHERE id=%s", (manga_id,))
    conn.commit()
    conn.close()

    r = ET.Element('DeleteResponse')
    ET.SubElement(r, 'Status').text = 'Success'
    return xresp(r)

# ── DEDUCT STOCK (used by order service) ─────────────────────
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

if __name__ == '__main__':
    print("=== MangaDen Inventory Service (Supabase) — port 5001 ===")
    app.run(port=5001, debug=False)