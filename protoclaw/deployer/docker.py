import os
import re
from pathlib import Path
from urllib.parse import urlparse

import docker
import paramiko

# Frameworks that must be built from source (no pre-built image on Docker Hub)
_BUILD_FRAMEWORKS = {"nanobot"}

# Pre-built images for frameworks that have them
_IMAGES = {
    "openclaw": "ghcr.io/openclaw/openclaw:latest",
}


def _ssh_info() -> dict | None:
    """Parse DOCKER_HOST=ssh://user@host into paramiko connect kwargs."""
    host = os.getenv("DOCKER_HOST", "")
    if not host.startswith("ssh://"):
        return None
    p = urlparse(host)
    key = os.path.expanduser("~/.ssh/protoclaw_key")
    return {
        "hostname": p.hostname,
        "username": p.username,
        "key_filename": key if os.path.exists(key) else None,
    }


def _make_ssh(info: dict) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(**info)
    return client


def _sftp_makedirs(sftp: paramiko.SFTPClient, path: str) -> None:
    """Create all directories in path, like mkdir -p."""
    parts = [p for p in path.split("/") if p]
    current = ""
    for part in parts:
        current = f"{current}/{part}"
        try:
            sftp.mkdir(current)
        except OSError:
            pass  # already exists


def _sftp_upload(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    """Recursively upload local directory to remote path, skipping .git and target."""
    _SKIP = {".git", "target", "__pycache__", ".pytest_cache"}
    _sftp_makedirs(sftp, remote)
    for item in local.iterdir():
        if item.name in _SKIP:
            continue
        rpath = f"{remote}/{item.name}"
        if item.is_dir():
            _sftp_upload(sftp, item, rpath)
        else:
            sftp.put(str(item), rpath)


def _exec(ssh: paramiko.SSHClient, cmd: str) -> tuple[int, str, str]:
    _, out, err = ssh.exec_command(cmd)
    code = out.channel.recv_exit_status()
    return code, out.read().decode(), err.read().decode()


def _ensure_network(client: docker.DockerClient, network_name: str) -> None:
    existing = [n.name for n in client.networks.list()]
    if network_name not in existing:
        client.networks.create(network_name, driver="bridge")


def deploy_agent(framework: str, workspace_dir: str, agent_name: str) -> str:
    """Deploy agent container on remote or local Docker. Returns container ID."""
    network = os.getenv("PROTOCLAW_NETWORK", "protoclaw-net")
    slug = re.sub(r"[^\w-]", "-", agent_name)[:40]
    container_name = f"protoclaw-{slug}"

    info = _ssh_info()

    if info and framework in _BUILD_FRAMEWORKS:
        # --- Remote SSH: upload workspace, build image, run container ---
        remote_ws = f"/home/{info['username']}/protoclaw-workspaces/{slug}"
        image_tag = f"protoclaw-{slug}:latest"

        ssh = _make_ssh(info)
        try:
            # Clean previous workspace if exists
            _exec(ssh, f"rm -rf {remote_ws}")

            # Upload workspace
            sftp = ssh.open_sftp()
            _sftp_upload(sftp, Path(workspace_dir), remote_ws)
            sftp.close()

            # Ensure Docker network exists on remote
            _exec(ssh, f"docker network inspect {network} >/dev/null 2>&1 || docker network create {network}")

            # Stop + remove existing container with same name
            _exec(ssh, f"docker rm -f {container_name} 2>/dev/null || true")

            # Build image (may take several minutes for Rust projects)
            code, out, err = _exec(
                ssh, f"docker build -t {image_tag} {remote_ws} 2>&1"
            )
            if code != 0:
                raise RuntimeError(f"docker build failed (exit {code}):\n{out}\n{err}")

            # Run container
            code, out, err = _exec(
                ssh,
                f"docker run -d --name {container_name} "
                f"--network {network} "
                f"--restart unless-stopped "
                f"{image_tag} 2>&1",
            )
            if code != 0:
                raise RuntimeError(f"docker run failed (exit {code}):\n{out}\n{err}")

            container_id = out.strip()
        finally:
            ssh.close()

        return container_id

    # --- Local or pre-built image path ---
    client = docker.from_env()
    _ensure_network(client, network)

    container = client.containers.run(
        _IMAGES[framework],
        name=container_name,
        volumes={workspace_dir: {"bind": "/workspace", "mode": "ro"}},
        network=network,
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
