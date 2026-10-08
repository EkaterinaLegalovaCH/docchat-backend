#!/usr/bin/env python3
"""Full end-to-end smoke test: upload PDF → embedding → question → citations → deletion."""

import json
import os
import sys
from pathlib import Path

import httpx

BASE = os.environ.get("DOCCHAT_BASE_URL", "http://127.0.0.1:8000")
PDF_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "smoke_document.pdf"

with httpx.Client(timeout=120) as client:
    # Upload
    pdf_bytes = PDF_PATH.read_bytes()
    upload = client.post(
        f"{BASE}/api/documents/upload",
        files={"file": (PDF_PATH.name, pdf_bytes, "application/pdf")},
    )
    print(f"upload_status {upload.status_code}")
    upload.raise_for_status()
    document = upload.json()
    doc_id = document["id"]
    print(
        "uploaded_document",
        json.dumps(
            {k: document.get(k) for k in ("id", "filename", "page_count", "chunk_count", "status")},
            sort_keys=True,
        ),
    )

    # Ask a question
    try:
        question = client.post(
            f"{BASE}/api/chat/ask",
            json={
                "question": "Which embedding model and dimension does DocChat use?",
                "document_ids": [doc_id],
            },
        )
        print(f"question_status {question.status_code}")
        question.raise_for_status()
        answer = question.json()
        print(f"answer_model {answer.get('model')}")
        print(f"citation_count {len(answer.get('citations', []))}")
        print("answer", answer.get("answer", "").replace("\n", " ")[:500])
    finally:
        # Delete and verify cleanup
        deleted = client.delete(f"{BASE}/api/documents/{doc_id}")
        print(f"delete_status {deleted.status_code}")
        deleted.raise_for_status()

        remaining = client.get(f"{BASE}/api/documents")
        print(f"list_status {remaining.status_code}")
        remaining.raise_for_status()
        present = any(item.get("id") == doc_id for item in remaining.json().get("documents", []))
        print(f"document_present_after_delete {present}")