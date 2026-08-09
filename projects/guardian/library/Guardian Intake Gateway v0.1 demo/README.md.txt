# Guardian Intake Gateway - v0.1 Demo

1. Install: `pip install -r requirements.txt`
2. Run: `python main.py`
3. Test in another terminal or browser:

Clean example:
```bash
curl -X POST http://localhost:8000/v1/audit-intake \
  -H "Content-Type: application/json" \
  -d '{
    "artifact": "'"$(base64 -w 0 sample_clean.txt)"'",
    "manifest": {
      "source": "user_upload",
      "filename": "q3_review.pdf",
      "content_type": "application/pdf",
      "uploader_id": "user_123",
      "purpose": "rag_index",
      "retention_days": 90
    }
  }'