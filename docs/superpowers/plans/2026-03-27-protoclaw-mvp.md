# ProtoClaw MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI that receives a mission string, decomposes it via LLM, selects between OpenClaw and NanoBot, generates config files from Jinja2 templates, clones the target repo, and deploys an isolated Docker container.

**Architecture:** LangGraph state machine with 8 nodes (parse → decompose → guardrails → select → generate → deploy → report). Each node is a pure function operating on `ProtoclawState`. LLM calls use a LangChain fallback chain (Claude → OpenAI → Ollama) with no LiteLLM dependency.

**Tech Stack:** Python 3.12+, LangGraph, LangChain (anthropic + openai), Jinja2, GitPython, Docker SDK, Click, Rich, pytest

---

## File Map

```
protoclaw/
├── protoclaw/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                       # Click CLI entry point
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── graph.py                      # LangGraph graph assembly
│   │   ├── state.py                      # ProtoclawState TypedDict + Subtask
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── parse.py                  # validate + clean mission input
│   │       ├── decompose.py              # LLM: mission → 4-8 subtasks
│   │       ├── guardrails.py             # LLM: generate focus rules
│   │       ├── select.py                 # deterministic: openclaw or nanobot
│   │       ├── generate_openclaw.py      # Jinja2: SOUL.md + AGENTS.md + workspace.json
│   │       ├── generate_nanobot.py       # Jinja2: .env + config.json
│   │       ├── deploy.py                 # wire workspace + docker together
│   │       └── report.py                 # format CLI success message
│   ├── llm/
│   │   ├── __init__.py
│   │   └── provider.py                   # build_llm() with fallback chain
│   ├── templates/
│   │   ├── openclaw/
│   │   │   ├── SOUL.md.j2
│   │   │   ├── AGENTS.md.j2
│   │   │   └── workspace.json.j2
│   │   └── nanobot/
│   │       ├── .env.j2
│   │       └── config.json.j2
│   ├── deployer/
│   │   ├── __init__.py
│   │   └── docker.py                     # Docker SDK: run/stop/logs/list
│   └── workspace/
│       ├── __init__.py
│       └── manager.py                    # GitPython: clone + inject files
├── tests/
│   ├── conftest.py                       # shared fixtures
│   ├── unit/
│   │   ├── test_state.py
│   │   ├── test_provider.py
│   │   ├── test_parse.py
│   │   ├── test_select.py
│   │   ├── test_decompose.py
│   │   ├── test_guardrails.py
│   │   ├── test_templates.py
│   │   ├── test_generate_openclaw.py
│   │   ├── test_generate_nanobot.py
│   │   └── test_docker.py
│   └── integration/
│       └── test_canary.py
├── workspaces/                           # runtime only, gitignored
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `protoclaw/__init__.py` (and all `__init__.py` files)
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "protoclaw"
version = "0.1.0"
description = "Intelligent agent factory — deploy focused AI agents from a mission string"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "langchain-openai>=0.2.0",
    "jinja2>=3.1.4",
    "gitpython>=3.1.0",
    "docker>=7.0.0",
    "click>=8.1.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
]

[project.scripts]
protoclaw = "protoclaw.cli.main:cli"

[tool.hatch.build.targets.wheel]
packages = ["protoclaw"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create directory structure and empty `__init__.py` files**

```bash
mkdir -p protoclaw/cli protoclaw/orchestrator/nodes protoclaw/llm \
         protoclaw/templates/openclaw protoclaw/templates/nanobot \
         protoclaw/deployer protoclaw/workspace \
         tests/unit tests/integration workspaces

touch protoclaw/__init__.py \
      protoclaw/cli/__init__.py \
      protoclaw/orchestrator/__init__.py \
      protoclaw/orchestrator/nodes/__init__.py \
      protoclaw/llm/__init__.py \
      protoclaw/deployer/__init__.py \
      protoclaw/workspace/__init__.py \
      tests/__init__.py \
      tests/unit/__init__.py \
      tests/integration/__init__.py
```

- [ ] **Step 3: Create `.env.example`**

```bash
# .env.example
# At least one LLM provider is required.
# Ollama (free, local) is always the last fallback if running locally.

ANTHROPIC_API_KEY=        # primary: claude-opus-4-6
OPENAI_API_KEY=           # fallback: gpt-4o
OLLAMA_MODEL=llama3       # last resort (ollama must be running)

# Docker network name for deployed agents
PROTOCLAW_NETWORK=protoclaw-net
```

- [ ] **Step 4: Add `workspaces/` to `.gitignore`**

Append to existing `.gitignore`:
```
workspaces/
*.egg-info/
__pycache__/
.pytest_cache/
dist/
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -e ".[dev]"
```

Expected: no errors, `protoclaw` command available.

- [ ] **Step 6: Verify install**

```bash
protoclaw --help
```

Expected output:
```
Usage: protoclaw [OPTIONS] COMMAND [ARGS]...

  ProtoClaw — Intelligent Agent Factory
...
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .env.example .gitignore protoclaw/ tests/ workspaces/.gitkeep
git commit -m "chore: scaffold Python project structure"
```

---

## Task 2: State TypedDict

**Files:**
- Create: `protoclaw/orchestrator/state.py`
- Create: `tests/unit/test_state.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_state.py
from protoclaw.orchestrator.state import ProtoclawState, Subtask

def test_protoclaw_state_accepts_valid_data():
    state: ProtoclawState = {
        "mission": "Pesquisar IA no Reddit",
        "subtasks": [],
        "guardrails": [],
        "framework": None,
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
    }
    assert state["mission"] == "Pesquisar IA no Reddit"

def test_subtask_fields():
    task: Subtask = {
        "description": "Coletar posts",
        "type": "sequential",
        "completion_criteria": "100 posts coletados",
    }
    assert task["type"] == "sequential"
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
pytest tests/unit/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'protoclaw.orchestrator.state'`

- [ ] **Step 3: Create `protoclaw/orchestrator/state.py`**

```python
from typing import TypedDict, Literal

class Subtask(TypedDict):
    description: str
    type: Literal["sequential", "parallel"]
    completion_criteria: str

class ProtoclawState(TypedDict):
    mission: str
    subtasks: list[Subtask]
    guardrails: list[str]
    framework: Literal["openclaw", "nanobot"] | None
    generated_files: dict[str, str]   # filename -> rendered content
    workspace_dir: str
    container_id: str
    error: str | None
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/unit/test_state.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/orchestrator/state.py tests/unit/test_state.py
git commit -m "feat: add ProtoclawState TypedDict"
```

---

## Task 3: LLM Provider

**Files:**
- Create: `protoclaw/llm/provider.py`
- Create: `tests/unit/test_provider.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_provider.py
import pytest

