import re
import shutil
from datetime import datetime
from pathlib import Path

import git

WORKSPACES_ROOT = Path(__file__).parent.parent.parent / "workspaces"

_REPOS = {
    "openclaw": "https://github.com/openclaw/openclaw.git",
    "nanobot": "https://github.com/yukihamada/nanobot.git",
}


def setup_workspace(
    framework: str,
    agent_name: str,
    generated_files: dict[str, str],
) -> str:
    """Clone target repo and inject generated config files. Returns workspace path string."""
    date_str = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r"[^\w-]", "-", agent_name)[:40]
    workspace_dir = WORKSPACES_ROOT / f"{slug}-{date_str}"

    WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    git.Repo.clone_from(_REPOS[framework], workspace_dir, depth=1)

    for filename, content in generated_files.items():
        target = workspace_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return str(workspace_dir)
