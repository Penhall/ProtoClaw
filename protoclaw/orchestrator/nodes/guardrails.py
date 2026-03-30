import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from protoclaw.llm.provider import build_llm
from protoclaw.llm.parsing import strip_to_json
from protoclaw.orchestrator.state import ProtoclawState

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an AI agent safety and focus expert. "
        "CRITICAL: respond with ONLY valid JSON — no introduction, no explanation, "
        "no markdown fences. Start your response directly with {{ and end with }}.",
    ),
    (
        "human",
        "Mission: {mission}\n"
        "Subtasks: {subtasks}\n\n"
        "Generate 5-8 strict, specific guardrails (focus rules). "
        "Each must be a clear prohibition that prevents scope deviation.\n\n"
        "Return ONLY this JSON structure:\n"
        '{{"guardrails": ["Clear prohibitive rule"]}}',
    ),
])


def _build_chain():
    return _PROMPT | build_llm() | strip_to_json | JsonOutputParser()


def guardrails_node(state: ProtoclawState) -> dict:
    chain = _build_chain()
    result = chain.invoke({
        "mission": state["mission"],
        "subtasks": json.dumps(state["subtasks"], ensure_ascii=False),
    })
    return {"guardrails": result["guardrails"]}
