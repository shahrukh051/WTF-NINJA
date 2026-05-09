import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent / "pharmacy.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT NOT NULL,
            batch_number TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL,
            expiry_date TEXT NOT NULL,
            reorder_level INTEGER DEFAULT 10,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT NOT NULL,
            quantity_sold INTEGER NOT NULL,
            sold_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sample inventory data — realistic Indian pharmacy stock
    today = date.today()
    sample_medicines = [
        ("Paracetamol 500mg",     "B001", 150, 2.5,  (today + timedelta(days=300)).isoformat(), 20),
        ("Azithromycin 250mg",    "B002",   8, 45.0, (today + timedelta(days=25)).isoformat(),  10),
        ("Metformin 500mg",       "B003",   5, 12.0, (today + timedelta(days=18)).isoformat(),  15),
        ("Cetirizine 10mg",       "B004", 200,  3.0, (today + timedelta(days=400)).isoformat(), 20),
        ("Omeprazole 20mg",       "B005",  75,  8.5, (today + timedelta(days=240)).isoformat(), 10),
        ("Amoxicillin 500mg",     "B006",   3, 35.0, (today + timedelta(days=10)).isoformat(),  10),
        ("Atorvastatin 10mg",     "B007",  60, 22.0, (today + timedelta(days=500)).isoformat(), 10),
        ("Pantoprazole 40mg",     "B008",  90, 15.0, (today + timedelta(days=350)).isoformat(), 10),
        ("Dolo 650mg",            "B009",   7,  4.0, (today + timedelta(days=28)).isoformat(),  20),
        ("Montelukast 10mg",      "B010",  12, 18.0, (today + timedelta(days=180)).isoformat(), 10),
        ("Vitamin D3 60000IU",    "B011",  30, 55.0, (today + timedelta(days=600)).isoformat(), 10),
        ("Cefixime 200mg",        "B012",   6, 38.0, (today + timedelta(days=22)).isoformat(),  10),
        ("Rabeprazole 20mg",      "B013",  80, 14.0, (today + timedelta(days=310)).isoformat(), 10),
        ("Levocetirizine 5mg",    "B014", 110,  5.0, (today + timedelta(days=420)).isoformat(), 20),
        ("Ibuprofen 400mg",       "B015",   4,  6.0, (today + timedelta(days=15)).isoformat(),  15),
        ("Metronidazole 400mg",   "B016",  55, 10.0, (today + timedelta(days=270)).isoformat(), 10),
        ("Ciprofloxacin 500mg",   "B017",   9, 28.0, (today + timedelta(days=19)).isoformat(),  10),
        ("Losartan 50mg",         "B018",  45, 20.0, (today + timedelta(days=380)).isoformat(), 10),
        ("Glimepiride 1mg",       "B019",  22, 16.0, (today + timedelta(days=290)).isoformat(), 10),
        ("Calcium + Vit D3",      "B020",  50, 30.0, (today + timedelta(days=450)).isoformat(), 10),
    ]

    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO inventory
            (medicine_name, batch_number, quantity, unit_price, expiry_date, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_medicines)

    sample_sales = [
        ("Paracetamol 500mg",   30),
        ("Azithromycin 250mg",  15),
        ("Cetirizine 10mg",     45),
        ("Paracetamol 500mg",   20),
        ("Omeprazole 20mg",     10),
        ("Dolo 650mg",          25),
        ("Cefixime 200mg",      12),
        ("Ibuprofen 400mg",     18),
        ("Metformin 500mg",      8),
        ("Losartan 50mg",       14),
    ]
    cursor.execute("SELECT COUNT(*) FROM sales_log")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO sales_log (medicine_name, quantity_sold)
            VALUES (?, ?)
        """, sample_sales)

    conn.commit()
    conn.close()
    print("Database initialized with sample data")


def get_all_inventory():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory ORDER BY medicine_name")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_sales_summary():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT medicine_name, SUM(quantity_sold) as total_sold
        FROM sales_log
        GROUP BY medicine_name
        ORDER BY total_sold DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_expiring_medicines(days: int = 30):
    threshold = (date.today() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT medicine_name, quantity, expiry_date, batch_number
        FROM inventory
        WHERE date(expiry_date) <= date(?)
        ORDER BY expiry_date ASC
    """, (threshold,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_low_stock_medicines(threshold: int = 10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT medicine_name, quantity, reorder_level
        FROM inventory
        WHERE quantity < ?
        ORDER BY quantity ASC
    """, (threshold,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