def test_build_llm_returns_something_when_no_keys(monkeypatch):
    """Ollama fallback always available — build_llm never returns None."""
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
    # With 2+ providers, returns a fallback chain (has .with_fallbacks attr used)
    assert llm is not None
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_provider.py -v
```

- [ ] **Step 3: Create `protoclaw/llm/provider.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_provider.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/llm/provider.py tests/unit/test_provider.py
git commit -m "feat: add LLM provider with Claude→OpenAI→Ollama fallback chain"
```

---

## Task 4: Parse Node

**Files:**
- Create: `protoclaw/orchestrator/nodes/parse.py`
- Create: `tests/unit/test_parse.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_parse.py
import pytest
from protoclaw.orchestrator.state import ProtoclawState

def _state(mission: str) -> ProtoclawState:
    return {
        "mission": mission, "subtasks": [], "guardrails": [],
        "framework": None, "generated_files": {}, "workspace_dir": "",
        "container_id": "", "error": None,
    }

def test_parse_empty_mission_returns_error():
    from protoclaw.orchestrator.nodes.parse import parse_node
    result = parse_node(_state("   "))
    assert result["error"] is not None
    assert "empty" in result["error"].lower()

def test_parse_valid_mission_strips_whitespace():
    from protoclaw.orchestrator.nodes.parse import parse_node
    result = parse_node(_state("  Pesquisar IA no Reddit  "))
    assert result["error"] is None
    assert result["mission"] == "Pesquisar IA no Reddit"

def test_parse_preserves_other_state_fields():
    from protoclaw.orchestrator.nodes.parse import parse_node
    state = _state("Missão válida")
    result = parse_node(state)
    assert result["subtasks"] == []
    assert result["framework"] is None
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_parse.py -v
```

- [ ] **Step 3: Create `protoclaw/orchestrator/nodes/parse.py`**

```python
from protoclaw.orchestrator.state import ProtoclawState

def parse_node(state: ProtoclawState) -> ProtoclawState:
    """Validate and clean the raw mission string."""
    mission = state["mission"].strip()

    if not mission:
        return {**state, "error": "Mission cannot be empty"}

    return {**state, "mission": mission, "error": None}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_parse.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/orchestrator/nodes/parse.py tests/unit/test_parse.py
git commit -m "feat: add parse node with input validation"
```

---

## Task 5: Select Node

**Files:**
- Create: `protoclaw/orchestrator/nodes/select.py`
- Create: `tests/unit/test_select.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_select.py
from protoclaw.orchestrator.state import ProtoclawState

def _state(mission: str) -> ProtoclawState:
    return {
        "mission": mission, "subtasks": [], "guardrails": [],
        "framework": None, "generated_files": {}, "workspace_dir": "",
        "container_id": "", "error": None,
    }

def test_select_nanobot_for_research_task():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Pesquisar tendências de IA no Reddit nos últimos 30 dias"))
    assert result["framework"] == "nanobot"

def test_select_openclaw_for_telegram():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Criar assistente no Telegram que responde dúvidas"))
    assert result["framework"] == "openclaw"

def test_select_openclaw_for_discord():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Monitorar canal Discord e resumir mensagens"))
    assert result["framework"] == "openclaw"

def test_select_openclaw_for_whatsapp():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Responder clientes no WhatsApp automaticamente"))
    assert result["framework"] == "openclaw"

def test_select_openclaw_for_persistent_assistant():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Assistente pessoal que sempre responde e-mails"))
    assert result["framework"] == "openclaw"

def test_select_nanobot_for_scraping():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Fazer scraping de preços de produtos na Amazon"))
    assert result["framework"] == "nanobot"

def test_select_nanobot_for_simple_monitoring():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Verificar disponibilidade de um site a cada hora"))
    assert result["framework"] == "nanobot"
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_select.py -v
```

- [ ] **Step 3: Create `protoclaw/orchestrator/nodes/select.py`**

```python
from protoclaw.orchestrator.state import ProtoclawState

_CHANNEL_KEYWORDS = {
    "telegram", "whatsapp", "discord", "slack", "instagram",
    "twitter", "signal", "imessage", "teams", "matrix", "line",
    "youtube", "facebook", "messenger",
}

_PERSISTENCE_KEYWORDS = {
    "assistente", "assistant", "daemon", "monitor", "sempre",
    "always", "continuously", "continuamente", "permanente",
    "permanent", "24h", "24/7",
}

def select_node(state: ProtoclawState) -> dict:
    """Deterministically choose openclaw or nanobot based on mission text."""
    words = set(state["mission"].lower().split())

    has_channel = bool(words & _CHANNEL_KEYWORDS)
    is_persistent = bool(words & _PERSISTENCE_KEYWORDS)

    framework = "openclaw" if (has_channel or is_persistent) else "nanobot"
    return {"framework": framework}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_select.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/orchestrator/nodes/select.py tests/unit/test_select.py
git commit -m "feat: add deterministic framework selector (openclaw vs nanobot)"
```

---

## Task 6: Decompose Node

**Files:**
- Create: `protoclaw/orchestrator/nodes/decompose.py`
- Create: `tests/unit/test_decompose.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_decompose.py
from unittest.mock import MagicMock, patch
from protoclaw.orchestrator.state import ProtoclawState

def _state(mission: str = "Pesquisar IA no Reddit") -> ProtoclawState:
    return {
        "mission": mission, "subtasks": [], "guardrails": [],
        "framework": None, "generated_files": {}, "workspace_dir": "",
        "container_id": "", "error": None,
    }

_MOCK_RESULT = {
    "subtasks": [
        {"description": "Coletar posts do Reddit sobre IA", "type": "sequential", "completion_criteria": "100 posts coletados"},
        {"description": "Filtrar posts dos últimos 30 dias", "type": "sequential", "completion_criteria": "Posts filtrados por data"},
        {"description": "Identificar top 5 tendências", "type": "sequential", "completion_criteria": "Tendências listadas"},
    ]
}

def test_decompose_returns_subtasks_list():
    from protoclaw.orchestrator.nodes.decompose import decompose_node, _build_chain
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = _MOCK_RESULT

    with patch("protoclaw.orchestrator.nodes.decompose._build_chain", return_value=mock_chain):
        result = decompose_node(_state())

    assert len(result["subtasks"]) == 3
    assert result["subtasks"][0]["description"] == "Coletar posts do Reddit sobre IA"

