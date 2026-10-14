import pytest
from fastapi import HTTPException

from app.services.provider_errors import raise_safe_provider_error


def test_non_provider_failures_keep_document_processing_message():
    with pytest.raises(HTTPException) as exc:
        raise_safe_provider_error(
            ValueError("bad PDF"),
            "document processing",
            fallback_detail="Document processing failed. Please try again.",
            fallback_status=500,
        )

    assert exc.value.status_code == 500
    assert exc.value.detail == "Document processing failed. Please try again."
