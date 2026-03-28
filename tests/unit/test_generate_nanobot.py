import json
from protoclaw.orchestrator.state import ProtoclawState


def _state() -> ProtoclawState:
    return {
        "mission": "Pesquisar tendências de IA no Reddit nos últimos 30 dias",
        "subtasks": [
            {
                "description": "Coletar posts",
                "type": "sequential",
                "completion_criteria": "Done",
            },
        ],
        "guardrails": ["Nunca acesse sites fora do Reddit"],
        "framework": "nanobot",
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
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