def test_decompose_subtask_has_required_fields():
    from protoclaw.orchestrator.nodes.decompose import decompose_node, _build_chain
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = _MOCK_RESULT

    with patch("protoclaw.orchestrator.nodes.decompose._build_chain", return_value=mock_chain):
        result = decompose_node(_state())

    for task in result["subtasks"]:
        assert "description" in task
        assert "type" in task
        assert "completion_criteria" in task
        assert task["type"] in ("sequential", "parallel")
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_decompose.py -v
```

- [ ] **Step 3: Create `protoclaw/orchestrator/nodes/decompose.py`**

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from protoclaw.llm.provider import build_llm
from protoclaw.orchestrator.state import ProtoclawState

_PROMPT = ChatPromptTemplate.from_template(
    "Você é um especialista em decomposição de tarefas para agentes de IA.\n\n"
    "Missão: {mission}\n\n"
    "Decomponha em 4-8 subtarefas claras. Cada subtarefa deve ser atômica e verificável.\n\n"
    "Responda APENAS com JSON válido:\n"
    '{{"subtasks": [{{"description": "...", "type": "sequential|parallel", "completion_criteria": "..."}}]}}'
)

def _build_chain():
    return _PROMPT | build_llm() | JsonOutputParser()

def decompose_node(state: ProtoclawState) -> dict:
    chain = _build_chain()
    result = chain.invoke({"mission": state["mission"]})
    return {"subtasks": result["subtasks"]}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_decompose.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/orchestrator/nodes/decompose.py tests/unit/test_decompose.py
git commit -m "feat: add decompose node (LLM mission → subtasks)"
```

---

## Task 7: Guardrails Node

**Files:**
- Create: `protoclaw/orchestrator/nodes/guardrails.py`
- Create: `tests/unit/test_guardrails.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_guardrails.py
from unittest.mock import MagicMock, patch
from protoclaw.orchestrator.state import ProtoclawState

def _state() -> ProtoclawState:
    return {
        "mission": "Pesquisar IA no Reddit",
        "subtasks": [
            {"description": "Coletar posts", "type": "sequential", "completion_criteria": "Done"}
        ],
        "guardrails": [], "framework": None, "generated_files": {},
        "workspace_dir": "", "container_id": "", "error": None,
    }

_MOCK_RESULT = {
    "guardrails": [
        "Nunca acesse sites fora do Reddit",
        "Não execute código externo",
        "Não envie mensagens a usuários",
        "Limite pesquisa aos últimos 30 dias",
        "Não armazene dados pessoais de usuários",
    ]
}

def test_guardrails_returns_list():
    from protoclaw.orchestrator.nodes.guardrails import guardrails_node, _build_chain
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = _MOCK_RESULT

    with patch("protoclaw.orchestrator.nodes.guardrails._build_chain", return_value=mock_chain):
        result = guardrails_node(_state())

    assert isinstance(result["guardrails"], list)
    assert len(result["guardrails"]) == 5

def test_guardrails_minimum_count():
    from protoclaw.orchestrator.nodes.guardrails import guardrails_node, _build_chain
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = _MOCK_RESULT

    with patch("protoclaw.orchestrator.nodes.guardrails._build_chain", return_value=mock_chain):
        result = guardrails_node(_state())

    assert len(result["guardrails"]) >= 3
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_guardrails.py -v
```

- [ ] **Step 3: Create `protoclaw/orchestrator/nodes/guardrails.py`**

```python
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from protoclaw.llm.provider import build_llm
from protoclaw.orchestrator.state import ProtoclawState

_PROMPT = ChatPromptTemplate.from_template(
    "Você é especialista em segurança e foco de agentes de IA.\n\n"
    "Missão: {mission}\n"
    "Subtarefas: {subtasks}\n\n"
    "Gere 5-8 guardrails (regras de foco) rígidas e específicas.\n"
    "Cada guardrail deve ser uma proibição clara que evita desvio de escopo.\n\n"
    "Responda APENAS com JSON válido:\n"
    '{{"guardrails": ["Regra proibitiva clara"]}}'
)

def _build_chain():
    return _PROMPT | build_llm() | JsonOutputParser()

def guardrails_node(state: ProtoclawState) -> dict:
    chain = _build_chain()
    result = chain.invoke({
        "mission": state["mission"],
        "subtasks": json.dumps(state["subtasks"], ensure_ascii=False),
    })
    return {"guardrails": result["guardrails"]}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_guardrails.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/orchestrator/nodes/guardrails.py tests/unit/test_guardrails.py
git commit -m "feat: add guardrails node (LLM → strict focus rules)"
```

---

## Task 8: Jinja2 Templates (Phase 0 Blueprints)

**Files:**
- Create: `protoclaw/templates/openclaw/SOUL.md.j2`
- Create: `protoclaw/templates/openclaw/AGENTS.md.j2`
- Create: `protoclaw/templates/openclaw/workspace.json.j2`
- Create: `protoclaw/templates/nanobot/.env.j2`
- Create: `protoclaw/templates/nanobot/config.json.j2`
- Create: `tests/unit/test_templates.py`

- [ ] **Step 1: Write failing template tests**

