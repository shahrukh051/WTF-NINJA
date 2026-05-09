from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from database import init_db
from seed_data import seed
from routes.medicines import router as medicines_router
from routes.inventory import router as inventory_router
from routes.bills     import router as bills_router
from routes.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Aushadhi Vault Backend starting...")
    init_db()
    seed()
    print("Ready on http://0.0.0.0:8000")
    print("Docs at http://0.0.0.0:8000/docs")
    yield
    print("Backend shutting down")


app = FastAPI(
    title="Aushadhi Vault — Backend API",
    description="Pharmacy management backend. Built for AMD Hackathon.",
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

# Register all routers
app.include_router(medicines_router)
app.include_router(inventory_router)
app.include_router(bills_router)
app.include_router(analytics_router)


@app.get("/")
def root():
    return {
        "service": "Aushadhi Vault Backend",
        "status":  "running",
        "docs":    "/docs",
        "routes": {
            "medicines":  "/medicines",
            "inventory":  "/inventory",
            "bills":      "/bills",
            "analytics":  "/analytics"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "aushadhi-vault-backend"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
