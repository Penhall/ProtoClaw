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
        "framework": "openclaw",
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
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
