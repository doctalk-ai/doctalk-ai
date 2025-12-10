import asyncio
import google.generativeai as genai


# embedding service using Google Generative AI 


async def get_embedding(text: str) -> list:
    """Get embedding vector using Google's embedding model"""
    for attempt in range(3): # Retry up to 3 times on failure
        try: 
            result = genai.embed_content(
                model="models/embedding-001",  # Example embedding model
                content=text 
                # No task_type needed - works for both documents and queries
            )
            return result['embedding']
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg and attempt < 2:
                wait_time = (attempt + 1) * 10
                print(f"Rate limit exceeded, retrying... (attempt {attempt + 1})")
                await asyncio.sleep(wait_time)  # Exponential backoff
            else:
                print(f"Error getting embedding: {e}")
                return [0.0] * 768 # Return a zero vector on failure
        
    print("Failed to get embedding after retries")
    return [0.0] * 768 # Return a zero vector on failure