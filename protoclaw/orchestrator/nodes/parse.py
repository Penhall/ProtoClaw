from protoclaw.orchestrator.state import ProtoclawState


def parse_node(state: ProtoclawState) -> ProtoclawState:
    """Validate and clean the raw mission string."""
    mission = state["mission"].strip()

    if not mission:
        return {**state, "error": "Mission cannot be empty"}

    return {**state, "mission": mission, "error": None}
