from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from weasyprint import HTML


APP_NAME = "Guardian Gateway Audit Service"
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RECEIPT_DIR = BASE_DIR / "receipts"
TEMPLATE_DIR = BASE_DIR

UPLOAD_DIR.mkdir(exist_ok=True)
RECEIPT_DIR.mkdir(exist_ok=True)

REQUIRED_CHECKS = ["Source", "Hash", "Manifest", "Risk", "Policy"]

RED_FLAG_TERMS = [
    "override policy",
    "external command",
    "sensitive data",
    "ignore previous instructions",
    "bypass security",
    "disable guardrails",
    "exfiltrate",
    "system prompt",
    "developer message",
    "execute shell",
    "run command",
]

BLOCKED_ACTIONS = {
    "execute_code",
    "external_command",
    "store_sensitive",
    "bypass_policy",
    "override_policy",
}

app = FastAPI(title=APP_NAME, version="0.1.0")

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class AuditCheck(BaseModel):
    name: str
    status: str
    detail: str


class AuditResult(BaseModel):
    receipt_id: str
    transaction_id: str
    decision: str
    file_name: str
    file_sha256: str
    manifest_sha256: Optional[str]
    timestamp_utc: str
    red_flags_found: List[str] = Field(default_factory=list)
    checks: List[AuditCheck]
    receipt_pdf_path: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_text_safely(path: Path, max_bytes: int = 2_000_000) -> str:
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="ignore")


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest is not valid JSON: {exc}") from exc


