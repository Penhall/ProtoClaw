from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from protoclaw.llm.provider import build_llm
from protoclaw.llm.parsing import strip_to_json
from protoclaw.orchestrator.state import ProtoclawState

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a task decomposition expert for AI agents. "
        "CRITICAL: respond with ONLY valid JSON — no introduction, no explanation, "
        "no markdown fences. Start your response directly with { and end with }.",
    ),
    (
        "human",
        "Mission: {mission}\n\n"
        "Decompose into 4-8 clear, executable subtasks. Each must be atomic and verifiable.\n\n"
        "Return ONLY this JSON structure:\n"
        '{{"subtasks": [{{"description": "...", "type": "sequential|parallel", '
        '"completion_criteria": "..."}}]}}',
    ),
])


def _build_chain():
    return _PROMPT | build_llm() | strip_to_json | JsonOutputParser()


def decompose_node(state: ProtoclawState) -> dict:
    chain = _build_chain()
    result = chain.invoke({"mission": state["mission"]})
    return {"subtasks": result["subtasks"]}
