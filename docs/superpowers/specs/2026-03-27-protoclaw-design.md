# ProtoClaw — Design Spec
**Date:** 2026-03-27
**Scope:** Phase 0 (Blueprints) + Phase 1 (MVP CLI)
**Status:** Approved

---

## 1. Problem & Goal

ProtoClaw is an intelligent agent factory. Given a high-level mission in natural language (e.g. "Pesquisar tendências de IA no Reddit nos últimos 30 dias"), it automatically:

1. Decomposes the mission into 4–8 focused subtasks
2. Generates strict guardrails so the agent never drifts off-focus
3. Selects the right target framework (OpenClaw or NanoBot)
4. Generates all configuration files from Jinja2 templates
5. Clones the target repo, injects the files, and deploys in Docker
6. Reports back: container name, status, logs endpoint

ProtoClaw does NOT fork or rewrite OpenClaw or NanoBot — it orchestrates them.

---

## 2. Target Frameworks

### OpenClaw (`github.com/openclaw/openclaw`)
- Language: TypeScript / Node.js
- Use when: multi-channel (Telegram, Discord, WhatsApp…), persistent daemon, personality required
- Config files generated: `SOUL.md`, `AGENTS.md`, `workspace.json`

### NanoBot (`github.com/yukihamada/nanobot`)
- Language: Rust, single binary ~9MB, 128MB RAM
- Use when: single task, scraping/research, no channel, stateless
- Config files generated: `.env`, `config.json`

---

## 3. Architecture

### 3.1 Pipeline (LangGraph state machine)

```
CLI Input
    │
    ▼
 PARSE        → extracts: objective, domain, context, language
    │
    ▼
 DECOMPOSE    → LLM generates 4–8 subtasks (sequential or parallel)
    │
    ▼
 GUARDRAILS   → LLM generates strict focus rules ("never do X")
    │
    ▼
 SELECT       → deterministic logic: OpenClaw or NanoBot?
    │
  ┌─┴─┐
  ▼   ▼
GEN_OC  GEN_NB  → Jinja2 renders all config files for chosen framework
  └─┬─┘
    │
    ▼
 DEPLOY       → Docker SDK: clone repo, inject files, build, run
    │
    ▼
 REPORT       → CLI output: container name, status, logs command
```

### 3.2 Shared State

```python
class ProtoclawState(TypedDict):
    mission: str
    subtasks: list[dict]        # [{description, type: sequential|parallel}]
    guardrails: list[str]       # strict focus rules
    framework: Literal["openclaw", "nanobot"]
    generated_files: dict[str, str]   # filepath → content
    workspace_dir: str
    container_id: str
    error: str | None
```

State persists across nodes. A failed DEPLOY node can be retried without regenerating configs.

### 3.3 LLM Provider Chain (no LiteLLM)

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

primary  = ChatAnthropic(model="claude-opus-4-6")
fallback1 = ChatOpenAI(model="gpt-4o")
fallback2 = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    model="llama3",
    api_key="ollama"
)

llm = primary.with_fallbacks([fallback1, fallback2])
```

Each provider only activates if its env var is set (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). Ollama requires no key and runs locally at no cost.

### 3.4 Framework Selection Logic (deterministic, no LLM)

| Mission signal | Selected framework |
|---|---|
| Mentions channel (Telegram, WhatsApp, Discord…) | OpenClaw |
| Long-running / daemon / persistent assistant | OpenClaw |
| Single task (scraping, research, monitoring) | NanoBot |
| Simple, stateless, no channel | NanoBot |
| Multi-channel + personality required | OpenClaw |

Implemented as a scored rule set — no ambiguity, fully testable.

---

## 4. Project Structure

```
protoclaw/
├── protoclaw/
│   ├── cli/
│   │   └── main.py               # Click: deploy, list, logs, stop, status
│   ├── orchestrator/
│   │   ├── graph.py              # LangGraph graph definition
│   │   ├── state.py              # ProtoclawState TypedDict
│   │   └── nodes/
│   │       ├── parse.py
│   │       ├── decompose.py
│   │       ├── guardrails.py
│   │       ├── select.py
│   │       ├── generate_openclaw.py
│   │       ├── generate_nanobot.py
│   │       ├── deploy.py
│   │       └── report.py
│   ├── llm/
│   │   └── provider.py           # fallback chain builder
│   ├── templates/
│   │   ├── openclaw/
│   │   │   ├── SOUL.md.j2
│   │   │   ├── AGENTS.md.j2
│   │   │   └── workspace.json.j2
│   │   └── nanobot/
│   │       ├── .env.j2
│   │       └── config.json.j2
│   ├── deployer/
│   │   └── docker.py             # Docker SDK: build, run, stop, logs
│   └── workspace/
│       └── manager.py            # GitPython: clone, inject files
│
├── tests/
│   ├── unit/                     # each graph node mocked independently
│   └── integration/              # canary mission end-to-end
├── docs/
│   └── superpowers/specs/
├── workspaces/                   # runtime only, gitignored
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml            # ProtoClaw + optional Ollama service
└── .env.example
```

---

## 5. Jinja2 Templates

### `SOUL.md.j2` (OpenClaw)
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
{% endfor %}
```

