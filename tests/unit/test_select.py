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


def test_select_nanobot_for_research_task():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Pesquisar tendências de IA no Reddit nos últimos 30 dias"))
    assert result["framework"] == "nanobot"


def test_select_openclaw_for_telegram():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Criar assistente no Telegram que responde dúvidas"))
    assert result["framework"] == "openclaw"


def test_select_openclaw_for_discord():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Monitorar canal Discord e resumir mensagens"))
    assert result["framework"] == "openclaw"


def test_select_openclaw_for_whatsapp():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Responder clientes no WhatsApp automaticamente"))
    assert result["framework"] == "openclaw"


def test_select_openclaw_for_persistent_assistant():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Assistente pessoal que sempre responde e-mails"))
    assert result["framework"] == "openclaw"


def test_select_nanobot_for_scraping():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Fazer scraping de preços de produtos na Amazon"))
    assert result["framework"] == "nanobot"


def test_select_nanobot_for_simple_monitoring():
    from protoclaw.orchestrator.nodes.select import select_node
    result = select_node(_state("Verificar disponibilidade de um site a cada hora"))
    assert result["framework"] == "nanobot"
