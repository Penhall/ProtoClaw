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
        {
            "type": "sequential",
            "description": "Coletar posts",
            "completion_criteria": "100 posts coletados",
        },
        {
            "type": "sequential",
            "description": "Filtrar por data",
            "completion_criteria": "Posts filtrados",
        },
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
        {
            "description": "Coletar posts",
            "type": "sequential",
            "completion_criteria": "Done",
        },
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
