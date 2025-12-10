from fastapi import APIRouter, UploadFile, File
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
load_dotenv()  # Loads from .env file
from core.database import supabase
import io
import asyncio
from services.embedding_service import get_embedding

router=APIRouter() # Create a router instance 

@router.post("/upload") # Use router instead of app,
async def upload_file(file: UploadFile = File(...)):
    
    print(f" Received file: {file.filename}")
    
    # 1. Read file contents
    contents = await file.read()
    
    # 2. Extract text with pypdf or plain text
    if file.content_type == "application/pdf":
        file_text = "" # Initialize empty string to hold text andf avoid reference before assignment
        reader = PdfReader(io.BytesIO(contents))
        for page in reader.pages: 
            file_text += page.extract_text() + "\n"
            print(f" Extracted {len(file_text)} characters of text")
    elif file.content_type == "text/plain":
        # Try UTF-8 first, if that fails, try Turkish Windows encoding
        try:
            file_text = contents.decode("utf-8")
        except UnicodeDecodeError:
            file_text = contents.decode("cp1254")  # Common for Turkish Windows files
            print(f" Extracted {len(file_text)} characters of text")
    else:
        return {"error": "Unsupported file type. Please upload a PDF or TXT file."}
            
    print(f"Extracted {len(file_text)} characters from TXT")   
    # 3. Chunk text with LangChain
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, # chunk size can be change as needed based on use case and model limits
        chunk_overlap=200 # overlap to maintain context between chunks 
    )
    chunks = text_splitter.split_text(file_text)
    
    print(f" Split into {len(chunks)} chunks")
    
    # 4. store document in db
    print("💾 Storing document in database...")
    document_data = {
        "file_name": file.filename
    }
    document_response = supabase.table("documents").insert(document_data).execute()
    document_id = document_response.data[0]["id"]
    print(f"   Document stored with ID: {document_id}")
    
    # 5. gen embeddings and store chunks
    print(" Generating embeddings and storing chunks...")
    stored_chunks = 0
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(2)  # To avoid rate limits
        embedding = await get_embedding(chunk)
        if not any(embedding): # Check for zero vector indicating an error
            print(f"  Skipping chunk {i+1} due to embedding error")
            continue
        
        chunk_data = {
            "document_id": document_id,
            "chunk_text": chunk,
            "embedding": embedding
        }
        supabase.table("document_chunks").insert(chunk_data).execute()
        stored_chunks += 1

        if embedding :
            print(f" stored chunk {i+1}/{len(chunks)}")
        else:
            print(f" failed to store chunk {i+1}/{len(chunks)}")
        
        # print preview of first 2 chunks
        if i < 2:
            print(f" preview chunk {i+1}: {len(embedding)} dimensions - {embedding[:3]}...")
    
    print(f"successfully stored {stored_chunks} chunks in database")
    
    return {
        "filename": file.filename,
        "text_length": len(file_text),
        "chunk_count": len(chunks),
        "document_id": document_id,
        "stored_chunks": stored_chunks,
        "message": "PDF or TXT file successfully processed and stored in database!"
    }