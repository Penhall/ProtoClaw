from unittest.mock import MagicMock, patch
from protoclaw.orchestrator.state import ProtoclawState


def _state(mission: str = "Pesquisar IA no Reddit") -> ProtoclawState:
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


_MOCK_RESULT = {
    "subtasks": [
        {
            "description": "Coletar posts do Reddit sobre IA",
            "type": "sequential",
            "completion_criteria": "100 posts coletados",
        },
        {
            "description": "Filtrar posts dos últimos 30 dias",
            "type": "sequential",
            "completion_criteria": "Posts filtrados por data",
        },
        {
            "description": "Identificar top 5 tendências",
            "type": "sequential",
            "completion_criteria": "Tendências listadas",
        },
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
