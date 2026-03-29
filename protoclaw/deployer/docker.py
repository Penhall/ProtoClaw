import re

import docker

_IMAGES = {
    "openclaw": "ghcr.io/openclaw/openclaw:latest",
    "nanobot": "yukihamada/nanobot:latest",
}


def _ensure_network(client: docker.DockerClient, network_name: str) -> None:
    existing = [n.name for n in client.networks.list()]
    if network_name not in existing:
        client.networks.create(network_name, driver="bridge")


def deploy_agent(framework: str, workspace_dir: str, agent_name: str) -> str:
    """Deploy agent container. Returns container ID."""
    client = docker.from_env()
    slug = re.sub(r"[^\w-]", "-", agent_name)[:40]
    container_name = f"protoclaw-{slug}"
    network_name = "protoclaw-net"

    _ensure_network(client, network_name)

    container = client.containers.run(
        _IMAGES[framework],
        name=container_name,
        volumes={workspace_dir: {"bind": "/workspace", "mode": "ro"}},
        network=network_name,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
    )
    return container.id


def get_logs(container_name: str) -> str:
    client = docker.from_env()
    container = client.containers.get(container_name)
    return container.logs(tail=100).decode("utf-8", errors="replace")


def stop_agent(container_name: str) -> None:
    client = docker.from_env()
    container = client.containers.get(container_name)
    container.stop()
    container.remove()


def list_agents() -> list[dict]:
    client = docker.from_env()
    containers = client.containers.list(filters={"name": "protoclaw-"})
    return [
        {"name": c.name, "status": c.status, "id": c.short_id}
        for c in containers
    ]
