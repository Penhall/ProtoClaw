import os
from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def build_llm() -> BaseChatModel:
    """Build LLM with fallback chain: Claude → OpenAI → Ollama."""
    providers: list[BaseChatModel] = []

    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(ChatAnthropic(model="claude-opus-4-6"))  # type: ignore[call-arg]

    if os.getenv("OPENAI_API_KEY"):
        providers.append(ChatOpenAI(model="gpt-4o"))

    # Ollama: always available as zero-cost local fallback
    providers.append(
        ChatOpenAI(
            base_url="http://localhost:11434/v1",
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            api_key="ollama",
        )
    )

    primary = providers[0]
    fallbacks = providers[1:]
    if not fallbacks:
        return primary
    return primary.with_fallbacks(fallbacks)