```python
# tests/unit/test_templates.py
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Path("protoclaw/templates")

_CONTEXT_OC = {
    "agent_name": "reddit-ia-trends",
    "mission_summary": "Pesquisar tendências de IA no Reddit nos últimos 30 dias",
    "primary_objective": "Pesquisar tendências de IA no Reddit nos últimos 30 dias",
    "guardrails": ["Nunca acesse sites fora do Reddit", "Não execute código externo"],
    "subtasks": [
        {"type": "sequential", "description": "Coletar posts", "completion_criteria": "100 posts coletados"},
        {"type": "sequential", "description": "Filtrar por data", "completion_criteria": "Posts filtrados"},
    ],
    "model": "claude-opus-4-6",
    "channels": [],
    "skills": [],
}

_CONTEXT_NB = {
    "agent_name": "reddit-ia-trends",
    "primary_objective": "Pesquisar tendências de IA no Reddit nos últimos 30 dias",
    "guardrails": ["Nunca acesse sites fora do Reddit"],
    "subtasks": [
        {"description": "Coletar posts", "type": "sequential", "completion_criteria": "Done"},
    ],
    "model": "claude-opus-4-6",
    "anthropic_api_key": "sk-ant-fake",
    "openai_api_key": "",
}

def test_soul_md_contains_agent_name():
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "openclaw")))
    result = env.get_template("SOUL.md.j2").render(**_CONTEXT_OC)
    assert "reddit-ia-trends" in result

def test_soul_md_contains_all_guardrails():
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "openclaw")))
    result = env.get_template("SOUL.md.j2").render(**_CONTEXT_OC)
    assert "Nunca acesse sites fora do Reddit" in result
    assert "Não execute código externo" in result

def test_agents_md_contains_subtasks():
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "openclaw")))
    result = env.get_template("AGENTS.md.j2").render(**_CONTEXT_OC)
    assert "Coletar posts" in result
    assert "Filtrar por data" in result

def test_workspace_json_is_valid_json():
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "openclaw")))
    result = env.get_template("workspace.json.j2").render(**_CONTEXT_OC)
    parsed = json.loads(result)
    assert parsed["name"] == "reddit-ia-trends"

def test_nanobot_config_json_is_valid():
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "nanobot")))
    result = env.get_template("config.json.j2").render(**_CONTEXT_NB)
    parsed = json.loads(result)
    assert parsed["agent_name"] == "reddit-ia-trends"
    assert len(parsed["guardrails"]) == 1

def test_nanobot_env_contains_api_key():
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES / "nanobot")))
    result = env.get_template(".env.j2").render(**_CONTEXT_NB)
    assert "ANTHROPIC_API_KEY=sk-ant-fake" in result
```

- [ ] **Step 2: Run tests — expect FileNotFoundError / TemplateNotFound**

```bash
pytest tests/unit/test_templates.py -v
```

- [ ] **Step 3: Create `protoclaw/templates/openclaw/SOUL.md.j2`**

```jinja2
# SOUL.md — {{ agent_name }}

## Missão Principal
{{ mission_summary }}

## Foco Absoluto
Você existe EXCLUSIVAMENTE para: {{ primary_objective }}

## Guardrails (inegociáveis)
{% for rule in guardrails %}
- {{ rule }}
{% endfor %}

## Subtarefas
{% for task in subtasks %}
{{ loop.index }}. [{{ task.type | upper }}] {{ task.description }}
   Critério de conclusão: {{ task.completion_criteria }}
{% endfor %}

## Política de Desvio
Qualquer solicitação fora do escopo acima deve ser recusada com:
"Estou configurado apenas para: {{ primary_objective }}"

---
_Gerado automaticamente pelo ProtoClaw._
```

- [ ] **Step 4: Create `protoclaw/templates/openclaw/AGENTS.md.j2`**

```jinja2
# AGENTS.md — Manual Operacional: {{ agent_name }}

## Identidade
- **Nome:** {{ agent_name }}
- **Objetivo:** {{ primary_objective }}

## Fluxo de Trabalho
{% for task in subtasks %}
### Etapa {{ loop.index }}: {{ task.description }}
- Tipo: {{ task.type }}
- Critério de conclusão: {{ task.completion_criteria }}
{% endfor %}

## Regras de Foco (NÃO NEGOCIÁVEIS)
{% for rule in guardrails %}
{{ loop.index }}. {{ rule }}
{% endfor %}

## Escopo Permitido
Apenas ações diretamente relacionadas a: **{{ primary_objective }}**

## Escopo Proibido
Qualquer ação não relacionada à missão acima. Responda sempre:
"Estou configurado apenas para: {{ primary_objective }}"

---
_Gerado automaticamente pelo ProtoClaw._
```

- [ ] **Step 5: Create `protoclaw/templates/openclaw/workspace.json.j2`**

```jinja2
{
  "name": "{{ agent_name }}",
  "model": "{{ model | default('claude-opus-4-6') }}",
  "channels": {{ channels | tojson(indent=2) }},
  "skills": {{ skills | tojson(indent=2) }},
  "focus": "{{ primary_objective }}"
}
```

- [ ] **Step 6: Create `protoclaw/templates/nanobot/config.json.j2`**

```jinja2
{
  "agent_name": "{{ agent_name }}",
  "objective": "{{ primary_objective }}",
  "model": "{{ model | default('claude-opus-4-6') }}",
  "guardrails": {{ guardrails | tojson(indent=2) }},
  "subtasks": {{ subtasks | tojson(indent=2) }}
}
```

- [ ] **Step 7: Create `protoclaw/templates/nanobot/.env.j2`**

```jinja2
AGENT_NAME={{ agent_name }}
{% if anthropic_api_key %}ANTHROPIC_API_KEY={{ anthropic_api_key }}
{% endif %}{% if openai_api_key %}OPENAI_API_KEY={{ openai_api_key }}
{% endif %}OLLAMA_MODEL=llama3
```

- [ ] **Step 8: Run tests — expect PASS**

```bash
pytest tests/unit/test_templates.py -v
```

Expected: 6 passed.

- [ ] **Step 9: Commit**

```bash
git add protoclaw/templates/ tests/unit/test_templates.py
git commit -m "feat: add Jinja2 templates for OpenClaw and NanoBot (Phase 0 blueprints)"
```

---

## Task 9: Generate Nodes

**Files:**
- Create: `protoclaw/orchestrator/nodes/generate_openclaw.py`
- Create: `protoclaw/orchestrator/nodes/generate_nanobot.py`
- Create: `tests/unit/test_generate_openclaw.py`
- Create: `tests/unit/test_generate_nanobot.py`

- [ ] **Step 1: Write failing tests for OpenClaw generator**

```python
# tests/unit/test_generate_openclaw.py
from protoclaw.orchestrator.state import ProtoclawState

def _state() -> ProtoclawState:
    return {
        "mission": "Pesquisar tendências de IA no Reddit nos últimos 30 dias",
        "subtasks": [
            {"description": "Coletar posts", "type": "sequential", "completion_criteria": "Done"},
        ],
        "guardrails": ["Nunca acesse sites fora do Reddit"],
        "framework": "openclaw",
        "generated_files": {}, "workspace_dir": "", "container_id": "", "error": None,
    }

def test_generate_openclaw_produces_three_files():
    from protoclaw.orchestrator.nodes.generate_openclaw import generate_openclaw_node
    result = generate_openclaw_node(_state())
    files = result["generated_files"]
    assert "SOUL.md" in files
    assert "AGENTS.md" in files
    assert "workspace.json" in files

def test_generate_openclaw_soul_contains_guardrail():
    from protoclaw.orchestrator.nodes.generate_openclaw import generate_openclaw_node
    result = generate_openclaw_node(_state())
    assert "Nunca acesse sites fora do Reddit" in result["generated_files"]["SOUL.md"]

def test_generate_openclaw_workspace_is_valid_json():
    import json
    from protoclaw.orchestrator.nodes.generate_openclaw import generate_openclaw_node
    result = generate_openclaw_node(_state())
    parsed = json.loads(result["generated_files"]["workspace.json"])
    assert "name" in parsed
```

