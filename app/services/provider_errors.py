"""Translate provider failures into safe API-facing exceptions."""

import logging

from fastapi import HTTPException
from openai import APIStatusError

logger = logging.getLogger(__name__)


def raise_safe_provider_error(
    exc: Exception,
    operation: str,
    fallback_detail: str = "The AI provider is temporarily unavailable.",
    fallback_status: int = 503,
) -> None:
    """Raise a sanitized error without mislabeling non-provider failures."""
    if not isinstance(exc, APIStatusError):
        logger.exception("%s failed", operation)
        raise HTTPException(status_code=fallback_status, detail=fallback_detail) from None

    logger.exception("OpenAI %s failed", operation)
    if exc.status_code == 401:
        raise HTTPException(status_code=503, detail="The AI provider is not configured correctly.") from None
    if exc.status_code == 429:
        raise HTTPException(status_code=429, detail="The AI provider is temporarily rate limited.") from None
    raise HTTPException(status_code=503, detail="The AI provider is temporarily unavailable.") from None
