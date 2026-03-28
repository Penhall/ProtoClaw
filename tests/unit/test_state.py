from protoclaw.orchestrator.state import ProtoclawState, Subtask


def test_protoclaw_state_accepts_valid_data():
    state: ProtoclawState = {
        "mission": "Pesquisar IA no Reddit",
        "subtasks": [],
        "guardrails": [],
        "framework": None,
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
    }
    assert state["mission"] == "Pesquisar IA no Reddit"


def test_subtask_fields():
    task: Subtask = {
        "description": "Coletar posts",
        "type": "sequential",
        "completion_criteria": "100 posts coletados",
    }
    assert task["type"] == "sequential"
