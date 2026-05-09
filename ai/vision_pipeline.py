import base64
import json
import os
import re
from io import BytesIO

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from PIL import Image
except ImportError:
    Image = None

# Talks to your local vLLM server
client = None
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
VISION_MODEL = os.getenv("VISION_MODEL", "meta-llama/Llama-3.2-11B-Vision-Instruct")


def get_client():
    global client
    if OpenAI is None:
        raise RuntimeError("openai is not installed. Install ai/requirements.txt for live scanning.")
    if client is None:
        client = OpenAI(
            base_url=VLLM_BASE_URL,
            api_key=os.getenv("VLLM_API_KEY", "dummy-key")
        )
    return client

EXTRACTION_PROMPT = """You are an expert at reading Indian medical prescriptions.
Look at this prescription image carefully and extract ALL medicines.

Return ONLY a valid JSON object. No explanation. No extra text. Just JSON.

Format:
{
  "medicines": [
    {
      "name": "Full medicine name with strength",
      "dosage": "500mg or 10ml or as directed",
      "quantity": 2,
      "frequency": "once daily"
    }
  ],
  "doctor_name": "Dr. name if visible or null",
  "patient_name": "Patient name if visible or null",
  "date": "Date if visible or null",
  "notes": "Any special instructions if visible or null"
}

Rules:
- Always include dosage/strength in the medicine name if readable
- If quantity is unclear write 1
- If frequency is unclear write "as directed"
- Extract every single medicine you can see
- Return only JSON, nothing else
"""

def encode_image(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string"""
    try:
        # Resize if too large to save tokens
        img = Image.open(BytesIO(image_bytes)) if Image else None
        if img and (img.width > 1200 or img.height > 1200):
            img.thumbnail((1200, 1200), Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
    except Exception:
        pass  # Use original if PIL fails
    return base64.b64encode(image_bytes).decode("utf-8")


def parse_json_safely(text: str) -> dict:
    """Extract JSON from model response even if it adds extra text"""
    # Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find JSON object in response
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {
        "medicines": [],
        "parse_error": True,
        "raw_response": text[:500]
    }


def scan_prescription(image_bytes: bytes) -> dict:
    """
    Main entry point.
    Input  : image bytes (jpg/png/webp)
    Output : dict with extracted medicines and metadata
    """
    try:
        image_b64 = encode_image(image_bytes)
        openai_client = get_client()

        response = openai_client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT
                        }
                    ]
                }
            ],
            max_tokens=1024,
            temperature=0.05   # Very low — we need consistent structured output
        )

        raw = response.choices[0].message.content
        parsed = parse_json_safely(raw)

        return {
            "success": True,
            "data": parsed,
            "model": VISION_MODEL,
            "medicines_count": len(parsed.get("medicines", []))
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {"medicines": []},
            "medicines_count": 0
        }


def scan_prescription_mock() -> dict:
    """
    Returns fake data for testing without GPU.
    Call this if vLLM server is not running.
    """
    return {
        "success": True,
        "data": {
            "medicines": [
                {"name": "Paracetamol 500mg", "dosage": "500mg", "quantity": 2, "frequency": "twice daily"},
                {"name": "Azithromycin 250mg", "dosage": "250mg", "quantity": 1, "frequency": "once daily"},
                {"name": "Cetirizine 10mg", "dosage": "10mg", "quantity": 1, "frequency": "at night"}
            ],
            "doctor_name": "Dr. Ramesh Kumar",
            "patient_name": "Ravi Sharma",
            "date": "2025-05-09",
            "notes": "Take after meals"
        },
        "model": "MOCK",
        "medicines_count": 3
    }
