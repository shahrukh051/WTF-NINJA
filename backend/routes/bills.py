import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import Medicine, Inventory, Bill, BillItem, SalesLog

router = APIRouter(prefix="/bills", tags=["Billing"])

AI_SERVICE_URL = "http://localhost:8002"


# ── Schemas ───────────────────────────────────────────────────────────────────

class BillItemIn(BaseModel):
    medicine_id: int
    quantity:    int = Field(gt=0)

class CreateBillPayload(BaseModel):
    customer_name: Optional[str] = "Walk-in Customer"
    notes:         Optional[str] = ""
    items:         List[BillItemIn]

class PrescriptionMedicine(BaseModel):
    name:     str
    dosage:   Optional[str] = ""
    quantity: int = Field(default=1, gt=0)

class FromPrescriptionPayload(BaseModel):
    customer_name: Optional[str] = "Walk-in Customer"
    medicines:     List[PrescriptionMedicine]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _deduct_and_log(db: Session, medicine_id: int, quantity: int):
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
    inv = db.query(Inventory).filter(Inventory.medicine_id == medicine_id).first()
    if not inv:
        raise HTTPException(status_code=400, detail=f"No inventory for medicine id {medicine_id}")
    if inv.quantity < quantity:
        med = db.query(Medicine).filter(Medicine.id == medicine_id).first()
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for {med.name if med else medicine_id}. Available: {inv.quantity}"
        )
    inv.quantity -= quantity
    log = SalesLog(medicine_id=medicine_id, quantity_sold=quantity)
    db.add(log)


def _fuzzy_match_medicine(name: str, db: Session) -> Optional[Medicine]:
    """Match medicine name from AI output to DB — case-insensitive, partial match"""
    name_lower = name.lower().strip()
    all_medicines = db.query(Medicine).all()
    # Exact match first
    for m in all_medicines:
        if m.name.lower() == name_lower:
            return m
    # Partial match
    for m in all_medicines:
        if name_lower in m.name.lower() or m.name.lower() in name_lower:
            return m
    # Word-level match (e.g. "Paracetamol" matches "Paracetamol 500mg")
    words = name_lower.split()
    for m in all_medicines:
        for word in words:
            if len(word) > 4 and word in m.name.lower():
                return m
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
def list_bills(limit: int = 20, db: Session = Depends(get_db)):
    """List all bills, most recent first"""
    bills = db.query(Bill).order_by(Bill.created_at.desc()).limit(limit).all()
    result = []
    for b in bills:
        result.append({
            "id":            b.id,
            "customer_name": b.customer_name,
            "total_amount":  b.total_amount,
            "items_count":   len(b.items),
            "created_at":    b.created_at.isoformat()
        })
    return {"success": True, "count": len(result), "bills": result}


