import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().with_name(".env"))
except ImportError:
    pass

from database import init_db, get_all_inventory, get_expiring_medicines, get_low_stock_medicines
from vision_pipeline import scan_prescription, scan_prescription_mock
from inventory_agent import generate_daily_report, generate_report_mock

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Aushadhi Vault AI Service starting...")
    init_db()
    mode = "MOCK MODE" if USE_MOCK else "LIVE MODE (vLLM)"
    print(f"Running in {mode}")
    print("Endpoints ready: /scan-prescription | /inventory-report")
    yield
    print("Shutting down AI service")


app = FastAPI(
    title="Aushadhi Vault — AI Service",
    description=(
        "Vision AI prescription scanner + LangChain inventory agent. "
        "Built for AMD Hackathon Track 3."
    ),
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── ROUTES ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Aushadhi Vault AI",
        "status": "running",
        "mode": "mock" if USE_MOCK else "live",
        "endpoints": {
            "scan_prescription": "POST /scan-prescription",
            "inventory_report": "GET  /inventory-report",
            "inventory_raw":    "GET  /inventory",
            "expiry_alerts":    "GET  /expiry-alerts",
            "low_stock":        "GET  /low-stock",
            "health":           "GET  /health"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "aushadhi-vault-ai", "mock": USE_MOCK}


@app.post("/scan-prescription")
async def scan_prescription_endpoint(
    file: UploadFile = File(...),
    mock: bool = Query(default=False, description="Use mock response instead of GPU")
):
    """
    Upload a prescription image (jpg/png/webp).
    Returns extracted medicine names, dosages, quantities as JSON.
    Called by Payal's backend at POST /bills/from-prescription
    """
    if mock or USE_MOCK:
        return scan_prescription_mock()

    # Validate
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Send jpg, png, or webp."
        )

    image_bytes = await file.read()

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file received.")

    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 15MB.")

    result = scan_prescription(image_bytes)

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Vision model error: {result.get('error', 'Unknown error')}"
        )

    return result


@app.get("/inventory-report")
def inventory_report_endpoint(
    mock: bool = Query(default=False, description="Use mock report instead of GPU agent")
):
    """
    Triggers the LangChain inventory monitoring agent.
    Returns a full daily report: expiry alerts, low stock, reorder suggestions.
    Called by Payal's backend and Saumya's frontend dashboard.
    """
    if mock or USE_MOCK:
        return generate_report_mock()

    result = generate_daily_report()

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {result.get('error')}"
        )

    return result


@app.get("/inventory")
def get_inventory():
    """
    Returns raw inventory list.
    Useful for Payal's backend to match medicine names from prescriptions.
    """
    try:
        items = get_all_inventory()
        return {"success": True, "count": len(items), "inventory": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/expiry-alerts")
def expiry_alerts(days: int = Query(default=30, ge=1, le=365)):
    """Returns medicines expiring within N days. Default 30."""
    try:
        items = get_expiring_medicines(days)
        return {
            "success": True,
            "days_threshold": days,
            "count": len(items),
            "medicines": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/low-stock")
def low_stock(threshold: int = Query(default=10, ge=1)):
    """Returns medicines with quantity below threshold. Default 10."""
    try:
        items = get_low_stock_medicines(threshold)
        return {
            "success": True,
            "threshold": threshold,
            "count": len(items),
            "medicines": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── RUN ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
