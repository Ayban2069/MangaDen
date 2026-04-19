"""
Payment Service — port 5002
Processes payments for manga orders.
"""
from flask import Flask, request, Response
import xml.etree.ElementTree as ET
from flask_cors import CORS
import random, string

app = Flask(__name__)
CORS(app)


def xresp(root):
    ET.indent(root, space='  ')
    return Response(ET.tostring(root, encoding='unicode'), mimetype='application/xml')

def gen_txn():
    return 'MD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        root = ET.fromstring(request.data)
    except ET.ParseError as e:
        r = ET.Element('Error'); r.text = str(e); return xresp(r), 400

    amount_text = root.findtext('Amount', '').strip()
    buyer       = root.findtext('Buyer', 'Guest').strip()

    try:
        amount = float(amount_text)
    except ValueError:
        r = ET.Element('PaymentResponse')
        ET.SubElement(r, 'Status').text = 'Failed'
        ET.SubElement(r, 'Message').text = 'Invalid amount'
        return xresp(r), 400

    if amount <= 0:
        r = ET.Element('PaymentResponse')
        ET.SubElement(r, 'Status').text = 'Failed'
        ET.SubElement(r, 'Message').text = 'Amount must be greater than zero'
        return xresp(r)

    r = ET.Element('PaymentResponse')
    ET.SubElement(r, 'Status').text = 'Success'
    ET.SubElement(r, 'TransactionID').text = gen_txn()
    ET.SubElement(r, 'Buyer').text = buyer
    ET.SubElement(r, 'AmountCharged').text = f'{amount:.2f}'
    ET.SubElement(r, 'Message').text = 'Payment processed successfully'
    return xresp(r)

if __name__ == '__main__':
    print("=== MangaDen Payment Service — port 5002 ===")
    app.run(port=5002, debug=False)