@router.get("/{bill_id}")
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    """Get full bill detail with all items"""
    b = db.query(Bill).filter(Bill.id == bill_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bill not found")

    items = []
    for item in b.items:
        med = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        items.append({
            "medicine_id":   item.medicine_id,
            "medicine_name": med.name if med else "Unknown",
            "quantity":      item.quantity,
            "unit_price":    item.unit_price,
            "subtotal":      round(item.quantity * item.unit_price, 2)
        })

    return {
        "id":            b.id,
        "customer_name": b.customer_name,
        "notes":         b.notes,
        "total_amount":  b.total_amount,
        "created_at":    b.created_at.isoformat(),
        "items":         items
    }


@router.post("/create")
def create_bill(payload: CreateBillPayload, db: Session = Depends(get_db)):
    """Create a bill manually with medicine IDs"""
    if not payload.items:
        raise HTTPException(status_code=400, detail="Bill must have at least one item")

    bill = Bill(customer_name=payload.customer_name, notes=payload.notes, total_amount=0.0)
    db.add(bill)
    db.flush()

    total = 0.0
    for item in payload.items:
        med = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        if not med:
            raise HTTPException(status_code=404, detail=f"Medicine id {item.medicine_id} not found")

        _deduct_and_log(db, item.medicine_id, item.quantity)

        bi = BillItem(
            bill_id=bill.id,
            medicine_id=item.medicine_id,
            quantity=item.quantity,
            unit_price=med.unit_price
        )
        db.add(bi)
        total += med.unit_price * item.quantity

    bill.total_amount = round(total, 2)
    db.commit()

    return {
        "success":      True,
        "bill_id":      bill.id,
        "customer":     bill.customer_name,
        "total_amount": bill.total_amount,
        "message":      "Bill created successfully"
    }


@router.post("/from-prescription")
def create_bill_from_prescription(
    payload: FromPrescriptionPayload,
    db: Session = Depends(get_db)
):
    """
    Takes AI-extracted medicine list (from Shahrukh's /scan-prescription)
    and creates a bill by matching names to our database.
    """
    if not payload.medicines:
        raise HTTPException(status_code=400, detail="No medicines provided")

    matched   = []
    unmatched = []

    for pm in payload.medicines:
        med = _fuzzy_match_medicine(pm.name, db)
        if med:
            matched.append({"medicine": med, "quantity": max(1, pm.quantity)})
        else:
            unmatched.append(pm.name)

    if not matched:
        return {
            "success":   False,
            "message":   "No medicines from prescription matched our inventory",
            "unmatched": unmatched
        }

    bill = Bill(
        customer_name=payload.customer_name,
        notes="Created from prescription scan",
        total_amount=0.0
    )
    db.add(bill)
    db.flush()

    total = 0.0
    bill_items_detail = []

    for entry in matched:
        med = entry["medicine"]
        qty = entry["quantity"]

        try:
            _deduct_and_log(db, med.id, qty)
        except HTTPException as e:
            # Stock issue — skip this item but continue
            unmatched.append(f"{med.name} (insufficient stock)")
            continue

        bi = BillItem(
            bill_id=bill.id,
            medicine_id=med.id,
            quantity=qty,
            unit_price=med.unit_price
        )
        db.add(bi)
        subtotal = med.unit_price * qty
        total += subtotal
        bill_items_detail.append({
            "medicine_name": med.name,
            "quantity":      qty,
            "unit_price":    med.unit_price,
            "subtotal":      round(subtotal, 2)
        })

    if not bill_items_detail:
        db.rollback()
        return {
            "success": False,
            "message": "No bill was created because all matched medicines were unavailable",
            "unmatched_medicines": unmatched
        }

    bill.total_amount = round(total, 2)
    db.commit()

    return {
        "success":      True,
        "bill_id":      bill.id,
        "customer":     bill.customer_name,
        "total_amount": bill.total_amount,
        "items":        bill_items_detail,
        "unmatched_medicines": unmatched,
        "message":      f"Bill created with {len(bill_items_detail)} medicines"
    }


@router.post("/scan-and-bill")
async def scan_and_bill(
    file: UploadFile = File(...),
    customer_name: str = "Walk-in Customer",
    db: Session = Depends(get_db)
):
    """
    One-shot endpoint:
    1. Sends image to Shahrukh's AI service
    2. Gets extracted medicines
    3. Creates bill automatically
    Frontend can call just this one endpoint.
    """
    image_bytes = await file.read()

    # Call AI service
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{AI_SERVICE_URL}/scan-prescription",
                files={"file": (file.filename, image_bytes, file.content_type)}
            )
            resp.raise_for_status()
            ai_result = resp.json()
        except httpx.ConnectError:
            # AI service down — return error
            raise HTTPException(
                status_code=503,
                detail="AI service is not running. Start Shahrukh's service on port 8002."
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    medicines_from_ai = ai_result.get("data", {}).get("medicines", [])
    if not medicines_from_ai:
        return {
            "success": False,
            "message": "AI could not extract medicines from the prescription image"
        }

    # Convert to our payload format
    prescription_medicines = [
        PrescriptionMedicine(name=m["name"], quantity=m.get("quantity", 1))
        for m in medicines_from_ai
    ]

    from_payload = FromPrescriptionPayload(
        customer_name=customer_name,
        medicines=prescription_medicines
    )
    return create_bill_from_prescription(from_payload, db)


@router.get("/today/summary")
def today_revenue(db: Session = Depends(get_db)):
    """Today's revenue — for dashboard"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    bills_today = db.query(Bill).filter(Bill.created_at >= today_start).all()
    revenue = sum(b.total_amount for b in bills_today)
    return {
        "today_bills":   len(bills_today),
        "today_revenue": round(revenue, 2)
    }
