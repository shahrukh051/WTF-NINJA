from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from database import get_db
from models import Medicine, Inventory, Bill, BillItem, SalesLog

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/top-medicines")
def top_medicines(limit: int = 10, db: Session = Depends(get_db)):
    """Top N selling medicines by units sold"""
    results = (
        db.query(Medicine.name, func.sum(SalesLog.quantity_sold).label("total_sold"))
        .join(SalesLog, Medicine.id == SalesLog.medicine_id)
        .group_by(Medicine.id)
        .order_by(func.sum(SalesLog.quantity_sold).desc())
        .limit(limit)
        .all()
    )

    return {
        "success": True,
        "top_medicines": [
            {"medicine_name": r[0], "total_sold": int(r[1])}
            for r in results
        ]
    }


@router.get("/revenue")
def revenue(period: str = "weekly", db: Session = Depends(get_db)):
    """
    Revenue summary.
    period: 'daily' | 'weekly' | 'monthly'
    Returns day-by-day breakdown for charts.
    """
    now = datetime.utcnow()

    if period == "daily":
        days = 1
    elif period == "weekly":
        days = 7
    else:
        days = 30

    start_date = now - timedelta(days=days)

    bills = db.query(Bill).filter(Bill.created_at >= start_date).all()

    # Build day-by-day revenue dict
    revenue_by_day = {}
    for i in range(days):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        revenue_by_day[day] = 0.0

    for b in bills:
        day = b.created_at.strftime("%Y-%m-%d")
        if day in revenue_by_day:
            revenue_by_day[day] += b.total_amount

    daily_breakdown = [
        {"date": d, "revenue": round(v, 2)}
        for d, v in sorted(revenue_by_day.items())
    ]

    return {
        "success":         True,
        "period":          period,
        "total_revenue":   round(sum(b.total_amount for b in bills), 2),
        "total_bills":     len(bills),
        "daily_breakdown": daily_breakdown
    }


@router.get("/expiry-risk")
def expiry_risk(db: Session = Depends(get_db)):
    """Total stock value at risk from expiring medicines"""
    threshold = (date.today() + timedelta(days=30)).isoformat()

    items = (
        db.query(Inventory, Medicine)
        .join(Medicine, Inventory.medicine_id == Medicine.id)
        .filter(Inventory.expiry_date <= threshold)
        .all()
    )

    total_risk_value = 0.0
    medicines_at_risk = []

    for inv, med in items:
        value = round(inv.quantity * med.unit_price, 2)
        total_risk_value += value
        medicines_at_risk.append({
            "medicine_name": med.name,
            "quantity":      inv.quantity,
            "unit_price":    med.unit_price,
            "expiry_date":   inv.expiry_date,
            "value_at_risk": value
        })

    medicines_at_risk.sort(key=lambda x: x["value_at_risk"], reverse=True)

    return {
        "success":           True,
        "total_risk_value":  round(total_risk_value, 2),
        "medicines_count":   len(medicines_at_risk),
        "medicines_at_risk": medicines_at_risk
    }


@router.get("/dashboard")
def dashboard_summary(db: Session = Depends(get_db)):
    """Single endpoint for all dashboard cards — Saumya calls this once"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    threshold_30 = (date.today() + timedelta(days=30)).isoformat()

    total_medicines    = db.query(Medicine).count()
    low_stock_count    = db.query(Inventory).filter(Inventory.quantity < 10).count()
    expiry_alert_count = db.query(Inventory).filter(Inventory.expiry_date <= threshold_30).count()

    bills_today = db.query(Bill).filter(Bill.created_at >= today_start).all()
    today_revenue = sum(b.total_amount for b in bills_today)

    recent_bills = db.query(Bill).order_by(Bill.created_at.desc()).limit(5).all()

    # 7-day revenue trend
    revenue_trend = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day.replace(hour=23, minute=59, second=59)
        day_bills = db.query(Bill).filter(
            Bill.created_at >= day_start,
            Bill.created_at <= day_end
        ).all()
        revenue_trend.append({
            "date":    day_str,
            "revenue": round(sum(b.total_amount for b in day_bills), 2)
        })

    return {
        "summary": {
            "total_medicines":    total_medicines,
            "low_stock_count":    low_stock_count,
            "expiry_alert_count": expiry_alert_count,
            "today_revenue":      round(today_revenue, 2),
            "today_bills":        len(bills_today)
        },
        "recent_bills": [
            {
                "id":            b.id,
                "customer_name": b.customer_name,
                "total_amount":  b.total_amount,
                "created_at":    b.created_at.isoformat()
            }
            for b in recent_bills
        ],
        "revenue_trend": revenue_trend
    }
