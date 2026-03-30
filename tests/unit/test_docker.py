from unittest.mock import MagicMock, call, patch

_OPENCLAW_IMAGE = "ghcr.io/openclaw/openclaw:latest"


def test_deploy_nanobot_via_ssh():
    """Nanobot deploy uses SSH upload + docker build/run on remote server."""
    from protoclaw.deployer.docker import deploy_agent

    mock_ssh_info = {"hostname": "cadalora", "username": "petto", "key_filename": None}
    mock_ssh = MagicMock()

    # Simulate: rm -rf → upload → network → rm container → build → run
    mock_stdout_ok = MagicMock()
    mock_stdout_ok.channel.recv_exit_status.return_value = 0
    mock_stdout_ok.read.return_value = b"abc123"
    mock_ssh.exec_command.return_value = (None, mock_stdout_ok, MagicMock(read=lambda: b""))

    mock_sftp = MagicMock()
    mock_ssh.open_sftp.return_value = mock_sftp

    with (
        patch("protoclaw.deployer.docker._ssh_info", return_value=mock_ssh_info),
        patch("protoclaw.deployer.docker._make_ssh", return_value=mock_ssh),
        patch("protoclaw.deployer.docker.Path.iterdir", return_value=[]),
    ):
        result = deploy_agent("nanobot", "/tmp/workspace", "test-agent")

    assert result == "abc123"
    # Ensure docker build was called on the remote
    calls_str = str(mock_ssh.exec_command.call_args_list)
    assert "docker build" in calls_str


def test_deploy_openclaw_uses_prebuilt_image():
    """OpenClaw deploy uses the pre-built GHCR image via local Docker SDK."""
    from protoclaw.deployer.docker import deploy_agent

    mock_container = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container

    with (
        patch("protoclaw.deployer.docker._ssh_info", return_value=None),
        patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client),
    ):
        deploy_agent("openclaw", "/tmp/workspace", "test-agent")

    call_args = mock_client.containers.run.call_args
    assert call_args[0][0] == _OPENCLAW_IMAGE


def test_list_agents_filters_by_protoclaw_prefix():
    from protoclaw.deployer.docker import list_agents

    mock_c1 = MagicMock()
    mock_c1.name = "protoclaw-test"
    mock_c1.status = "running"
    mock_c1.short_id = "abc"

    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_c1]

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        result = list_agents()

    assert len(result) == 1
    assert result[0]["name"] == "protoclaw-test"


def test_stop_agent_calls_stop_and_remove():
    from protoclaw.deployer.docker import stop_agent

    mock_container = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        stop_agent("protoclaw-test")

    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()
