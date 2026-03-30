import re
from langchain_core.runnables import RunnableLambda


def _extract_json_text(message) -> str:
    """Strip any preamble before the first { or [ in LLM output."""
    text = message.content if hasattr(message, "content") else str(message)
    match = re.search(r"[{\[]", text)
    return text[match.start():] if match else text


#: Drop-in replacement for the LLM→JsonOutputParser step boundary.
#: Usage: _PROMPT | build_llm() | strip_to_json | JsonOutputParser()
strip_to_json = RunnableLambda(_extract_json_text)
