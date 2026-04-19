# MangaDen — XML-Powered Manga Store (Mini SOA)

## Setup

```bash
pip install flask requests
```

## How to Run

Open **4 separate terminal windows**:

```bash
# Terminal 1 — Inventory Service (data + CRUD) — port 5001
python inventory_service.py

# Terminal 2 — Payment Service — port 5002
python payment_service.py

# Terminal 3 — Order Service (orchestrator) — port 5000
python order_service.py

# Terminal 4 — Frontend Web App — port 5003
python app.py
```

Then open your browser at: **http://127.0.0.1:5003**

## Architecture

```
Browser (port 5003)
    │
    ├── GET/POST/PUT/DELETE /manga        → Inventory Service (port 5001)
    │                                        reads/writes data/manga.xml
    │
    └── POST /place_order                 → Order Service (port 5000)
                │
                ├──► POST /deduct_stock   → Inventory Service (port 5001)
                └──► POST /process_payment→ Payment Service  (port 5002)
```

## Features

- 🛒 Browse manga store with cover images, genre badges, stock indicators
- 🔍 Search by title or author
- 🏷️ Filter by genre
- 💳 Buy manga — triggers full SOA flow (Inventory → Payment → Confirmation)
- ⚙️ Admin panel — Add, Edit, Delete manga
- 💾 All data stored in **data/manga.xml** (persists across restarts)
- 🔔 Toast notifications for all actions
