from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date
from database import get_db
from models import Medicine, Inventory, BillItem, SalesLog

router = APIRouter(prefix="/medicines", tags=["Medicines"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MedicineCreate(BaseModel):
    name:         str
    manufacturer: Optional[str] = ""
    category:     Optional[str] = "General"
    unit_price:   float = Field(ge=0)
    # Inventory fields
    quantity:     int = Field(default=0, ge=0)
    expiry_date:  str = ""
    batch_number: Optional[str] = ""
    reorder_level: Optional[int] = Field(default=10, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name is required")
        return value

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, value: str) -> str:
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("expiry_date must be YYYY-MM-DD") from exc
        return value


class MedicineUpdate(BaseModel):
    manufacturer: Optional[str] = None
    category:     Optional[str] = None
    unit_price:   Optional[float] = Field(default=None, ge=0)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
def list_medicines(db: Session = Depends(get_db)):
    """List all medicines with current stock"""
    medicines = db.query(Medicine).all()
    result = []
    for m in medicines:
        inv = db.query(Inventory).filter(Inventory.medicine_id == m.id).first()
        result.append({
            "id":           m.id,
            "name":         m.name,
            "manufacturer": m.manufacturer,
            "category":     m.category,
            "unit_price":   m.unit_price,
            "quantity":     inv.quantity if inv else 0,
            "expiry_date":  inv.expiry_date if inv else None,
            "batch_number": inv.batch_number if inv else None,
            "reorder_level":inv.reorder_level if inv else 10,
            "stock_status": _stock_status(inv)
        })
    return {"success": True, "count": len(result), "medicines": result}


@router.get("/{medicine_id}")
def get_medicine(medicine_id: int, db: Session = Depends(get_db)):
    m = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medicine not found")
    inv = db.query(Inventory).filter(Inventory.medicine_id == m.id).first()
    return {
        "id": m.id, "name": m.name, "manufacturer": m.manufacturer,
        "category": m.category, "unit_price": m.unit_price,
        "quantity": inv.quantity if inv else 0,
        "expiry_date": inv.expiry_date if inv else None,
        "batch_number": inv.batch_number if inv else None,
    }


@router.post("/")
def add_medicine(payload: MedicineCreate, db: Session = Depends(get_db)):
    """Add a new medicine and its initial inventory"""
    existing = db.query(Medicine).filter(Medicine.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Medicine with this name already exists")

    medicine = Medicine(
        name=payload.name,
        manufacturer=payload.manufacturer,
        category=payload.category,
        unit_price=payload.unit_price
    )
    db.add(medicine)
    db.flush()

    inventory = Inventory(
        medicine_id=medicine.id,
        quantity=payload.quantity,
        expiry_date=payload.expiry_date,
        batch_number=payload.batch_number,
        reorder_level=payload.reorder_level
    )
    db.add(inventory)
    db.commit()

    return {"success": True, "message": f"Medicine '{payload.name}' added", "id": medicine.id}


@router.put("/{medicine_id}")
def update_medicine(medicine_id: int, payload: MedicineUpdate, db: Session = Depends(get_db)):
    m = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medicine not found")
    if payload.manufacturer is not None: m.manufacturer = payload.manufacturer
    if payload.category     is not None: m.category     = payload.category
    if payload.unit_price   is not None: m.unit_price   = payload.unit_price
    db.commit()
    return {"success": True, "message": "Medicine updated"}


@router.delete("/{medicine_id}")
def delete_medicine(medicine_id: int, db: Session = Depends(get_db)):
    m = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Medicine not found")
    has_bill_items = db.query(BillItem).filter(BillItem.medicine_id == medicine_id).first()
    has_sales = db.query(SalesLog).filter(SalesLog.medicine_id == medicine_id).first()
    if has_bill_items or has_sales:
        raise HTTPException(
            status_code=409,
            detail="Medicine has billing or sales history and cannot be deleted"
        )
    db.delete(m)
    db.commit()
    return {"success": True, "message": "Medicine deleted"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stock_status(inv: Inventory) -> str:
    if not inv:
        return "no_inventory"
    from datetime import date, timedelta
    today = date.today()
    try:
        expiry = date.fromisoformat(inv.expiry_date) if inv.expiry_date else None
    except ValueError:
        return "invalid_expiry_date"
    if expiry and expiry <= today + timedelta(days=30):
        return "expiry_alert"
    if inv.quantity < inv.reorder_level:
        return "low_stock"
    return "healthy"
