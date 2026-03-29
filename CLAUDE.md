# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Run unit tests only (fast, no Docker, no real LLM)
python -m pytest tests/unit/ -v

# Run a single test
python -m pytest tests/unit/test_select.py::test_select_nanobot_for_research_task -v

# Run integration tests (LLM nodes are mocked, no real API calls)
python -m pytest tests/integration/ -v

# Deploy an agent
protoclaw deploy "Pesquisar tendências de IA no Reddit nos últimos 30 dias"

# List running agents
protoclaw list

# View agent logs
protoclaw logs protoclaw-<agent-name>

# Stop an agent
protoclaw stop protoclaw-<agent-name>
```

## Architecture

ProtoClaw is a **LangGraph state machine** that receives a mission string and deploys a focused AI agent in Docker.

**Pipeline:** `parse → decompose → guardrails → select → generate_{framework} → deploy → report`

**State object** (`protoclaw/orchestrator/state.py`): `ProtoclawState` TypedDict flows through every node. Nodes return partial dicts merged into the state.

**LLM nodes** (`decompose.py`, `guardrails.py`): Call `_build_chain()` — a patchable helper returning `PROMPT | build_llm() | JsonOutputParser()`. Patch `_build_chain` to test without real LLM calls.

**Framework selection** (`select.py`): Fully deterministic keyword matching — no LLM involved. Channel keywords → `openclaw`; everything else → `nanobot`.

**Templates** (`protoclaw/templates/`): Jinja2 `.j2` files, one directory per framework. Rendered by `generate_openclaw.py` and `generate_nanobot.py`.

**Target frameworks:**
- `openclaw` → `github.com/openclaw/openclaw` (TypeScript, multi-channel, SOUL.md + AGENTS.md + workspace.json)
- `nanobot` → `github.com/yukihamada/nanobot` (Rust, single binary, .env + config.json)

## Environment

Copy `.env.example` to `.env`. Requires at least one of `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. Ollama is the zero-cost local fallback (requires `ollama` running at `localhost:11434`).

## Testing Strategy

- **Unit tests**: Each node tested in isolation. LLM nodes use `unittest.mock.patch` on `_build_chain`. Docker and Git operations are mocked.
- **Integration tests**: Canary mission *"Pesquisar tendências de IA no Reddit nos últimos 30 dias"* runs the full pipeline with LLM nodes mocked but all other logic real.
- LLM nodes use `_build_chain()` as the mock seam — never mock `build_llm` directly.
