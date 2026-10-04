"""
Chat router — accept a question and return an AI-generated answer with citations.
"""

from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.rag import ask as rag_ask
from app.config import settings

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask a question about one or more uploaded documents.

    The server will:
      1. Embed the question
      2. Search the vector store for the most relevant chunks
      3. Build a prompt with context
      4. Call OpenAI for an answer with citations

    If document_ids is omitted, all documents are searched.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is not configured. "
                   "Set OPENAI_API_KEY in your .env file and restart.",
        )

    response = rag_ask(
        question=request.question.strip(),
        document_ids=request.document_ids,
    )
    return response