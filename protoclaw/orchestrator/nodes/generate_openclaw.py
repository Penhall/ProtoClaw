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
