from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GEMINI_API_KEY


def get_llm(temperature: float = 0.0, max_output_tokens: int = 1024, api_key: str | None = None):
    """
    Returns a configured Gemini chat model.
    temperature=0 for code generation (deterministic, fewer syntax errors).
    max_output_tokens caps response length -- without this, a rambling
    explanation has no upper bound and quietly costs real money.
    api_key: pass a user's own Gemini key to bill their account instead of
    the app owner's. Falls back to the shared GEMINI_API_KEY if not given
    or if the caller passes None (e.g. user hasn't set their own key).
    """
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=api_key or GEMINI_API_KEY,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
