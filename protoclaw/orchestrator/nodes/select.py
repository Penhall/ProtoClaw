from protoclaw.orchestrator.state import ProtoclawState

_CHANNEL_KEYWORDS = {
    "telegram", "whatsapp", "discord", "slack", "instagram",
    "twitter", "signal", "imessage", "teams", "matrix", "line",
    "youtube", "facebook", "messenger",
}

_PERSISTENCE_KEYWORDS = {
    "assistente", "assistant", "daemon", "monitor", "sempre",
    "always", "continuously", "continuamente", "permanente",
    "permanent", "24h", "24/7",
}


def select_node(state: ProtoclawState) -> dict:
    """Deterministically choose openclaw or nanobot based on mission text."""
    words = set(state["mission"].lower().split())

    has_channel = bool(words & _CHANNEL_KEYWORDS)
    is_persistent = bool(words & _PERSISTENCE_KEYWORDS)

    framework = "openclaw" if (has_channel or is_persistent) else "nanobot"
    return {"framework": framework}
