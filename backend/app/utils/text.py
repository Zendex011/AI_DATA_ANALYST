from typing import Any

def strip_code_fences(text: Any) -> str:
    """
    Handles Gemini responses that may be strings or lists and removes
    markdown code fences.
    """

    if isinstance(text, list):
        parts = []

        for item in text:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            else:
                parts.append(str(item))

        text = "\n".join(parts)

    text = str(text).strip()

    if text.startswith("```python"):
        text = text[9:]

    elif text.startswith("```sql"):
        text = text[6:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()