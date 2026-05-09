# Aushadhi Vault — Backend API

FastAPI backend with SQLite. Handles medicines, inventory, billing, analytics.

---

## Setup

```bash
cd backend/
pip install -r requirements.txt
python main.py
```

Runs on: http://localhost:8000
API docs: http://localhost:8000/docs

---

## Key Endpoints

### Medicines
| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | /medicines | List all medicines with stock |
| POST | /medicines | Add new medicine |
| PUT | /medicines/{id} | Update medicine details |
| DELETE | /medicines/{id} | Delete medicine |

### Inventory
| Method | Endpoint | What it does |
|--------|----------|--------------|
| PUT | /inventory/restock | Add stock to a medicine |
| GET | /inventory/expiry-alerts | Medicines expiring within 30 days |
| GET | /inventory/low-stock | Medicines below 10 units |
| GET | /inventory/summary | Dashboard summary counts |

### Billing
| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | /bills | List all bills |
| GET | /bills/{id} | Single bill detail |
| POST | /bills/create | Create bill manually |
| POST | /bills/from-prescription | Create bill from AI-extracted medicines |
| POST | /bills/scan-and-bill | Upload image → scan → create bill (one shot) |
| GET | /bills/today/summary | Today's revenue |

### Analytics
| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | /analytics/top-medicines | Top 10 selling medicines |
| GET | /analytics/revenue?period=weekly | Revenue breakdown |
| GET | /analytics/expiry-risk | Stock value at expiry risk |
| GET | /analytics/dashboard | All dashboard data in one call |

---

## For Saumya (Frontend)

Call `/analytics/dashboard` once on page load — it gives everything 
needed for the dashboard: summary cards, recent bills, 7-day revenue trend.

---

## Ports
| Service | Port |
|---------|------|
| This backend | 8000 |
| Shahrukh's AI service | 8002 |
| Shahrukh's vLLM server | 8001 |