- [ ] **Step 2: Write failing tests for NanoBot generator**

```python
# tests/unit/test_generate_nanobot.py
import json
from protoclaw.orchestrator.state import ProtoclawState

def _state() -> ProtoclawState:
    return {
        "mission": "Pesquisar tendências de IA no Reddit nos últimos 30 dias",
        "subtasks": [
            {"description": "Coletar posts", "type": "sequential", "completion_criteria": "Done"},
        ],
        "guardrails": ["Nunca acesse sites fora do Reddit"],
        "framework": "nanobot",
        "generated_files": {}, "workspace_dir": "", "container_id": "", "error": None,
    }

def test_generate_nanobot_produces_two_files():
    from protoclaw.orchestrator.nodes.generate_nanobot import generate_nanobot_node
    result = generate_nanobot_node(_state())
    files = result["generated_files"]
    assert ".env" in files
    assert "config.json" in files

def test_generate_nanobot_config_is_valid_json():
    from protoclaw.orchestrator.nodes.generate_nanobot import generate_nanobot_node
    result = generate_nanobot_node(_state())
    parsed = json.loads(result["generated_files"]["config.json"])
    assert parsed["agent_name"] is not None
    assert isinstance(parsed["guardrails"], list)
```

- [ ] **Step 3: Run tests — expect ImportError**

```bash
pytest tests/unit/test_generate_openclaw.py tests/unit/test_generate_nanobot.py -v
```

- [ ] **Step 4: Create `protoclaw/orchestrator/nodes/generate_openclaw.py`**

```python
import os
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from protoclaw.orchestrator.state import ProtoclawState

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "openclaw"

def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")[:40]

def generate_openclaw_node(state: ProtoclawState) -> dict:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
    agent_name = _slug(state["mission"])

    context = {
        "agent_name": agent_name,
        "mission_summary": state["mission"],
        "primary_objective": state["mission"],
        "guardrails": state["guardrails"],
        "subtasks": state["subtasks"],
        "model": os.getenv("PROTOCLAW_MODEL", "claude-opus-4-6"),
        "channels": [],
        "skills": [],
    }

    files: dict[str, str] = {}
    for tpl_name, out_name in [
        ("SOUL.md.j2", "SOUL.md"),
        ("AGENTS.md.j2", "AGENTS.md"),
        ("workspace.json.j2", "workspace.json"),
    ]:
        files[out_name] = env.get_template(tpl_name).render(**context)

    return {"generated_files": files}
```

- [ ] **Step 5: Create `protoclaw/orchestrator/nodes/generate_nanobot.py`**

```python
import os
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from protoclaw.orchestrator.state import ProtoclawState

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "nanobot"

def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")[:40]

def generate_nanobot_node(state: ProtoclawState) -> dict:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
    agent_name = _slug(state["mission"])

    context = {
        "agent_name": agent_name,
        "primary_objective": state["mission"],
        "guardrails": state["guardrails"],
        "subtasks": state["subtasks"],
        "model": os.getenv("PROTOCLAW_MODEL", "claude-opus-4-6"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    }

    files: dict[str, str] = {}
    for tpl_name, out_name in [
        (".env.j2", ".env"),
        ("config.json.j2", "config.json"),
    ]:
        files[out_name] = env.get_template(tpl_name).render(**context)

    return {"generated_files": files}
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest tests/unit/test_generate_openclaw.py tests/unit/test_generate_nanobot.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add protoclaw/orchestrator/nodes/generate_openclaw.py \
        protoclaw/orchestrator/nodes/generate_nanobot.py \
        tests/unit/test_generate_openclaw.py \
        tests/unit/test_generate_nanobot.py
git commit -m "feat: add OpenClaw and NanoBot config generators"
```

---

## Task 10: Workspace Manager

**Files:**
- Create: `protoclaw/workspace/manager.py`
- Create: `tests/unit/test_workspace.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_workspace.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

def test_setup_workspace_creates_directory(tmp_path, monkeypatch):
    from protoclaw.workspace import manager
    monkeypatch.setattr(manager, "WORKSPACES_ROOT", tmp_path)

    mock_repo = MagicMock()
    with patch("protoclaw.workspace.manager.git.Repo.clone_from", return_value=mock_repo):
        result = manager.setup_workspace(
            framework="nanobot",
            agent_name="test-agent",
            generated_files={"config.json": '{"name": "test"}', ".env": "KEY=val"},
        )

    workspace_dir = Path(result)
    assert workspace_dir.parent == tmp_path

def test_setup_workspace_writes_generated_files(tmp_path, monkeypatch):
    from protoclaw.workspace import manager
    monkeypatch.setattr(manager, "WORKSPACES_ROOT", tmp_path)

    with patch("protoclaw.workspace.manager.git.Repo.clone_from"):
        result = manager.setup_workspace(
            framework="nanobot",
            agent_name="test-agent",
            generated_files={"config.json": '{"name": "test"}'},
        )

    config_file = Path(result) / "config.json"
    assert config_file.exists()
    assert '{"name": "test"}' in config_file.read_text()

def test_setup_workspace_clones_correct_repo(tmp_path, monkeypatch):
    from protoclaw.workspace import manager
    monkeypatch.setattr(manager, "WORKSPACES_ROOT", tmp_path)

    with patch("protoclaw.workspace.manager.git.Repo.clone_from") as mock_clone:
        manager.setup_workspace(
            framework="openclaw",
            agent_name="test-agent",
            generated_files={},
        )

    called_url = mock_clone.call_args[0][0]
    assert "openclaw/openclaw" in called_url
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_workspace.py -v
```

- [ ] **Step 3: Create `protoclaw/workspace/manager.py`**

