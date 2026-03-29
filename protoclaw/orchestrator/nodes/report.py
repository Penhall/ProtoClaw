import re

from protoclaw.orchestrator.state import ProtoclawState


def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")[:40]


def report_node(state: ProtoclawState) -> dict:
    """Build the success message shown to the user."""
    agent_name = _slug(state["mission"])
    container_name = f"protoclaw-{agent_name}"

    report = (
        f"\n[✓] Agent deployed successfully!\n"
        f"  Framework : {state['framework']}\n"
        f"  Directory : {state['workspace_dir']}\n"
        f"  Container : {container_name}\n"
        f"  Status    : running\n"
        f"  Logs      : protoclaw logs {container_name}\n"
    )

    return {"report": report}
