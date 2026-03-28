from pathlib import Path
from unittest.mock import patch, MagicMock


def test_setup_workspace_creates_directory(tmp_path, monkeypatch):
    from protoclaw.workspace import manager
    monkeypatch.setattr(manager, "WORKSPACES_ROOT", tmp_path)

    with patch("protoclaw.workspace.manager.git.Repo.clone_from"):
        result = manager.setup_workspace(
            framework="nanobot",
            agent_name="test-agent",
            generated_files={"config.json": '{"name": "test"}', ".env": "KEY=val"},
        )

    workspace_dir = Path(result)
    assert workspace_dir.parent == tmp_path


def test_setup_workspace_writes_generated_files(tmp_path, monkeypatch):
    from protoclaw.workspace import manager
    monkeypatch.setattr(manager, "WORKSPACES_ROOT", tmp_path)

    with patch("protoclaw.workspace.manager.git.Repo.clone_from"):
        result = manager.setup_workspace(
            framework="nanobot",
            agent_name="test-agent",
            generated_files={"config.json": '{"name": "test"}'},
        )

    config_file = Path(result) / "config.json"
    assert config_file.exists()
    assert '{"name": "test"}' in config_file.read_text()


def test_setup_workspace_clones_correct_repo(tmp_path, monkeypatch):
    from protoclaw.workspace import manager
    monkeypatch.setattr(manager, "WORKSPACES_ROOT", tmp_path)

    with patch("protoclaw.workspace.manager.git.Repo.clone_from") as mock_clone:
        manager.setup_workspace(
            framework="openclaw",
            agent_name="test-agent",
            generated_files={},
        )

    called_url = mock_clone.call_args[0][0]
    assert "openclaw/openclaw" in called_url
