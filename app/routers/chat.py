"""
Chat router — accept a question and return an AI-generated answer with citations.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.config import settings
from app.models.chat import ChatRequest, ChatResponse
from app.security.rate_limit import enforce_limit, chat_limiter
from app.services.provider_errors import raise_safe_provider_error
from app.services.rag import ask as rag_ask

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Ask a question about one or more uploaded documents.

    The server will:
      1. Embed the question
      2. Search the vector store for the most relevant chunks
      3. Build a prompt with context
      4. Call the configured chat provider for an answer with citations

    If document_ids is omitted, all documents are searched.
    """
    enforce_limit(chat_limiter, user.id)
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not settings.chat_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chat provider API key is not configured. Set the provider key in your .env file and restart.",
        )

    try:
        return rag_ask(
            question=request.question.strip(),
            user_id=user.id,
            document_ids=request.document_ids,
        )
    except Exception as exc:
        raise_safe_provider_error(exc, "chat")
        raise AssertionError("unreachable")  # pragma: no cover
