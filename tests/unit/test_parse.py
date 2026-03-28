from protoclaw.orchestrator.state import ProtoclawState


def _state(mission: str) -> ProtoclawState:
    return {
        "mission": mission,
        "subtasks": [],
        "guardrails": [],
        "framework": None,
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
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
