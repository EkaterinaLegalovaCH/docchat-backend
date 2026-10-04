"""
RAG (Retrieval-Augmented Generation) orchestration.

This service ties together:
  1. Embed the user's question
  2. Search the vector store for similar chunks
  3. Build a prompt with those chunks as context
  4. Call OpenAI to generate an answer with citations
"""

from openai import OpenAI
from typing import List, Optional

from app.config import settings
from app.services.embeddings import embed_text
from app.db.supabase import search_chunks, SupabaseChunk
from app.models.chat import ChatResponse, Citation


def _build_context(chunks: List[SupabaseChunk]) -> str:
    """Format retrieved chunks into a single context string for the LLM."""
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[SOURCE {i}] Document: {c.document_name} | Page: {c.page_number}\n"
            f"{c.text}\n"
        )
    return "\n---\n".join(parts)


def _build_prompt(question: str, context: str) -> str:
    """Build a system + user prompt that forces the LLM to cite sources."""
    system = (
        "You are a helpful document-assistant. Answer the user's question "
        "based ONLY on the provided context. If the context doesn't contain "
        "the answer, say so clearly — do not make up information.\n\n"
        "For every claim you make, cite the source by referencing the "
        "SOURCE number in brackets, like [SOURCE 1]. "
        "At the end, list each source you cited with its document name and page number."
    )
    user = f"Context:\n{context}\n\nQuestion: {question}"
    return system, user


def ask(
    question: str,
    document_ids: Optional[List[str]] = None,
) -> ChatResponse:
    """
    Full RAG pipeline: embed → search → prompt → answer → citations.

    Parameters
    ----------
    question : str
        The user's natural-language question.
    document_ids : list of str or None
        If provided, restrict the vector search to these documents.

    Returns
    -------
    ChatResponse with answer text and structured citations.
    """
    # 1. Embed the question
    question_vector = embed_text(question)

    # 2. Retrieve top-K relevant chunks
    top_k = 5
    similar_chunks = search_chunks(
        query_vector=question_vector,
        top_k=top_k,
        document_ids=document_ids,
    )

    if not similar_chunks:
        return ChatResponse(
            answer="I couldn't find any relevant content in the uploaded documents "
                   "to answer your question. Try uploading documents first or "
                   "rephrase your question.",
            citations=[],
            model=settings.openai_model,
        )

    # 3. Build context and prompt
    context = _build_context(similar_chunks)
    system_prompt, user_prompt = _build_prompt(question, context)

    # 4. Call OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,  # low temp = more factual, less creative
    )

    answer_text = response.choices[0].message.content or ""

    # 5. Build structured citations from the retrieved chunks
    citations = [
        Citation(
            document_id=c.document_id,
            document_name=c.document_name,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            text_snippet=c.text[:200],  # first 200 chars as excerpt
        )
        for c in similar_chunks
    ]

    return ChatResponse(
        answer=answer_text,
        citations=citations,
        model=settings.openai_model,
    )