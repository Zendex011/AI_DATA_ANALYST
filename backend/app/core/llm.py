from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GEMINI_API_KEY


def get_llm(temperature: float = 0.0, max_output_tokens: int = 1024):
    """
    Returns a configured Gemini chat model.
    temperature=0 for code generation (deterministic, fewer syntax errors).
    max_output_tokens caps response length — without this, a rambling
    explanation has no upper bound and quietly costs real money.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=GEMINI_API_KEY,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )