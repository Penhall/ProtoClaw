import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from protoclaw.llm.provider import build_llm
from protoclaw.orchestrator.state import ProtoclawState

_PROMPT = ChatPromptTemplate.from_template(
    "Você é especialista em segurança e foco de agentes de IA.\n\n"
    "Missão: {mission}\n"
    "Subtarefas: {subtasks}\n\n"
    "Gere 5-8 guardrails (regras de foco) rígidas e específicas.\n"
    "Cada guardrail deve ser uma proibição clara que evita desvio de escopo.\n\n"
    "Responda APENAS com JSON válido:\n"
    '{{"guardrails": ["Regra proibitiva clara"]}}'
)


def _build_chain():
    return _PROMPT | build_llm() | JsonOutputParser()


def guardrails_node(state: ProtoclawState) -> dict:
    chain = _build_chain()
    result = chain.invoke({
        "mission": state["mission"],
        "subtasks": json.dumps(state["subtasks"], ensure_ascii=False),
    })
    return {"guardrails": result["guardrails"]}
