from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, timedelta
from database import get_db
from models import Medicine, Inventory

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RestockPayload(BaseModel):
    medicine_id:  int
    quantity:     int = Field(gt=0)
    expiry_date:  Optional[str] = None
    batch_number: Optional[str] = None

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, value: Optional[str]) -> Optional[str]:
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("expiry_date must be YYYY-MM-DD") from exc
        return value


# ── Routes ────────────────────────────────────────────────────────────────────

@router.put("/restock")
def restock_medicine(payload: RestockPayload, db: Session = Depends(get_db)):
    """Add stock to an existing medicine"""
    inv = db.query(Inventory).filter(Inventory.medicine_id == payload.medicine_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found for this medicine")

    inv.quantity += payload.quantity
    if payload.expiry_date:
        inv.expiry_date = payload.expiry_date
    if payload.batch_number:
        inv.batch_number = payload.batch_number

    db.commit()

    med = db.query(Medicine).filter(Medicine.id == payload.medicine_id).first()
    return {
        "success": True,
        "message": f"Restocked {payload.quantity} units of {med.name if med else 'medicine'}",
        "new_quantity": inv.quantity
    }


@router.get("/expiry-alerts")
def expiry_alerts(days: int = 30, db: Session = Depends(get_db)):
    """Medicines expiring within N days"""
    threshold = (date.today() + timedelta(days=days)).isoformat()
    items = (
        db.query(Inventory, Medicine)
        .join(Medicine, Inventory.medicine_id == Medicine.id)
        .filter(Inventory.expiry_date <= threshold)
        .order_by(Inventory.expiry_date.asc())
        .all()
    )

    result = []
    for inv, med in items:
        expiry = date.fromisoformat(inv.expiry_date)
        days_left = (expiry - date.today()).days
        result.append({
            "medicine_id":   med.id,
            "medicine_name": med.name,
            "quantity":      inv.quantity,
            "expiry_date":   inv.expiry_date,
            "days_left":     days_left,
            "batch_number":  inv.batch_number,
            "urgency":       "critical" if days_left <= 7 else "warning" if days_left <= 30 else "ok"
        })

    return {
        "success": True,
        "days_threshold": days,
        "count": len(result),
        "medicines": result
    }


@router.get("/low-stock")
def low_stock(threshold: int = 10, db: Session = Depends(get_db)):
    """Medicines with quantity below threshold"""
    items = (
        db.query(Inventory, Medicine)
        .join(Medicine, Inventory.medicine_id == Medicine.id)
        .filter(Inventory.quantity < threshold)
        .order_by(Inventory.quantity.asc())
        .all()
    )

    result = []
    for inv, med in items:
        result.append({
            "medicine_id":   med.id,
            "medicine_name": med.name,
            "quantity":      inv.quantity,
            "reorder_level": inv.reorder_level,
            "unit_price":    med.unit_price,
            "urgency":       "critical" if inv.quantity <= 3 else "low"
        })

    return {
        "success": True,
        "threshold": threshold,
        "count": len(result),
        "medicines": result
    }


@router.get("/summary")
def inventory_summary(db: Session = Depends(get_db)):
    """Quick summary counts for dashboard cards"""
    from sqlalchemy import func
    today_str = date.today().isoformat()
    threshold_30 = (date.today() + timedelta(days=30)).isoformat()

    total_medicines   = db.query(Medicine).count()
    low_stock_count   = db.query(Inventory).filter(Inventory.quantity < 10).count()
    expiry_alert_count = db.query(Inventory).filter(Inventory.expiry_date <= threshold_30).count()
    total_stock_value = db.query(func.sum(Inventory.quantity * Medicine.unit_price))\
        .join(Medicine, Inventory.medicine_id == Medicine.id).scalar() or 0.0

    return {
        "total_medicines":    total_medicines,
        "low_stock_count":    low_stock_count,
        "expiry_alert_count": expiry_alert_count,
        "total_stock_value":  round(total_stock_value, 2)
    }
