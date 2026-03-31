import os
import re
from urllib.parse import urlparse

from protoclaw.orchestrator.state import ProtoclawState


def _slug(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")[:40]


def report_node(state: ProtoclawState) -> dict:
    """Build the success message shown to the user."""
    agent_name = _slug(state["mission"])
    container_name = f"protoclaw-{agent_name}"
    framework = state["framework"]

    url_line = ""
    docker_host = os.getenv("DOCKER_HOST", "")
    if framework == "nanobot" and docker_host.startswith("ssh://"):
        hostname = urlparse(docker_host).hostname or "localhost"
        host_port = 3100 + (hash(agent_name) % 900)
        url_line = f"  URL       : http://{hostname}:{host_port}\n"

    report = (
        f"\n[✓] Agent deployed successfully!\n"
        f"  Framework : {framework}\n"
        f"  Container : {container_name}\n"
        f"  Status    : running\n"
        f"{url_line}"
        f"  Logs      : protoclaw logs {container_name}\n"
    )

    return {"report": report}
