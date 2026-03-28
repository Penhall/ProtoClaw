def test_build_llm_returns_something_when_no_keys(monkeypatch):
    """Ollama fallback always present — build_llm never returns None."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from protoclaw.llm.provider import build_llm
    llm = build_llm()
    assert llm is not None


def test_build_llm_with_anthropic_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from protoclaw.llm.provider import build_llm
    llm = build_llm()
    assert llm is not None


def test_build_llm_with_both_keys_returns_chain(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    from protoclaw.llm.provider import build_llm
    llm = build_llm()
    assert llm is not None