```python
import re
from datetime import datetime
from pathlib import Path
import git

WORKSPACES_ROOT = Path(__file__).parent.parent.parent / "workspaces"

_REPOS = {
    "openclaw": "https://github.com/openclaw/openclaw.git",
    "nanobot": "https://github.com/yukihamada/nanobot.git",
}

def setup_workspace(
    framework: str,
    agent_name: str,
    generated_files: dict[str, str],
) -> str:
    """Clone target repo and inject generated config files. Returns workspace path."""
    date_str = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r"[^\w-]", "-", agent_name)[:40]
    workspace_dir = WORKSPACES_ROOT / f"{slug}-{date_str}"

    WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from(_REPOS[framework], workspace_dir, depth=1)

    for filename, content in generated_files.items():
        target = workspace_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return str(workspace_dir)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_workspace.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/workspace/manager.py tests/unit/test_workspace.py
git commit -m "feat: add workspace manager (clone + inject config files)"
```

---

## Task 11: Docker Deployer

**Files:**
- Create: `protoclaw/deployer/docker.py`
- Create: `tests/unit/test_docker.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_docker.py
from unittest.mock import MagicMock, patch

_IMAGES = {"openclaw": "ghcr.io/openclaw/openclaw:latest", "nanobot": "yukihamada/nanobot:latest"}

def test_deploy_agent_returns_container_id():
    from protoclaw.deployer.docker import deploy_agent
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        result = deploy_agent("nanobot", "/tmp/workspace", "test-agent")

    assert result == "abc123"

def test_deploy_agent_uses_correct_image_for_openclaw():
    from protoclaw.deployer.docker import deploy_agent
    mock_container = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        deploy_agent("openclaw", "/tmp/workspace", "test-agent")

    call_kwargs = mock_client.containers.run.call_args
    assert call_kwargs[0][0] == _IMAGES["openclaw"]

def test_list_agents_filters_by_protoclaw_prefix():
    from protoclaw.deployer.docker import list_agents
    mock_c1 = MagicMock(name="protoclaw-test", status="running", short_id="abc")
    mock_c1.name = "protoclaw-test"
    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_c1]

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        result = list_agents()

    assert len(result) == 1
    assert result[0]["name"] == "protoclaw-test"

def test_stop_agent_calls_stop_and_remove():
    from protoclaw.deployer.docker import stop_agent
    mock_container = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        stop_agent("protoclaw-test")

    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/unit/test_docker.py -v
```

- [ ] **Step 3: Create `protoclaw/deployer/docker.py`**

```python
import re
import docker

_IMAGES = {
    "openclaw": "ghcr.io/openclaw/openclaw:latest",
    "nanobot": "yukihamada/nanobot:latest",
}

def _ensure_network(client: docker.DockerClient, network_name: str) -> None:
    existing = [n.name for n in client.networks.list()]
    if network_name not in existing:
        client.networks.create(network_name, driver="bridge")

def deploy_agent(framework: str, workspace_dir: str, agent_name: str) -> str:
    """Deploy agent container. Returns container ID."""
    client = docker.from_env()
    slug = re.sub(r"[^\w-]", "-", agent_name)[:40]
    container_name = f"protoclaw-{slug}"
    network_name = "protoclaw-net"

    _ensure_network(client, network_name)

    container = client.containers.run(
        image=_IMAGES[framework],
        name=container_name,
        volumes={workspace_dir: {"bind": "/workspace", "mode": "ro"}},
        network=network_name,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
    )
    return container.id

def get_logs(container_name: str) -> str:
    client = docker.from_env()
    container = client.containers.get(container_name)
    return container.logs(tail=100).decode("utf-8", errors="replace")

def stop_agent(container_name: str) -> None:
    client = docker.from_env()
    container = client.containers.get(container_name)
    container.stop()
    container.remove()

def list_agents() -> list[dict]:
    client = docker.from_env()
    containers = client.containers.list(filters={"name": "protoclaw-"})
    return [{"name": c.name, "status": c.status, "id": c.short_id} for c in containers]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/unit/test_docker.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add protoclaw/deployer/docker.py tests/unit/test_docker.py
git commit -m "feat: add Docker deployer (run/stop/logs/list)"
```

---

## Task 12: Deploy + Report Nodes

**Files:**
- Create: `protoclaw/orchestrator/nodes/deploy.py`
- Create: `protoclaw/orchestrator/nodes/report.py`

- [ ] **Step 1: Create `protoclaw/orchestrator/nodes/deploy.py`**

```python
import re
from protoclaw.orchestrator.state import ProtoclawState
from protoclaw.workspace.manager import setup_workspace
from protoclaw.deployer.docker import deploy_agent

def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")[:40]

def deploy_node(state: ProtoclawState) -> dict:
    """Wire workspace setup and Docker deploy together."""
    agent_name = _slug(state["mission"])
    framework = state["framework"]

    workspace_dir = setup_workspace(
        framework=framework,
        agent_name=agent_name,
        generated_files=state["generated_files"],
    )

    container_id = deploy_agent(
        framework=framework,
        workspace_dir=workspace_dir,
        agent_name=agent_name,
    )

    return {"workspace_dir": workspace_dir, "container_id": container_id}
```

- [ ] **Step 2: Create `protoclaw/orchestrator/nodes/report.py`**

```python
import re
from protoclaw.orchestrator.state import ProtoclawState

def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")[:40]

def report_node(state: ProtoclawState) -> dict:
    """Build the success message shown to the user."""
    agent_name = _slug(state["mission"])
    container_name = f"protoclaw-{agent_name}"

    report = (
        f"\n[✓] Agent deployed successfully!\n"
        f"  Framework : {state['framework']}\n"
        f"  Directory : {state['workspace_dir']}\n"
        f"  Container : {container_name}\n"
        f"  Status    : running\n"
        f"  Logs      : protoclaw logs {container_name}\n"
    )

    return {"report": report}
```

- [ ] **Step 3: Run the full unit suite to verify no regressions**

```bash
pytest tests/unit/ -v
```

Expected: all previous tests still pass.

- [ ] **Step 4: Commit**

```bash
git add protoclaw/orchestrator/nodes/deploy.py protoclaw/orchestrator/nodes/report.py
git commit -m "feat: add deploy and report nodes"
```

---

## Task 13: LangGraph Graph Assembly

**Files:**
- Create: `protoclaw/orchestrator/graph.py`

- [ ] **Step 1: Create `protoclaw/orchestrator/graph.py`**

