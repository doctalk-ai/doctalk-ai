import google.generativeai as genai
from backend.core.config import config
from backend.core.logging_config import setup_logging
import logging
logger = logging.getLogger(__name__)

genai.configure(api_key=config.GEN_AI_KEY)


def generate_answer(question: str, context: str):
    prompt = f"""
    Answer the question based ONLY on the context.

    CONTEXT:
    {context}

    QUESTION:
    {question}

    If you cannot answer, say "Not enough information."
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text or "No response."

if generate_answer =="No response.":
    logger.warning("Generated answer is empty, returning default message.")
else:
    logger.info("Answer generated successfully.")  