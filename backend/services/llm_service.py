import os
import google.generativeai as genai





def generate_answer(question: str, context: str) -> str:
    """Generate answer using Google Gemini with RAG optimization"""
    
    # More specific prompt for better RAG performance
    prompt = f"""You are a helpful AI assistant. Answer the question based ONLY on the provided context.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Answer using only the information from the context above
- If the context doesn't contain the answer, say "I don't have enough information to answer this question"
- Keep your response concise and relevant to the question
- Do not make up information or use external knowledge

ANSWER:"""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Handle empty responses gracefully
        if response.text:
            return response.text
        else:
            return "No response generated from the AI model."
            
    except Exception as e:
        # Log the error and return a user-friendly message
        print(f"Gemini API error: {e}")
        return f"Error generating response: {str(e)}"