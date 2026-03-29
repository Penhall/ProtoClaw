from unittest.mock import MagicMock, patch

_IMAGES = {
    "openclaw": "ghcr.io/openclaw/openclaw:latest",
    "nanobot": "yukihamada/nanobot:latest",
}


def test_deploy_agent_returns_container_id():
    from protoclaw.deployer.docker import deploy_agent

    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        result = deploy_agent("nanobot", "/tmp/workspace", "test-agent")

    assert result == "abc123"


def test_deploy_agent_uses_correct_image_for_openclaw():
    from protoclaw.deployer.docker import deploy_agent

    mock_container = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.run.return_value = mock_container

    with patch("protoclaw.deployer.docker.docker.from_env", return_value=mock_client):
        deploy_agent("openclaw", "/tmp/workspace", "test-agent")

    call_args = mock_client.containers.run.call_args
    assert call_args[0][0] == _IMAGES["openclaw"]


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
