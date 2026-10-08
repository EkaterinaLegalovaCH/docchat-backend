#!/usr/bin/env bash
set -euo pipefail

pdf_path="${1:?Usage: ./scripts/smoke_test.sh path/to/file.pdf}"
base_url="${DOCCHAT_BASE_URL:-http://localhost:8000}"

upload_response="$(curl --fail-with-body -sS -F "file=@${pdf_path}" "${base_url}/api/documents/upload")"
document_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${upload_response}")"
trap 'curl --fail-with-body -sS -X DELETE "${base_url}/api/documents/${document_id}" >/dev/null || true' EXIT

curl --fail-with-body -sS "${base_url}/api/health"
printf '\n'
curl --fail-with-body -sS "${base_url}/api/ready"
printf '\nUploaded document: %s\n' "${document_id}"
printf '%s\n' 'Ask a question through the UI or /api/chat, then verify citations before deletion.'
