from unittest.mock import MagicMock, patch
from protoclaw.orchestrator.state import ProtoclawState


def _state() -> ProtoclawState:
    return {
        "mission": "Pesquisar IA no Reddit",
        "subtasks": [
            {
                "description": "Coletar posts",
                "type": "sequential",
                "completion_criteria": "Done",
            }
        ],
        "guardrails": [],
        "framework": None,
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
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
