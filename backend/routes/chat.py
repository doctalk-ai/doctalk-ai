from fastapi import APIRouter
from services.llm_service import generate_answer
from services.embedding_service import get_embedding
from core.database import supabase

router = APIRouter()

@router.post("/chat")

async def chat_with_document(question: str, document_id: str):
    print(f"chat question: {question}")
    print(f"querying document: {document_id}")
    
    # 1. embed the question
    question_embedding = get_embedding(question)
    print(f"🧠 Question embedded with {len(question_embedding)} dimensions")
    
    # 2. locate similar chunks using vector search
    print("searching for relevant chunks...")
    response = supabase.rpc(
        'match_chunks',
        {
            'query_embedding': question_embedding,
            'match_count': 5,
            'filter_document_id': document_id  # Changed from 'document_id'
        }
    ).execute()
    
    relevant_chunks = response.data
    print(f"found {len(relevant_chunks)} relevant chunks")
    
    # 3. biuld context from relevant chunks
    context = "\n\n".join([chunk['chunk_text'] for chunk in relevant_chunks])
    
    # 4. gen ai response
    print("generating AI response...")
    answer = generate_answer(question, context)
    if len(answer) > 0:
        print(f" Answer received: {answer}")
    else:
        print(f" Error: couldn't get answer")



    return {
        "question": question,
        "document_id": document_id,
        "relevant_chunks_count": len(relevant_chunks),
        "answer": answer
    }