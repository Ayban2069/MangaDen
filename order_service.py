"""
Order Service — port 5000
Orchestrates: Inventory deduction → Payment → Confirmation
"""
from flask import Flask, request, Response
import xml.etree.ElementTree as ET
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

INVENTORY_DEDUCT = 'http://127.0.0.1:5001/deduct_stock'
PAYMENT_URL      = 'http://127.0.0.1:5002/process_payment'

def xresp(root, status=200):
    ET.indent(root, space='  ')
    return Response(ET.tostring(root, encoding='unicode'), mimetype='application/xml', status=status)

def fail(message, stage=''):
    r = ET.Element('OrderResponse')
    ET.SubElement(r, 'Status').text = 'Failed'
    if stage: ET.SubElement(r, 'Stage').text = stage
    ET.SubElement(r, 'Message').text = message
    return xresp(r)

@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        root = ET.fromstring(request.data)
    except ET.ParseError as e:
        return fail(f'Invalid XML: {e}')

    manga_id  = root.findtext('MangaID', '').strip()
    quantity  = root.findtext('Quantity', '1').strip()
    buyer     = root.findtext('Buyer', 'Guest').strip()

    if not manga_id:
        return fail('MangaID is required')

    # ── Step 1: Deduct inventory ──────────────────────────────────────────────
    inv_xml = ET.Element('StockRequest')
    ET.SubElement(inv_xml, 'MangaID').text  = manga_id
    ET.SubElement(inv_xml, 'Quantity').text = quantity

    try:
        inv_resp = requests.post(INVENTORY_DEDUCT,
                                 data=ET.tostring(inv_xml),
                                 headers={'Content-Type': 'application/xml'},
                                 timeout=5)
    except requests.ConnectionError:
        return fail('Inventory Service unreachable', 'Inventory')

    inv_root = ET.fromstring(inv_resp.content)
    if inv_root.findtext('Status') != 'Success':
        return fail(inv_root.findtext('Message', 'Inventory failed'), 'Inventory')

    total     = inv_root.findtext('TotalAmount')
    title     = inv_root.findtext('Title')
    remaining = inv_root.findtext('RemainingStock')

    # ── Step 2: Process payment ───────────────────────────────────────────────
    pay_xml = ET.Element('Payment')
    ET.SubElement(pay_xml, 'Amount').text = total
    ET.SubElement(pay_xml, 'Buyer').text  = buyer

    try:
        pay_resp = requests.post(PAYMENT_URL,
                                 data=ET.tostring(pay_xml),
                                 headers={'Content-Type': 'application/xml'},
                                 timeout=5)
    except requests.ConnectionError:
        return fail('Payment Service unreachable', 'Payment')

    pay_root = ET.fromstring(pay_resp.content)
    if pay_root.findtext('Status') != 'Success':
        return fail(pay_root.findtext('Message', 'Payment failed'), 'Payment')

    # ── Step 3: Confirm ───────────────────────────────────────────────────────
    r = ET.Element('OrderResponse')
    ET.SubElement(r, 'Status').text        = 'Success'
    ET.SubElement(r, 'Message').text       = 'Order placed successfully!'
    ET.SubElement(r, 'Title').text         = title
    ET.SubElement(r, 'MangaID').text       = manga_id
    ET.SubElement(r, 'Quantity').text      = quantity
    ET.SubElement(r, 'Buyer').text         = buyer
    ET.SubElement(r, 'TotalCharged').text  = f'PHP {float(total):.2f}'
    ET.SubElement(r, 'TransactionID').text = pay_root.findtext('TransactionID')
    ET.SubElement(r, 'RemainingStock').text= remaining
    return xresp(r)

if __name__ == '__main__':
    print("=== MangaDen Order Service — port 5000 ===")
    app.run(port=5000, debug=False)