def find_red_flags(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for term in RED_FLAG_TERMS:
        pattern = re.escape(term.lower())
        if re.search(pattern, lowered):
            found.append(term)
    return sorted(set(found))


def validate_policy(manifest: Dict[str, Any]) -> tuple[bool, str]:
    allowed_actions = manifest.get("allowed_actions")
    retention_policy = manifest.get("retention_policy")

    if not isinstance(allowed_actions, list):
        return False, "Manifest missing allowed_actions list."

    if not isinstance(retention_policy, dict):
        return False, "Manifest missing retention_policy object."

    blocked_requested = sorted(set(allowed_actions).intersection(BLOCKED_ACTIONS))
    if blocked_requested:
        return False, f"Manifest requests blocked action(s): {', '.join(blocked_requested)}."

    if "store_raw" not in retention_policy:
        return False, "Retention policy missing store_raw field."

    if "store_receipt" not in retention_policy:
        return False, "Retention policy missing store_receipt field."

    return True, "Policy fields present and no blocked actions requested."


def render_receipt_pdf(result: Dict[str, Any], output_path: Path) -> None:
    template = jinja_env.get_template("audit_template.html")
    html = template.render(**result)
    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(str(output_path))


def audit_intake(file_path: str) -> AuditResult:
    artifact_path = Path(file_path).resolve()

    if not artifact_path.exists() or not artifact_path.is_file():
        raise FileNotFoundError(f"File not found: {artifact_path}")

    manifest_path = artifact_path.with_name("manifest.json")
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    transaction_id = f"txn_{uuid.uuid4().hex}"
    receipt_id = f"rcpt_{uuid.uuid4().hex}"

    file_hash = sha256_file(artifact_path)
    manifest_hash = sha256_file(manifest_path) if manifest_path.exists() else None

    checks: List[AuditCheck] = []

    source_ok = artifact_path.stat().st_size > 0
    checks.append(
        AuditCheck(
            name="Source",
            status="PASS" if source_ok else "FAIL",
            detail="Source file exists and is readable." if source_ok else "Source file is empty or unreadable.",
        )
    )

    manifest_ok = manifest_path.exists()
    manifest: Dict[str, Any] = {}

    if manifest_ok:
        try:
            manifest = load_manifest(manifest_path)
            checks.append(
                AuditCheck(
                    name="Manifest",
                    status="PASS",
                    detail="manifest.json found and parsed successfully.",
                )
            )
        except ValueError as exc:
            manifest_ok = False
            checks.append(
                AuditCheck(
                    name="Manifest",
                    status="FAIL",
                    detail=str(exc),
                )
            )
    else:
        checks.append(
            AuditCheck(
                name="Manifest",
                status="FAIL",
                detail="No manifest.json found next to source file.",
            )
        )

    expected_hash = manifest.get("artifact_sha256") if manifest_ok else None
    hash_ok = bool(expected_hash and expected_hash == file_hash)

    checks.append(
        AuditCheck(
            name="Hash",
            status="PASS" if hash_ok else "FAIL",
            detail=(
                "Artifact SHA-256 matches manifest."
                if hash_ok
                else "Artifact SHA-256 missing from manifest or does not match."
            ),
        )
    )

    raw_text = read_text_safely(artifact_path)
    red_flags = find_red_flags(raw_text)
    risk_ok = len(red_flags) == 0

    checks.append(
        AuditCheck(
            name="Risk",
            status="PASS" if risk_ok else "FAIL",
            detail=(
                "No configured red-flag terms detected."
                if risk_ok
                else f"Detected red-flag term(s): {', '.join(red_flags)}."
            ),
        )
    )

    if manifest_ok:
        policy_ok, policy_detail = validate_policy(manifest)
    else:
        policy_ok, policy_detail = False, "Policy cannot be verified without valid manifest."

    checks.append(
        AuditCheck(
            name="Policy",
            status="PASS" if policy_ok else "FAIL",
            detail=policy_detail,
        )
    )

    all_passed = all(check.status == "PASS" for check in checks)
    decision = "ALLOW" if all_passed else "BLOCK"

    pdf_path = RECEIPT_DIR / f"{receipt_id}.pdf"

    result_payload = {
        "app_name": APP_NAME,
        "receipt_id": receipt_id,
        "transaction_id": transaction_id,
        "decision": decision,
        "file_name": artifact_path.name,
        "file_sha256": file_hash,
        "manifest_sha256": manifest_hash or "N/A",
        "timestamp_utc": timestamp_utc,
        "checks": [check.model_dump() for check in checks],
        "red_flags_found": red_flags,
    }

    render_receipt_pdf(result_payload, pdf_path)

    return AuditResult(
        receipt_id=receipt_id,
        transaction_id=transaction_id,
        decision=decision,
        file_name=artifact_path.name,
        file_sha256=file_hash,
        manifest_sha256=manifest_hash,
        timestamp_utc=timestamp_utc,
        red_flags_found=red_flags,
        checks=checks,
        receipt_pdf_path=str(pdf_path),
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": APP_NAME}


@app.post("/audit")
async def audit_upload(
    artifact: UploadFile = File(...),
    manifest: Optional[UploadFile] = File(None),
) -> JSONResponse:
    safe_name = Path(artifact.filename or f"artifact_{uuid.uuid4().hex}.txt").name
    workspace = UPLOAD_DIR / uuid.uuid4().hex
    workspace.mkdir(parents=True, exist_ok=True)

    artifact_path = workspace / safe_name
    artifact_path.write_bytes(await artifact.read())

    if manifest is not None:
        manifest_path = workspace / "manifest.json"
        manifest_path.write_bytes(await manifest.read())

    try:
        result = audit_intake(str(artifact_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = result.model_dump()
    response["receipt_download_url"] = f"/receipt/{Path(result.receipt_pdf_path).name}"
    return JSONResponse(response)


@app.get("/receipt/{receipt_file}")
def get_receipt(receipt_file: str) -> FileResponse:
    safe_name = Path(receipt_file).name
    receipt_path = RECEIPT_DIR / safe_name

    if not receipt_path.exists() or receipt_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Receipt not found.")

    return FileResponse(
        str(receipt_path),
        media_type="application/pdf",
        filename=safe_name,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)