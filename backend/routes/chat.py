from fastapi import APIRouter
from backend.services.embedding_service import get_embedding
from backend.services.answer_service import generate_answer
from backend.core.clients import supabase_client
from backend.core.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat")
async def chat(question: str, document_id: str):
    embedding = await get_embedding(question)

    # vector search
    res = supabase_client.rpc("match_chunks", {
        "query_embedding": embedding,
        "match_count": 5,
        "filter_document_id": document_id
    }).execute()
    logger.debug(f"Vector search returned {len(res.data)} chunks for document ID {document_id}")

    chunks = res.data
    context = "\n".join([c["chunk_text"] for c in chunks])
    logger.info(f"Constructed context of length {len(context)} for question.")

    answer = generate_answer(question, context)
    logger.info("Answer generated successfully.")

    return {
        "question": question,
        "chunks": len(chunks),
        "answer": answer
    }
logger.debug("Chat endpoint setup complete.")
