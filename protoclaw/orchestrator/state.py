from typing import TypedDict, Literal


class Subtask(TypedDict):
    description: str
    type: Literal["sequential", "parallel"]
    completion_criteria: str


class ProtoclawState(TypedDict):
    mission: str
    subtasks: list[Subtask]
    guardrails: list[str]
    framework: Literal["openclaw", "nanobot"] | None
    generated_files: dict[str, str]   # filename -> rendered content
    workspace_dir: str
    container_id: str
    error: str | None