### `AGENTS.md.j2` (OpenClaw)
```jinja2
# AGENTS.md — Manual Operacional

## Fluxo de Trabalho
{% for task in subtasks %}
### Etapa {{ loop.index }}: {{ task.description }}
- Tipo: {{ task.type }}
- Critério de conclusão: {{ task.completion_criteria }}
{% endfor %}

## Regras de Foco
Qualquer solicitação fora do escopo abaixo deve ser IGNORADA:
**Escopo:** {{ primary_objective }}

## Política de Desvio
Se o usuário pedir algo fora do escopo: responda "Estou configurado apenas para {{ primary_objective }}."
```

### `config.json.j2` (NanoBot)
```jinja2
{
  "agent_name": "{{ agent_name }}",
  "objective": "{{ primary_objective }}",
  "guardrails": {{ guardrails | tojson }},
  "subtasks": {{ subtasks | tojson }},
  "channels": {{ channels | tojson }},
  "model": "{{ model | default('claude-opus-4-6') }}"
}
```

---

## 6. CLI Interface (Phase 1)

```bash
# Deploy a new agent from mission
protoclaw deploy "Pesquisar tendências de IA no Reddit nos últimos 30 dias"

# List running agents
protoclaw list

# Tail container logs
protoclaw logs reddit-ia-trends-20260327

# Stop and remove agent
protoclaw stop reddit-ia-trends-20260327

# Health check
protoclaw status reddit-ia-trends-20260327
```

Output example after deploy:
```
✓ Mission parsed
✓ Decomposed into 5 subtasks
✓ Framework selected: NanoBot (stateless research task)
✓ Generated: .env, config.json
✓ Workspace cloned: workspaces/reddit-ia-trends-20260327/
✓ Container started: protoclaw-reddit-ia-trends-20260327

Agent deployed successfully!
  Directory : workspaces/reddit-ia-trends-20260327/
  Container : protoclaw-reddit-ia-trends-20260327
  Status    : running
  Logs      : protoclaw logs reddit-ia-trends-20260327
```

---

## 7. Docker Deployment

Each agent runs in an isolated container:

```
Container name : protoclaw-{mission-slug}-{YYYYMMDD}
Base image     : openclaw:latest  OR  nanobot:latest
Volume mount   : workspaces/{slug}/  →  /workspace (read-only config)
Network        : protoclaw-net (isolated bridge)
Secrets        : injected as env vars at runtime (never written to files)
```

The ProtoClaw orchestrator itself runs via `docker-compose.yml`:

```yaml
services:
  protoclaw:
    build: .
    volumes:
      - ./workspaces:/app/workspaces
      - /var/run/docker.sock:/var/run/docker.sock
    env_file: .env

  ollama:                         # optional local LLM fallback
    image: ollama/ollama
    profiles: [local-llm]
```

---

## 8. Error Handling

| Node | Failure | Recovery |
|---|---|---|
| DECOMPOSE | LLM timeout/error | Retry with next provider in chain |
| SELECT | Ambiguous mission | Default to NanoBot (safer, lighter) |
| DEPLOY | Docker daemon down | Retry 3x with exponential backoff |
| DEPLOY | Image pull fails | Report error with fix instructions |
| Any node | Unrecoverable | State saved, error surfaced via CLI |

---

## 9. Testing Strategy

- **Unit tests:** Each LangGraph node tested in isolation with mocked LLM responses
- **Template tests:** Each Jinja2 template rendered with fixture data, output validated
- **Integration test (canary):** Full pipeline with mission *"Pesquisar tendências de IA no Reddit nos últimos 30 dias"* against local NanoBot container
- **Selection tests:** Full coverage of framework selection rule table

---

## 10. Phase 0 Deliverables (Blueprints)

Before Phase 1 coding begins:

1. Study OpenClaw onboarding flow (`openclaw onboard`) → extract minimum viable `workspace.json` fields
2. Study NanoBot workspace format (`~/.nanobot/`) → extract minimum viable `config.json` fields
3. Write and validate all 5 Jinja2 templates with real data
4. Define guardrails taxonomy: a reusable bank of focus-rules the LLM can draw from
5. Document both repos' Docker setup (images, ports, volumes) in `docs/blueprints/`

---

## 11. Out of Scope (Phase 1)

- Web UI / dashboard (Phase 2)
- Multi-agent per mission (Phase 2)
- Kubernetes (Phase 3)
- Marketplace of templates (Phase 3)
- Support for frameworks beyond OpenClaw and NanoBot (Phase 4+)
