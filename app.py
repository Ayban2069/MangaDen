"""
MangaDen App — port 5003
Starts ALL services (inventory, order, payment) + frontend
"""
from flask import Flask, render_template
import threading
import subprocess
import sys

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# 🔥 Function to run a service
def run_service(script_name):
    subprocess.run([sys.executable, script_name])

if __name__ == '__main__':
    print("=== Starting MangaDen ALL Services ===")

    # Start backend services
    threading.Thread(target=run_service, args=("inventory_service.py",), daemon=True).start()
    threading.Thread(target=run_service, args=("order_service.py",), daemon=True).start()
    threading.Thread(target=run_service, args=("payment_service.py",), daemon=True).start()

    print("=== Frontend running at http://127.0.0.1:5003 ===")

    # Start frontend
    app.run(port=5003, debug=False)