```python
from langgraph.graph import StateGraph, END
from protoclaw.orchestrator.state import ProtoclawState
from protoclaw.orchestrator.nodes.parse import parse_node
from protoclaw.orchestrator.nodes.decompose import decompose_node
from protoclaw.orchestrator.nodes.guardrails import guardrails_node
from protoclaw.orchestrator.nodes.select import select_node
from protoclaw.orchestrator.nodes.generate_openclaw import generate_openclaw_node
from protoclaw.orchestrator.nodes.generate_nanobot import generate_nanobot_node
from protoclaw.orchestrator.nodes.deploy import deploy_node
from protoclaw.orchestrator.nodes.report import report_node

def _route_after_select(state: ProtoclawState) -> str:
    if state.get("error"):
        return END
    return f"generate_{state['framework']}"

def build_graph():
    workflow = StateGraph(ProtoclawState)

    workflow.add_node("parse", parse_node)
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("select", select_node)
    workflow.add_node("generate_openclaw", generate_openclaw_node)
    workflow.add_node("generate_nanobot", generate_nanobot_node)
    workflow.add_node("deploy", deploy_node)
    workflow.add_node("report", report_node)

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "decompose")
    workflow.add_edge("decompose", "guardrails")
    workflow.add_edge("guardrails", "select")
    workflow.add_conditional_edges(
        "select",
        _route_after_select,
        {
            "generate_openclaw": "generate_openclaw",
            "generate_nanobot": "generate_nanobot",
            END: END,
        },
    )
    workflow.add_edge("generate_openclaw", "deploy")
    workflow.add_edge("generate_nanobot", "deploy")
    workflow.add_edge("deploy", "report")
    workflow.add_edge("report", END)

    return workflow.compile()
```

- [ ] **Step 2: Smoke test graph compiles**

```bash
python -c "from protoclaw.orchestrator.graph import build_graph; g = build_graph(); print('Graph compiled OK')"
```

Expected: `Graph compiled OK`

- [ ] **Step 3: Commit**

```bash
git add protoclaw/orchestrator/graph.py
git commit -m "feat: assemble LangGraph state machine (parse→decompose→guardrails→select→generate→deploy→report)"
```

---

## Task 14: CLI

**Files:**
- Create: `protoclaw/cli/main.py`

- [ ] **Step 1: Create `protoclaw/cli/main.py`**

```python
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

@click.group()
def cli():
    """ProtoClaw — Intelligent Agent Factory\n\nDeploy focused AI agents from a mission string."""
    pass

@cli.command()
@click.argument("mission")
def deploy(mission: str):
    """Deploy a new agent from a mission description.

    Example: protoclaw deploy "Pesquisar tendências de IA no Reddit nos últimos 30 dias"
    """
    from protoclaw.orchestrator.graph import build_graph

    initial_state = {
        "mission": mission,
        "subtasks": [],
        "guardrails": [],
        "framework": None,
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
    }

    with console.status("[bold green]Deploying agent...[/bold green]"):
        graph = build_graph()
        result = graph.invoke(initial_state)

    if result.get("error"):
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
        raise SystemExit(1)

    console.print(result.get("report", "Agent deployed."))

@cli.command(name="list")
def list_agents():
    """List all running ProtoClaw agents."""
    from protoclaw.deployer.docker import list_agents as _list

    agents = _list()
    if not agents:
        console.print("[yellow]No agents running.[/yellow]")
        return

    table = Table(title="Running Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("ID", style="dim")
    for agent in agents:
        table.add_row(agent["name"], agent["status"], agent["id"])
    console.print(table)

@cli.command()
@click.argument("name")
def logs(name: str):
    """Tail logs for an agent container."""
    from protoclaw.deployer.docker import get_logs
    console.print(get_logs(name))

@cli.command()
@click.argument("name")
def stop(name: str):
    """Stop and remove an agent container."""
    from protoclaw.deployer.docker import stop_agent
    stop_agent(name)
    console.print(f"[green]✓[/green] Agent [cyan]{name}[/cyan] stopped and removed.")

@cli.command()
@click.argument("name")
def status(name: str):
    """Show status of an agent container."""
    from protoclaw.deployer.docker import list_agents
    agents = {a["name"]: a for a in list_agents()}
    if name not in agents:
        console.print(f"[yellow]Agent '{name}' not found.[/yellow]")
        raise SystemExit(1)
    agent = agents[name]
    console.print(f"  Name   : {agent['name']}")
    console.print(f"  Status : [green]{agent['status']}[/green]")
    console.print(f"  ID     : {agent['id']}")
```

- [ ] **Step 2: Test CLI help**

```bash
protoclaw --help
protoclaw deploy --help
```

Expected: help text appears for each command with description and arguments.

- [ ] **Step 3: Commit**

```bash
git add protoclaw/cli/main.py
git commit -m "feat: add Click CLI (deploy/list/logs/stop/status)"
```

---

## Task 15: Docker Infrastructure

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `workspaces/.gitkeep`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY protoclaw/ protoclaw/

ENTRYPOINT ["protoclaw"]
CMD ["--help"]
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  protoclaw:
    build: .
    volumes:
      - ./workspaces:/app/workspaces
      - /var/run/docker.sock:/var/run/docker.sock
    env_file:
      - .env
    stdin_open: true
    tty: true

  ollama:
    image: ollama/ollama
    profiles:
      - local-llm
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

- [ ] **Step 3: Build Docker image to verify**

```bash
docker build -t protoclaw:latest .
```

Expected: build succeeds, image created.

- [ ] **Step 4: Smoke test in Docker**

```bash
docker run --rm protoclaw:latest --help
```

Expected: CLI help text printed.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml workspaces/.gitkeep
git commit -m "feat: add Dockerfile and docker-compose for ProtoClaw + Ollama"
```

---

## Task 16: Integration Test (Canary Mission)

**Files:**
- Create: `tests/integration/test_canary.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
# tests/conftest.py
# Shared fixtures for unit and integration tests.
```

- [ ] **Step 2: Create `tests/integration/test_canary.py`**

```python
# tests/integration/test_canary.py
"""
Canary integration test: runs the full pipeline with LLM nodes mocked
but workspace and generation nodes real.
Run with: pytest tests/integration/test_canary.py -v
"""
import json
import pytest
from unittest.mock import MagicMock, patch

_CANARY_MISSION = "Pesquisar tendências de IA no Reddit nos últimos 30 dias"

_MOCK_SUBTASKS = {
    "subtasks": [
        {"description": "Coletar posts do Reddit sobre IA", "type": "sequential", "completion_criteria": "100 posts coletados"},
        {"description": "Filtrar posts dos últimos 30 dias", "type": "sequential", "completion_criteria": "Posts com data >= 30 dias atrás"},
        {"description": "Identificar top 5 tendências", "type": "sequential", "completion_criteria": "5 tendências listadas"},
        {"description": "Gerar relatório final", "type": "sequential", "completion_criteria": "Relatório em markdown gerado"},
    ]
}

