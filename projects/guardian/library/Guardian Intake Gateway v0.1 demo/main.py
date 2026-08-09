from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import hashlib
import json
from datetime import datetime
from jinja2 import Template
import base64

app = FastAPI(title="Guardian Intake Gateway v0.1")

class Manifest(BaseModel):
    source: str
    filename: str
    content_type: str
    uploader_id: str
    purpose: str  # e.g. "rag_index", "chat_summary", "agent_tool"
    retention_days: Optional[int] = 90

class IntakeRequest(BaseModel):
    artifact: str  # base64 encoded content (for demo) or URL/reference
    manifest: Manifest
    context: Optional[Dict] = None

class IntakeDecision(BaseModel):
    decision: str  # ALLOW | HOLD | BLOCK
    risk_score: float  # 0.0 - 1.0
    receipt_id: str
    reasons: List[str]
    timestamp: str
    allowed_actions: List[str]
    receipt_summary: str

# Simple risk scanner
RED_FLAGS = ["ignore previous instructions", "ignore company policy", "reveal confidential", "bypass security"]
SENSITIVE_PATTERNS = ["password", "ssn", "credit card", "confidential", "proprietary"]

def scan_content(content: str) -> tuple[float, List[str]]:
    content_lower = content.lower()
    reasons = []
    score = 0.0

    # Hash check simulation
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

    for flag in RED_FLAGS:
        if flag in content_lower:
            reasons.append(f"Hidden instruction detected: '{flag}'")
            score += 0.4

    for pattern in SENSITIVE_PATTERNS:
        if pattern in content_lower:
            reasons.append(f"Sensitive data pattern: {pattern}")
            score += 0.3

    if score > 0.8:
        decision = "BLOCK"
    elif score > 0.3:
        decision = "HOLD"
    else:
        decision = "ALLOW"

    return min(score, 1.0), reasons, decision, content_hash

@app.post("/v1/audit-intake", response_model=IntakeDecision)
async def audit_intake(request: IntakeRequest):
    # Decode artifact (demo uses base64 text)
    try:
        content = base64.b64decode(request.artifact).decode('utf-8')
    except:
        content = request.artifact  # fallback for plain text

    risk_score, reasons, decision, content_hash = scan_content(content)

    receipt_id = f"grd_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{content_hash}"

    allowed_actions = ["summarize"] if decision == "ALLOW" else []
    if decision == "ALLOW":
        allowed_actions.extend(["store", "index", "send_to_model"])

    decision_obj = IntakeDecision(
        decision=decision,
        risk_score=risk_score,
        receipt_id=receipt_id,
        reasons=reasons or ["No red flags detected"],
        timestamp=datetime.utcnow().isoformat(),
        allowed_actions=allowed_actions,
        receipt_summary=f"Guardian Intake Receipt - {decision}"
    )

    # In real version, generate PDF here (async)
    return decision_obj

# Simple receipt HTML preview
@app.get("/receipt/{receipt_id}")
async def get_receipt(receipt_id: str):
    template = Template("""
    <html><body style="font-family: Arial; max-width: 800px; margin: 40px;">
    <h1>Guardian Intake Receipt</h1>
    <p><strong>Receipt ID:</strong> {{ receipt_id }}</p>
    <p><strong>Decision:</strong> <span style="color:{% if decision=='ALLOW' %}green{% elif decision=='HOLD' %}orange{% else %}red{% endif %}">{{ decision }}</span></p>
    <p><strong>Risk Score:</strong> {{ risk_score }}</p>
    <p><strong>Timestamp:</strong> {{ timestamp }}</p>
    <h3>Reasons:</h3>
    <ul>{% for reason in reasons %}<li>{{ reason }}</li>{% endfor %}</ul>
    <h3>Allowed Actions:</h3>
    <ul>{% for action in allowed_actions %}<li>{{ action }}</li>{% endfor %}</ul>
    <hr>
    <p><small>Guardian Intake Gateway v0.1 • Zero-Trust AI Context Boundary</small></p>
    </body></html>
    """)
    # For demo we just return placeholder - in real version render actual data
    return {"message": "Receipt preview available in production version", "id": receipt_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)