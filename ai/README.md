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
- `GET  http://localhost:8002/inventory`         — full medicine list
- `GET  http://localhost:8002/expiry-alerts`     — expiring medicines
- `GET  http://localhost:8002/low-stock`         — low stock medicines
