"""
Run this once to populate the database with sample data.
Usage: python seed_data.py
"""
from datetime import date, timedelta
from database import SessionLocal, init_db
from models import Medicine, Inventory, SalesLog, Bill, BillItem

today = date.today()

MEDICINES = [
    # (name, manufacturer, category, unit_price)
    ("Paracetamol 500mg",     "Cipla",          "Analgesic",       2.5),
    ("Azithromycin 250mg",    "Sun Pharma",     "Antibiotic",      45.0),
    ("Metformin 500mg",       "USV",            "Antidiabetic",    12.0),
    ("Cetirizine 10mg",       "Mankind",        "Antiallergic",    3.0),
    ("Omeprazole 20mg",       "Alkem",          "Antacid",         8.5),
    ("Amoxicillin 500mg",     "GlaxoSmithKline","Antibiotic",      35.0),
    ("Atorvastatin 10mg",     "Ranbaxy",        "Cholesterol",     22.0),
    ("Pantoprazole 40mg",     "Zydus",          "Antacid",         15.0),
    ("Dolo 650mg",            "Micro Labs",     "Analgesic",       4.0),
    ("Montelukast 10mg",      "Cipla",          "Antiallergic",    18.0),
    ("Vitamin D3 60000IU",    "Abbott",         "Supplement",      55.0),
    ("Cefixime 200mg",        "Lupin",          "Antibiotic",      38.0),
    ("Rabeprazole 20mg",      "Sun Pharma",     "Antacid",         14.0),
    ("Levocetirizine 5mg",    "Cipla",          "Antiallergic",    5.0),
    ("Ibuprofen 400mg",       "Mankind",        "Analgesic",       6.0),
    ("Metronidazole 400mg",   "Alkem",          "Antibiotic",      10.0),
    ("Ciprofloxacin 500mg",   "Cipla",          "Antibiotic",      28.0),
    ("Losartan 50mg",         "Lupin",          "Antihypertensive",20.0),
    ("Glimepiride 1mg",       "Sanofi",         "Antidiabetic",    16.0),
    ("Calcium + Vit D3",      "Pfizer",         "Supplement",      30.0),
]

INVENTORY = [
    # (medicine_index, quantity, days_until_expiry, batch)
    (0,  150, 300, "B001"),   # Paracetamol — healthy
    (1,    8,  25, "B002"),   # Azithromycin — LOW STOCK + EXPIRY
    (2,    5,  18, "B003"),   # Metformin — LOW STOCK + EXPIRY
    (3,  200, 400, "B004"),   # Cetirizine — healthy
    (4,   75, 240, "B005"),   # Omeprazole — healthy
    (5,    3,  10, "B006"),   # Amoxicillin — CRITICAL
    (6,   60, 500, "B007"),   # Atorvastatin — healthy
    (7,   90, 350, "B008"),   # Pantoprazole — healthy
    (8,    7,  28, "B009"),   # Dolo — LOW STOCK + EXPIRY
    (9,   12, 180, "B010"),   # Montelukast — healthy
    (10,  30, 600, "B011"),   # Vitamin D3 — healthy
    (11,   6,  22, "B012"),   # Cefixime — LOW STOCK + EXPIRY
    (12,  80, 310, "B013"),   # Rabeprazole — healthy
    (13, 110, 420, "B014"),   # Levocetirizine — healthy
    (14,   4,  15, "B015"),   # Ibuprofen — LOW STOCK + EXPIRY
    (15,  55, 270, "B016"),   # Metronidazole — healthy
    (16,   9,  19, "B017"),   # Ciprofloxacin — LOW STOCK + EXPIRY
    (17,  45, 380, "B018"),   # Losartan — healthy
    (18,  22, 290, "B019"),   # Glimepiride — healthy
    (19,  50, 450, "B020"),   # Calcium + Vit D3 — healthy
]

SALES = [
    # (medicine_index, quantity_sold)
    (0, 30), (1, 15), (3, 45), (0, 20), (4, 10),
    (8, 25), (11, 12), (14, 18), (2, 8),  (17, 14),
    (6, 20), (13, 35), (7, 22), (9, 11), (0, 15),
]


def seed():
    init_db()
    db = SessionLocal()

    try:
        # Skip if already seeded
        if db.query(Medicine).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # Insert medicines
        medicine_objs = []
        for name, manufacturer, category, price in MEDICINES:
            m = Medicine(
                name=name,
                manufacturer=manufacturer,
                category=category,
                unit_price=price
            )
            db.add(m)
            medicine_objs.append(m)
        db.flush()

        # Insert inventory
        for med_idx, qty, days, batch in INVENTORY:
            inv = Inventory(
                medicine_id=medicine_objs[med_idx].id,
                quantity=qty,
                expiry_date=(today + timedelta(days=days)).isoformat(),
                batch_number=batch,
                reorder_level=10
            )
            db.add(inv)

        # Insert sales log
        from datetime import datetime
        import random
        for med_idx, qty in SALES:
            sl = SalesLog(
                medicine_id=medicine_objs[med_idx].id,
                quantity_sold=qty,
                sold_at=datetime.utcnow()
            )
            db.add(sl)

        # Insert a sample bill for demo
        bill = Bill(customer_name="Ravi Sharma", total_amount=0.0, notes="Sample bill")
        db.add(bill)
        db.flush()

        total = 0.0
        for med_idx, qty in [(0, 2), (3, 1), (4, 1)]:
            m = medicine_objs[med_idx]
            bi = BillItem(
                bill_id=bill.id,
                medicine_id=m.id,
                quantity=qty,
                unit_price=m.unit_price
            )
            db.add(bi)
            total += m.unit_price * qty

        bill.total_amount = total
        db.commit()
        print("Seed data inserted — 20 medicines, inventory, sales, 1 sample bill")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
