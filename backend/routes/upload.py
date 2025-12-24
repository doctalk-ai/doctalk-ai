from fastapi import APIRouter, UploadFile, File
from backend.services.embedding_service import get_embedding
from backend.core.clients import supabase_client
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import io
import asyncio
from backend.core.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    logger.info(f"Starting upload for file: {file.filename} ({file.content_type})")
    contents = await file.read()
    try:
    # 2. Extract text with pypdf or plain text
        if file.content_type == "application/pdf":
            file_text = "" # Initialize empty string to hold text and avoid reference before assignment
            reader = PdfReader(io.BytesIO(contents))
            for page in reader.pages: 
                file_text += page.extract_text() + "\n"
                logger.info(f" Extracted {len(file_text)} characters of text")
        elif file.content_type == "text/plain":
            # Try UTF-8 first, if that fails, try Turkish Windows encoding
            try:
                file_text = contents.decode("utf-8")
            except UnicodeDecodeError:
                file_text = contents.decode("cp1254")  # Common for Turkish Windows files
                logger.info(f" Extracted {len(file_text)} characters of text")
        else:
            logger.error(f"Unsupported file type uploaded.{file.content_type}")
            return {"error": "Unsupported file type. Please upload a PDF or TXT file."}
    except Exception as e:
        logger.error(f"Error extracting text from file: {e}")
        return {"error": f"Failed to extract text: {str(e)}"}
    
    # Split text
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(file_text)

    # Create document
    doc = supabase_client.table("documents").insert({"file_name": file.filename}).execute()
    doc_id = doc.data[0]["id"]

    # Store chunks
    for i, chunk in enumerate(chunks):
        await asyncio.sleep(1)
        embedding = await get_embedding(chunk)
        supabase_client.table("document_chunks").insert({
            "document_id": doc_id,
            "chunk_text": chunk,
            "embedding": embedding
        }).execute()
        logger.debug(f"Stored chunk {i + 1}/{len(chunks)} for document ID {doc_id}")

    return {"message": "Uploaded", "document_id": doc_id, "chunks": len(chunks)}
    
