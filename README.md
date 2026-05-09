# WTF-NINJA
# Aushadhi Vault — AI Service

Vision prescription scanner + LangChain inventory agent.
Built on AMD MI300X with ROCm for the AMD Hackathon Track 3.

---

## Setup (Run these commands on AMD Developer Cloud instance)

### Step 1 — Verify ROCm
```bash
rocm-smi
```

### Step 2 — Install PyTorch with ROCm
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1
python3 -c "import torch; print('GPU:', torch.cuda.get_device_name(0))"
```

### Step 3 — Install dependencies
```bash
cd ai/
pip install -r requirements.txt
```

### Step 4 — Set HuggingFace token
```bash
export HF_TOKEN=your_token_here
```
Get your token at: https://huggingface.co/settings/tokens
Accept Llama 3.2 license at: https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct

### Step 5 — Start vLLM server (Terminal 1, keep running)
```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.2-11B-Vision-Instruct \
  --host 0.0.0.0 \
  --port 8001 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.9 \
  --trust-remote-code
```
Wait until you see: `Application startup complete`

### Step 6 — Start AI FastAPI server (Terminal 2)
```bash
cd ai/
python main.py
```
Runs on: http://0.0.0.0:8002

---

## Test Endpoints

```bash
# Health check
curl http://localhost:8002/health

# Inventory report (mock — no GPU needed)
curl "http://localhost:8002/inventory-report?mock=true"

# Inventory report (real — needs vLLM running)
curl http://localhost:8002/inventory-report

# Expiry alerts
curl http://localhost:8002/expiry-alerts

# Low stock
curl http://localhost:8002/low-stock

# Prescription scan (mock)
curl -X POST "http://localhost:8002/scan-prescription?mock=true" \
  -F "file=@any_image.jpg"

# Prescription scan (real)
curl -X POST http://localhost:8002/scan-prescription \
  -F "file=@prescription.jpg"
```

---

## Mock Mode (if GPU not ready yet)

Run without vLLM for testing:
```bash
USE_MOCK=true python main.py
```

---

## Ports Summary (tell teammates)

| Service        | Port  | Owner    |
|----------------|-------|----------|
| vLLM server    | 8001  | Shahrukh |
| AI FastAPI     | 8002  | Shahrukh |
| Backend API    | 8000  | Payal    |
| Frontend       | browser | Saumya |

---

## What Payal needs to call

- `POST http://localhost:8002/scan-prescription` — upload prescription image
- `GET  http://localhost:8002/inventory-report`  — daily agent report

- # Aushadhi Vault — Backend API

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
- `GET  http://localhost:8002/inventory`         — full medicine list
- `GET  http://localhost:8002/expiry-alerts`     — expiring medicines
- `GET  http://localhost:8002/low-stock`         — low stock medicines
