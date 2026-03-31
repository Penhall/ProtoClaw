import re

from protoclaw.deployer.docker import deploy_agent
from protoclaw.orchestrator.state import ProtoclawState
from protoclaw.workspace.manager import setup_workspace


def _slug(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")[:40]


def deploy_node(state: ProtoclawState) -> dict:
    """Wire workspace setup and Docker deploy together."""
    agent_name = _slug(state["mission"])
    framework = state["framework"]

    workspace_dir = setup_workspace(
        framework=framework,
        agent_name=agent_name,
        generated_files=state["generated_files"],
    )

    container_id = deploy_agent(
        framework=framework,
        workspace_dir=workspace_dir,
        agent_name=agent_name,
    )

    return {"workspace_dir": workspace_dir, "container_id": container_id}
