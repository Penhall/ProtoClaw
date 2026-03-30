import os
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from protoclaw.orchestrator.state import ProtoclawState

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "nanobot"


def _slug(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")[:40]


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
        "google_ai_api_key": os.getenv("GOOGLE_AI_API_KEY", ""),
    }

    files: dict[str, str] = {}
    for tpl_name, out_name in [
        (".env.j2", ".env"),
        ("config.json.j2", "config.json"),
    ]:
        files[out_name] = env.get_template(tpl_name).render(**context)

    return {"generated_files": files}
