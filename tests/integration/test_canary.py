"""
Canary integration test: runs the full pipeline with LLM nodes mocked
but all other nodes (parse, select, generate) running for real.

Run with: pytest tests/integration/test_canary.py -v
"""
import json
from unittest.mock import MagicMock, patch

_CANARY_MISSION = "Pesquisar tendências de IA no Reddit nos últimos 30 dias"

_MOCK_SUBTASKS = {
    "subtasks": [
        {
            "description": "Coletar posts do Reddit sobre IA",
            "type": "sequential",
            "completion_criteria": "100 posts coletados",
        },
        {
            "description": "Filtrar posts dos últimos 30 dias",
            "type": "sequential",
            "completion_criteria": "Posts com data >= 30 dias atrás",
        },
        {
            "description": "Identificar top 5 tendências",
            "type": "sequential",
            "completion_criteria": "5 tendências listadas",
        },
        {
            "description": "Gerar relatório final",
            "type": "sequential",
            "completion_criteria": "Relatório em markdown gerado",
        },
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


def test_canary_pipeline_selects_nanobot():
    """Full pipeline up to select: canary mission should pick NanoBot (no channel, not persistent)."""
    mock_decompose = MagicMock()
    mock_decompose.invoke.return_value = _MOCK_SUBTASKS

    mock_guardrails = MagicMock()
    mock_guardrails.invoke.return_value = _MOCK_GUARDRAILS

    with (
        patch("protoclaw.orchestrator.nodes.decompose._build_chain", return_value=mock_decompose),
        patch("protoclaw.orchestrator.nodes.guardrails._build_chain", return_value=mock_guardrails),
    ):
        from protoclaw.orchestrator.nodes.parse import parse_node
        from protoclaw.orchestrator.nodes.decompose import decompose_node
        from protoclaw.orchestrator.nodes.guardrails import guardrails_node
        from protoclaw.orchestrator.nodes.select import select_node

        state = {
            "mission": _CANARY_MISSION,
            "subtasks": [],
            "guardrails": [],
            "framework": None,
            "generated_files": {},
            "workspace_dir": "",
            "container_id": "",
            "error": None,
        }

        state = {**state, **parse_node(state)}
        state = {**state, **decompose_node(state)}
        state = {**state, **guardrails_node(state)}
        state = {**state, **select_node(state)}

    assert state["error"] is None
    assert state["framework"] == "nanobot"
    assert len(state["subtasks"]) == 4
    assert len(state["guardrails"]) == 5


def test_canary_pipeline_generates_valid_nanobot_configs():
    """Generate step produces valid JSON config.json for NanoBot."""
    mock_decompose = MagicMock()
    mock_decompose.invoke.return_value = _MOCK_SUBTASKS

    mock_guardrails = MagicMock()
    mock_guardrails.invoke.return_value = _MOCK_GUARDRAILS

    with (
        patch("protoclaw.orchestrator.nodes.decompose._build_chain", return_value=mock_decompose),
        patch("protoclaw.orchestrator.nodes.guardrails._build_chain", return_value=mock_guardrails),
    ):
        from protoclaw.orchestrator.nodes.parse import parse_node
        from protoclaw.orchestrator.nodes.decompose import decompose_node
        from protoclaw.orchestrator.nodes.guardrails import guardrails_node
        from protoclaw.orchestrator.nodes.select import select_node
        from protoclaw.orchestrator.nodes.generate_nanobot import generate_nanobot_node

        state = {
            "mission": _CANARY_MISSION,
            "subtasks": [],
            "guardrails": [],
            "framework": None,
            "generated_files": {},
            "workspace_dir": "",
            "container_id": "",
            "error": None,
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