_MOCK_GUARDRAILS = {
    "guardrails": [
        "Nunca acesse sites fora do Reddit",
        "Não execute código externo não autorizado",
        "Não armazene dados pessoais de usuários",
        "Limite pesquisa aos últimos 30 dias",
        "Não envie mensagens a usuários do Reddit",
    ]
}

@pytest.fixture
def mock_decompose_chain():
    mock = MagicMock()
    mock.invoke.return_value = _MOCK_SUBTASKS
    return mock

@pytest.fixture
def mock_guardrails_chain():
    mock = MagicMock()
    mock.invoke.return_value = _MOCK_GUARDRAILS
    return mock

def test_canary_pipeline_selects_nanobot(mock_decompose_chain, mock_guardrails_chain):
    """Full pipeline: canary mission should select NanoBot (research task, no channel)."""
    with (
        patch("protoclaw.orchestrator.nodes.decompose._build_chain", return_value=mock_decompose_chain),
        patch("protoclaw.orchestrator.nodes.guardrails._build_chain", return_value=mock_guardrails_chain),
    ):
        from protoclaw.orchestrator.nodes.parse import parse_node
        from protoclaw.orchestrator.nodes.decompose import decompose_node
        from protoclaw.orchestrator.nodes.guardrails import guardrails_node
        from protoclaw.orchestrator.nodes.select import select_node

        state = {
            "mission": _CANARY_MISSION,
            "subtasks": [], "guardrails": [], "framework": None,
            "generated_files": {}, "workspace_dir": "", "container_id": "", "error": None,
        }

        state = {**state, **parse_node(state)}
        state = {**state, **decompose_node(state)}
        state = {**state, **guardrails_node(state)}
        state = {**state, **select_node(state)}

        assert state["error"] is None
        assert state["framework"] == "nanobot"
        assert len(state["subtasks"]) == 4
        assert len(state["guardrails"]) == 5

def test_canary_pipeline_generates_valid_nanobot_configs(mock_decompose_chain, mock_guardrails_chain):
    """Generate step produces valid JSON config.json for NanoBot."""
    with (
        patch("protoclaw.orchestrator.nodes.decompose._build_chain", return_value=mock_decompose_chain),
        patch("protoclaw.orchestrator.nodes.guardrails._build_chain", return_value=mock_guardrails_chain),
    ):
        from protoclaw.orchestrator.nodes.parse import parse_node
        from protoclaw.orchestrator.nodes.decompose import decompose_node
        from protoclaw.orchestrator.nodes.guardrails import guardrails_node
        from protoclaw.orchestrator.nodes.select import select_node
        from protoclaw.orchestrator.nodes.generate_nanobot import generate_nanobot_node

        state = {
            "mission": _CANARY_MISSION,
            "subtasks": [], "guardrails": [], "framework": None,
            "generated_files": {}, "workspace_dir": "", "container_id": "", "error": None,
        }

        for node_fn in [parse_node, decompose_node, guardrails_node, select_node, generate_nanobot_node]:
            state = {**state, **node_fn(state)}

        files = state["generated_files"]
        assert "config.json" in files
        assert ".env" in files

        config = json.loads(files["config.json"])
        assert config["agent_name"] is not None
        assert len(config["guardrails"]) == 5
        assert len(config["subtasks"]) == 4
```

- [ ] **Step 3: Run integration tests**

```bash
pytest tests/integration/test_canary.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/integration/test_canary.py
git commit -m "test: add canary integration test for full pipeline"
```

---

## Task 17: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Rewrite `CLAUDE.md` with real project content**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run unit tests only (fast, no Docker)
pytest tests/unit/ -v

# Run a single test
pytest tests/unit/test_select.py::test_select_nanobot_for_research_task -v

# Run integration tests (LLM nodes are mocked, no real API calls)
pytest tests/integration/ -v

# Deploy an agent
protoclaw deploy "Pesquisar tendências de IA no Reddit nos últimos 30 dias"

# List running agents
protoclaw list

# View agent logs
protoclaw logs protoclaw-<agent-name>

# Stop agent
protoclaw stop protoclaw-<agent-name>
```

## Architecture

ProtoClaw is a **LangGraph state machine** that receives a mission string and deploys a focused AI agent in Docker.

**Pipeline:** `parse → decompose → guardrails → select → generate_{framework} → deploy → report`

**State object** (`protoclaw/orchestrator/state.py`): `ProtoclawState` TypedDict flows through every node. Nodes return partial dicts that are merged into the state.

**LLM nodes** (`decompose`, `guardrails`): Use `_build_chain()` helper (patchable in tests) that returns `PROMPT | build_llm() | JsonOutputParser()`. Mock `_build_chain` to test without real LLM calls.

**Framework selection** (`select.py`): Fully deterministic — keyword matching against channel and persistence keyword sets. No LLM involved.

**Templates** (`protoclaw/templates/`): Jinja2 `.j2` files, one directory per framework. Rendered by `generate_openclaw.py` and `generate_nanobot.py`.

**Target frameworks:**
- `openclaw` → `github.com/openclaw/openclaw` (TypeScript, multi-channel, SOUL.md + AGENTS.md)
- `nanobot` → `github.com/yukihamada/nanobot` (Rust, single binary, env config)

## Environment

Copy `.env.example` to `.env`. At minimum one of `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is needed; Ollama is the zero-cost local fallback.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with real commands and architecture"
```

---

## Task 18: Final Push

- [ ] **Step 1: Run full test suite one last time**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass, zero failures.

- [ ] **Step 2: Push all commits to GitHub**

```bash
git push origin master
```

- [ ] **Step 3: Manual smoke test**

```bash
cp .env.example .env
# Add at least one API key to .env
protoclaw deploy "Pesquisar tendências de IA no Reddit nos últimos 30 dias"
```

Expected output (with real LLM):
```
✓ Agent deployed successfully!
  Framework : nanobot
  Directory : workspaces/pesquisar-tendncias-de-ia-no-reddit-nos-lt-20260327/
  Container : protoclaw-pesquisar-tendncias-de-ia-no-reddit-nos-lt
  Status    : running
  Logs      : protoclaw logs protoclaw-pesquisar-tendncias-de-ia-no-reddit-nos-lt
```
